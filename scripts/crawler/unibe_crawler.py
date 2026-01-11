"""Minimal, configurable CrawlSpider to yield a list of URLs and PDFs (not content)."""

import logging
from pathlib import Path
from typing import Any, ClassVar

import scrapy
import yaml
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from w3lib.url import canonicalize_url

# logger
logger = logging.getLogger("unibe-crawler")
logger.setLevel(logging.DEBUG)
logger.propagate = False
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)


def _split_csv(s: str | None) -> list[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def _yaml_to_csv(value: list | str) -> str:
    """Convert YAML list or string into a comma-separated string for _split_csv."""
    if isinstance(value, list):
        return ",".join([str(x).strip() for x in value if str(x).strip()])
    if isinstance(value, str):
        return value
    return ""


class UnibeSpider(CrawlSpider):
    """Minimal, configurable CrawlSpider to yield a list of URLs and PDFs (not content).

    - Seed URLs via -a seed_urls="..."
    - Allowed domains via -a allowed_domains="..."
    - Allow/Deny regex patterns via -a allow="...", -a deny="..."
    - Deny domains via -a deny_domains="..."
    - Exports page URL as {"URL": "<url>"} using feed export (-o ...)
    - PDFs are allowed by default (we don't deny any extensions)
    """

    name = "spidey"
    custom_settings: ClassVar[dict[str, object]] = {
        "ROBOTSTXT_OBEY": True,
        "LOG_LEVEL": "INFO",
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 0.5,
        "AUTOTHROTTLE_MAX_DELAY": 5.0,
        "DOWNLOAD_DELAY": 0.25,
        "DEPTH_LIMIT": 12,
    }

    def __init__(
        self,
        config: str | None = None,
        **kwargs: str,
    ) -> None:
        """Initialize the spider."""
        super().__init__(**kwargs)
        cfg: dict[str, Any] = {}
        if config:
            with Path(config).open(encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}

        # Read static_pdfs from config
        self.static_pdfs = cfg.get("static_pdfs", [])

        def merged(key: str, cli_value: str) -> str:
            return cli_value or _yaml_to_csv(cfg.get(key, ""))

        seed_urls = merged("seed_urls", kwargs.get("seed_urls", ""))
        allowed_domains = merged("allowed_domains", kwargs.get("allowed_domains", ""))
        allow = merged("allow", kwargs.get("allow", ""))
        deny = merged("deny", kwargs.get("deny", ""))
        deny_domains = merged("deny_domains", kwargs.get("deny_domains", ""))

        # Parse args (unchanged logic)
        self.start_urls = _split_csv(seed_urls)
        self.allowed_domains = _split_csv(allowed_domains)
        allow_patterns = tuple(_split_csv(allow))
        deny_patterns = tuple(_split_csv(deny))
        deny_domains_list = tuple(_split_csv(deny_domains))

        # Build a single dynamic rule (unchanged logic)
        link_extractor = LinkExtractor(
            allow=allow_patterns,
            deny=deny_patterns,
            allow_domains=self.allowed_domains or (),
            deny_domains=deny_domains_list or (),
            unique=True,
        )
        self.rules = (Rule(link_extractor, callback="parse_item", follow=True),)
        self._compile_rules()

        if not self.start_urls:
            self.logger.warning(
                "No seed_urls provided. Use -a seed_urls='http://example,...'"
            )
        self._exported = set()

    def _canon(self, url: str) -> str:
        """Canonicalize the url."""
        return canonicalize_url(url, keep_fragments=False)

    def start_requests(self):
        """Start requests - yield static PDFs first, then normal crawling."""
        # First, yield all static PDFs
        for pdf_url in self.static_pdfs:
            canonical_url = self._canon(pdf_url)
            if canonical_url not in self._exported:
                self._exported.add(canonical_url)
                logger.info(f"Yielding static PDF: {canonical_url}")
                yield {"PDF": canonical_url}
        
        # Then proceed with normal crawling
        for url in self.start_urls:
            yield scrapy.Request(url, dont_filter=True)

    def parse_start_url(self, response: scrapy.http.Response) -> scrapy.http.Response:
        """Parse the start url."""
        return self.parse_item(response)

    def parse_item(self, response: scrapy.http.Response) -> scrapy.http.Response:
        """Parse the item."""
        url = self._canon(response.url)
        if url not in self._exported:
            self._exported.add(url)
            yield {"URL": url}

        for href in response.css("a::attr(href)").getall():
            if ".pdf" in href.lower():
                pdf_url = self._canon(response.urljoin(href))
                if pdf_url not in self._exported:
                    self._exported.add(pdf_url)
                    yield {"PDF": pdf_url}
