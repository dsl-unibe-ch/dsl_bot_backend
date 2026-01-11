"""
Playwright-based content extractor that expands all accordions/tabs first,
then extracts content in natural reading order using Beautiful Soup.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any
import argparse
from datetime import datetime, timezone

from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup, NavigableString, Tag
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ContentExtractor:
    """Extract content from pages by expanding all interactive elements first."""
    
    def __init__(self, customer_name: str, output_dir: Path):
        self.customer_name = customer_name
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_base_url = None  # Track current page URL for resolving relative links
    
    async def expand_all_accordions(self, page: Page) -> int:
        """
        Expand all accordion/collapsible elements on the page.
        Returns the number of elements expanded.
        """
        expanded_count = 0
        
        # List of selectors for accordion/collapsible elements
        accordion_selectors = [
            'details:not([open])',  # HTML5 details element
            '[aria-expanded="false"]',  # ARIA accordions
            '[class*="accordion"]:not(.expanded)',
            '[class*="collapse"]:not(.show)',
            'button[class*="accordion"]',
        ]
        
        for selector in accordion_selectors:
            try:
                elements = await page.query_selector_all(selector)
                logger.info(f"Found {len(elements)} elements for selector: {selector}")
                
                for element in elements:
                    try:
                        # Check if element is visible and clickable
                        if await element.is_visible():
                            # For details elements, just add the open attribute
                            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
                            if tag_name == 'details':
                                await element.evaluate('el => el.setAttribute("open", "")')
                            else:
                                # Try to click the element
                                await element.click(timeout=1000)
                            
                            expanded_count += 1
                            await asyncio.sleep(0.1)  # Small delay for animation
                            
                    except Exception as e:
                        logger.debug(f"Could not expand element: {e}")
                        
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
        
        logger.info(f"Expanded {expanded_count} accordion/collapsible elements")
        return expanded_count
    
    async def click_all_tabs(self, page: Page) -> int:
        """
        Click through all tabs to ensure all content is loaded.
        Returns the number of tabs clicked.
        """
        tab_selectors = [
            '[role="tab"]',
            '[data-toggle="tab"]',
            'button[class*="tab"]:not([class*="table"])',
            'a[class*="tab"]:not([class*="table"])',
        ]
        
        tabs = []
        for selector in tab_selectors:
            try:
                found_tabs = await page.query_selector_all(selector)
                for tab in found_tabs:
                    if await tab.is_visible():
                        tabs.append(tab)
                
                if tabs:
                    logger.info(f"Found {len(tabs)} tabs using selector: {selector}")
                    break
                    
            except Exception as e:
                logger.debug(f"Error finding tabs with {selector}: {e}")
        
        # Click through each tab to load content
        for i, tab in enumerate(tabs):
            try:
                tab_label = await tab.inner_text()
                logger.info(f"Clicking tab {i+1}/{len(tabs)}: {tab_label[:50]}")
                await tab.click(timeout=2000)
                await asyncio.sleep(0.3)
                
                # After clicking each tab, expand any accordions within it
                await self.expand_all_accordions(page)
                
            except Exception as e:
                logger.debug(f"Error clicking tab {i}: {e}")
        
        # Click the first tab again to return to initial state (optional)
        if tabs:
            try:
                await tabs[0].click(timeout=2000)
                await asyncio.sleep(0.3)
            except Exception:
                pass
        
        logger.info(f"Processed {len(tabs)} tabs")
        return len(tabs)
    
    def extract_text_content(self, soup: BeautifulSoup) -> str:
        """
        Extract text content from BeautifulSoup object in natural reading order.
        Preserves hierarchy and structure.
        """
        # Find main content area
        main_content = None
        for selector in ['main', '[role="main"]', 'article', '.content', '#content', 'body']:
            main_content = soup.select_one(selector)
            if main_content:
                logger.debug(f"Using main content selector: {selector}")
                break
        
        if not main_content:
            main_content = soup.body if soup.body else soup
        
        # Remove script, style, and hidden elements
        for element in main_content.find_all(['script', 'style', 'noscript']):
            element.decompose()
        
        # Remove hidden elements
        for element in main_content.find_all(style=lambda s: s and 'display:none' in s.replace(' ', '')):
            element.decompose()
        
        for element in main_content.find_all(attrs={'hidden': True}):
            element.decompose()
        
        for element in main_content.find_all(attrs={'aria-hidden': 'true'}):
            element.decompose()
        
        # Extract text with structure
        lines = []
        self._extract_text_recursive(main_content, lines, level=0)
        
        # Clean up and join
        result = '\n'.join(lines)
        
        # Remove excessive blank lines (more than 2 consecutive)
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
        
        return result.strip()
    
    def _extract_text_recursive(self, element, lines: list, level: int = 0):
        """
        Recursively extract text from element and its children.
        Maintains structure and hierarchy.
        Captures URLs from hyperlinks.
        """
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                lines.append(text)
            return
        
        if not isinstance(element, Tag):
            return
        
        # Skip certain elements
        if element.name in ['script', 'style', 'noscript']:
            return
        
        # Handle hyperlinks - extract text and URL
        if element.name == 'a':
            text = element.get_text(strip=True)
            href = element.get('href', '')
            if text and href:
                # Convert relative URLs to absolute URLs
                if self.current_base_url and href:
                    absolute_url = urljoin(self.current_base_url, href)
                else:
                    absolute_url = href
                
                # Only include valid HTTP/HTTPS URLs (filter out javascript:, mailto:, etc.)
                if absolute_url.startswith('http'):
                    lines.append(f"{text} {absolute_url}")
                else:
                    # Just include the text without the URL for non-http links
                    lines.append(text)
            elif text:
                lines.append(text)
            return  # Don't process children since we already got the text
        
        # Handle specific elements
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            # Add headings with spacing
            text = element.get_text(strip=True)
            if text:
                if lines and lines[-1]:  # Add blank line before heading if not at start
                    lines.append('')
                lines.append(text + ' ')
                lines.append('')  # Add blank line after heading to separate from content
        elif element.name in ['p', 'div', 'section', 'article']:
            # Process block elements
            # Get direct text and child elements
            for child in element.children:
                self._extract_text_recursive(child, lines, level + 1)
            
            # Add spacing after block elements (if they had content)
            if element.name in ['p', 'section'] and lines and lines[-1]:
                lines.append('')
        elif element.name in ['li']:
            # List items - process children to capture links
            for child in element.children:
                self._extract_text_recursive(child, lines, level + 1)
        elif element.name in ['br']:
            # Line breaks
            lines.append('')
        elif element.name == 'summary':
            # Details/summary elements (accordion titles)
            text = element.get_text(strip=True)
            if text:
                if lines and lines[-1]:
                    lines.append('')
                lines.append(text + ' ')
        else:
            # For other elements, process children
            for child in element.children:
                self._extract_text_recursive(child, lines, level)
    
    async def process_url(self, page: Page, url: str, index: int) -> dict[str, Any]:
        """Process a single URL and extract content."""
        logger.info(f"Processing URL {index}: {url}")
        
        # Set the base URL for resolving relative links
        self.current_base_url = url
        
        try:
            # Navigate to the page
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(1)  # Let page settle
            
            # Expand all accordions
            logger.info("Expanding all accordions...")
            await self.expand_all_accordions(page)
            
            # Click through all tabs
            logger.info("Processing tabs...")
            await self.click_all_tabs(page)
            
            # Get the final HTML after all expansions
            logger.info("Extracting content...")
            html = await page.content()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract text content in natural order
            content = self.extract_text_content(soup)
            
            logger.info(f"Extracted {len(content)} characters of content")
            
            return {
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "content": content,
                "success": True
            }
            
        except PlaywrightTimeout as e:
            logger.error(f"Timeout processing {url}: {e}")
            return {
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "success": False
            }
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return {
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "success": False
            }
    
    def save_result(self, result: dict[str, Any], index: int) -> None:
        """Save a single result to a JSONL file."""
        output_file = self.output_dir / f"{self.customer_name}_content.jsonl"
        
        with output_file.open('a', encoding='utf-8') as f:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        logger.info(f"Saved result {index} to {output_file}")
    
    async def process_jsonl(self, jsonl_file: Path, max_urls: int | None = None) -> None:
        """Process all non-PDF URLs from a JSONL file."""
        # Read URLs from JSONL
        urls = []
        with jsonl_file.open('r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line.strip())
                if 'URL' in data:
                    urls.append(data['URL'])
        
        logger.info(f"Found {len(urls)} non-PDF URLs to process")
        
        if max_urls:
            urls = urls[:max_urls]
            logger.info(f"Limited to {max_urls} URLs for processing")
        
        # Process URLs with Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            try:
                for i, url in enumerate(urls, start=1):
                    result = await self.process_url(page, url, i)
                    self.save_result(result, i)
                    
                    # Small delay between requests
                    await asyncio.sleep(1)
                    
            finally:
                await browser.close()
        
        logger.info("Processing complete!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract content from web pages by expanding all elements first"
    )
    parser.add_argument(
        "--jsonl_file",
        type=Path,
        help="Path to JSONL file containing URLs"
    )
    parser.add_argument(
        "--customer_name",
        help="Customer name for output directory"
    )
    parser.add_argument(
        "--max-urls",
        type=int,
        default=None,
        help="Maximum number of URLs to process (for testing)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: data/customer_name)"
    )
    
    args = parser.parse_args()
    
    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        script_dir = Path(__file__).parent
        output_dir = script_dir / "data" / args.customer_name.lower()
    
    # Create extractor and run
    extractor = ContentExtractor(args.customer_name, output_dir)
    asyncio.run(extractor.process_jsonl(args.jsonl_file, args.max_urls))


if __name__ == "__main__":
    main()

