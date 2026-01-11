"""
PDF content extractor that processes PDF files and extracts text content
in the same format as the URL content extractor.
"""

import json
import logging
from pathlib import Path
from typing import Any
import argparse
from datetime import datetime, timezone
import os
import tempfile
from urllib.parse import urlparse
import requests
import pdfplumber

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PDFContentExtractor:
    """Extract content from PDF files."""
    
    def __init__(self, customer_name: str, output_dir: Path, download_dir: Path | None = None):
        self.customer_name = customer_name
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up download directory for URL-based PDFs
        if download_dir:
            self.download_dir = download_dir
        else:
            # Default: data/customer_name/raw/pdf_files
            script_dir = Path(__file__).parent
            self.download_dir = script_dir / "data" / customer_name.lower() / "raw" / "pdf_files"
        
        self.download_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"PDF download directory: {self.download_dir}")
    
    def is_url(self, path_str: str) -> bool:
        """Check if the path is a URL (http or https)."""
        return path_str.startswith('http://') or path_str.startswith('https://')
    
    def download_pdf(self, url: str) -> Path | None:
        """Download PDF from URL to download directory."""
        try:
            logger.info(f"Downloading PDF from: {url}")
            
            # Generate filename from URL
            parsed_url = urlparse(url)
            filename = Path(parsed_url.path).name
            if not filename or not filename.endswith('.pdf'):
                # Generate a filename based on URL hash if needed
                import hashlib
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                filename = f"downloaded_{url_hash}.pdf"
            
            local_path = self.download_dir / filename
            
            # Download the file
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Save to local file
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded to: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Error downloading PDF from {url}: {e}")
            return None
    
    def get_file_modified_date(self, file_path: Path) -> str:
        """Get the last modified date of a file in ISO format."""
        try:
            timestamp = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return dt.isoformat()
        except Exception as e:
            logger.warning(f"Could not get modified date for {file_path}: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text from PDF using pdfplumber."""
        content_parts = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text()
                    if text:
                        content_parts.append(text)
                    logger.debug(f"Extracted page {page_num}/{len(pdf.pages)}")
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num}: {e}")
        
        return '\n\n'.join(content_parts)
    
    def clean_text_content(self, content: str) -> str:
        """Clean up extracted text content."""
        # Remove excessive blank lines (more than 2 consecutive)
        while '\n\n\n' in content:
            content = content.replace('\n\n\n', '\n\n')
        
        return content.strip()
    
    def process_pdf(self, pdf_path: Path, index: int, original_url: str | None = None) -> dict[str, Any]:
        """Process a single PDF file and extract content."""
        logger.info(f"Processing PDF {index}: {pdf_path.name}")
        
        try:
            # Extract content
            content = self.extract_text_from_pdf(pdf_path)
            
            # Clean up content
            content = self.clean_text_content(content)
            
            # Get file modified date
            date_modified = self.get_file_modified_date(pdf_path)
            
            logger.info(f"Extracted {len(content)} characters from {pdf_path.name}")
            
            result = {
                "url": original_url if original_url else str(pdf_path.absolute()),
                "filename": pdf_path.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "date_modified": date_modified,
                "content": content,
                "success": True
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path.name}: {e}")
            return {
                "url": original_url if original_url else str(pdf_path.absolute()),
                "filename": pdf_path.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "date_modified": None,
                "error": str(e),
                "success": False
            }
    
    def save_result(self, result: dict[str, Any], index: int) -> None:
        """Save a single result to a JSONL file."""
        output_file = self.output_dir / f"{self.customer_name}_content.jsonl"
        
        with output_file.open('a', encoding='utf-8') as f:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        logger.info(f"Saved result {index} to {output_file}")
    
    def process_jsonl(self, jsonl_file: Path, max_pdfs: int | None = None) -> None:
        """Process all PDF URLs from a JSONL file."""
        # Read PDF URLs/paths from JSONL
        pdf_links = []
        with jsonl_file.open('r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line.strip())
                # Check for 'PDF' key (preferred) or 'Link' key with .pdf extension
                if 'PDF' in data:
                    pdf_links.append(data['PDF'])
                elif 'URL' in data:
                    link = data['URL']
                    # Check if it's a PDF link
                    if link.lower().endswith('.pdf'):
                        pdf_links.append(link)
        
        logger.info(f"Found {len(pdf_links)} PDF files to process")
        
        if max_pdfs:
            pdf_links = pdf_links[:max_pdfs]
            logger.info(f"Limited to {max_pdfs} PDFs for processing")
        
        # Process each PDF
        for i, pdf_link in enumerate(pdf_links, start=1):
            downloaded_file = None
            original_url = None
            
            try:
                # Check if it's a URL or local path
                if self.is_url(pdf_link):
                    # Download the PDF first
                    original_url = pdf_link
                    downloaded_file = self.download_pdf(pdf_link)
                    
                    if not downloaded_file:
                        logger.error(f"Failed to download PDF {i}: {pdf_link}")
                        continue
                    
                    pdf_path = downloaded_file
                else:
                    # Local file path
                    pdf_path = Path(pdf_link)
                    
                    if not pdf_path.exists():
                        logger.error(f"PDF file not found {i}: {pdf_path}")
                        continue
                
                # Process the PDF
                result = self.process_pdf(pdf_path, i, original_url)
                
                # Only save successful results
                if result.get('success', False):
                    self.save_result(result, i)
                else:
                    logger.error(f"Failed to process PDF {i}: {result.get('url')} - {result.get('error')}")
                
            finally:
                # Clean up downloaded file
                if downloaded_file and downloaded_file.exists():
                    try:
                        downloaded_file.unlink()
                        logger.info(f"Deleted downloaded file: {downloaded_file}")
                    except Exception as e:
                        logger.warning(f"Could not delete downloaded file {downloaded_file}: {e}")
        
        logger.info("Processing complete!")
    
    def process_directory(self, pdf_dir: Path, max_pdfs: int | None = None, recursive: bool = False) -> None:
        """Process all PDF files in a directory."""
        # Check if directory exists
        if not pdf_dir.exists():
            logger.warning(f"PDF directory does not exist: {pdf_dir}")
            logger.info("No PDFs to process. To add PDFs:")
            logger.info(f"  1. Place PDF files in: {pdf_dir}")
            logger.info(f"  2. Or use --jsonl_file to download PDFs from URLs")
            logger.info(f"  3. Or use --pdf_dir to specify a different directory")
            return
        
        # Find all PDF files
        logger.info(f"Scanning directory: {pdf_dir}")
        if recursive:
            logger.info("  Searching recursively in subdirectories...")
            pdf_files = list(pdf_dir.rglob('*.pdf')) + list(pdf_dir.rglob('*.PDF'))
        else:
            pdf_files = list(pdf_dir.glob('*.pdf')) + list(pdf_dir.glob('*.PDF'))
        
        logger.info(f"Found {len(pdf_files)} local PDF file(s) in {pdf_dir}")
        
        if len(pdf_files) == 0:
            logger.info("No PDFs found. To add PDFs:")
            logger.info(f"  1. Place PDF files in: {pdf_dir}")
            logger.info(f"  2. Or use --jsonl_file to download PDFs from URLs")
            logger.info(f"  3. Or use --pdf_dir to specify a different directory")
            return
        
        if max_pdfs:
            pdf_files = pdf_files[:max_pdfs]
            logger.info(f"Limited to {max_pdfs} PDFs for processing")
        
        # List the PDF files found
        logger.info("PDF files to process:")
        for i, pdf_path in enumerate(pdf_files, start=1):
            logger.info(f"  {i}. {pdf_path.name}")
        
        # Process each PDF
        for i, pdf_path in enumerate(pdf_files, start=1):
            result = self.process_pdf(pdf_path, i)
            self.save_result(result, i)
        
        logger.info("Processing complete!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract content from PDF files"
    )
    
    # Input source
    parser.add_argument(
        "--jsonl_file",
        type=Path,
        default=None,
        help="Path to JSONL file containing PDF paths/URLs"
    )
    parser.add_argument(
        "--pdf_dir",
        type=Path,
        default=None,
        help="Directory containing PDF files to process (default: data/customer_name/raw/pdf_files)"
    )
    
    parser.add_argument(
        "--customer_name",
        required=True,
        help="Customer name for output file naming"
    )
    parser.add_argument(
        "--max_pdfs",
        type=int,
        default=None,
        help="Maximum number of PDFs to process (for testing)"
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=None,
        help="Output directory (default: data/customer_name)"
    )
    parser.add_argument(
        "--download_dir",
        type=Path,
        default=None,
        help="Directory to download PDF URLs (default: data/customer_name/raw/pdf_files)"
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively search for PDFs in subdirectories (only with --pdf-dir)"
    )
    
    args = parser.parse_args()
    
    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        script_dir = Path(__file__).parent
        output_dir = script_dir / "data" / args.customer_name.lower()
    
    # Create extractor
    extractor = PDFContentExtractor(args.customer_name, output_dir, args.download_dir)
    
    # Process based on input type
    if args.jsonl_file:
        # Process PDFs from JSONL (URLs will be downloaded, local paths used directly)
        extractor.process_jsonl(args.jsonl_file, args.max_pdfs)
    else:
        # Process local PDFs from directory
        if args.pdf_dir:
            pdf_dir = args.pdf_dir
            logger.info(f"Using specified PDF directory: {pdf_dir}")
        else:
            # Default: look in data/customer_name/raw/pdf_files
            pdf_dir = extractor.download_dir
            logger.info(f"No PDF directory specified, using default: {pdf_dir}")
        
        extractor.process_directory(pdf_dir, args.max_pdfs, args.recursive)


if __name__ == "__main__":
    main()

