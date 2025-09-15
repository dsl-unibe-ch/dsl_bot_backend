from typing import List, Optional
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from w3lib.url import canonicalize_url
import yaml

def _split_csv(s: Optional[str]) -> List[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]

def _yaml_to_csv(value) -> str:
    """Convert YAML list or string into a comma-separated string for _split_csv."""
    if isinstance(value, list):
        return ",".join([str(x).strip() for x in value if str(x).strip()])
    if isinstance(value, str):
        return value
    return ""

class UnibeSpider(CrawlSpider):
    """ Minimal, configurable CrawlSpider to yield a list of URLs and PDFs (not content):
    - Seed URLs via -a seed_urls="..."
    - Allowed domains via -a allowed_domains="..."
    - Allow/Deny regex patterns via -a allow="...", -a deny="..."
    - Deny domains via -a deny_domains="..."
    - Exports each visited page URL as {"Link": "<url>"} using Scrapy's feed export (-o ...)
    - PDFs are allowed by default (we don't deny any extensions)
    """
    name = "spidey"
    custom_settings = {
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
        seed_urls: str = "",
        allowed_domains: str = "",
        allow: str = "",
        deny: str = "",
        deny_domains: str = "",
        config: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        cfg = {}
        if config:
            with open(config, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        def merged(key: str, cli_value: str) -> str:
            if cli_value:
                return cli_value
            return _yaml_to_csv(cfg.get(key, ""))

        seed_urls      = merged("seed_urls", seed_urls)
        allowed_domains= merged("allowed_domains", allowed_domains)
        allow          = merged("allow", allow)
        deny           = merged("deny", deny)
        deny_domains   = merged("deny_domains", deny_domains)

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
            self.logger.warning("No seed_urls provided. Use -a seed_urls='http://example,...'")
        self._exported = set()

    def _canon(self, url: str) -> str:
        return canonicalize_url(url, keep_fragments=False)

    def parse_start_url(self, response):
        return self.parse_item(response)

    def parse_item(self, response: scrapy.http.Response):
        url = self._canon(response.url)
        if url not in self._exported:
            self._exported.add(url)
            yield {"Link": url}

        for href in response.css('a::attr(href)').getall():
            if '.pdf' in href.lower():
                pdf_url = self._canon(response.urljoin(href))
                if pdf_url not in self._exported:
                    self._exported.add(pdf_url)
                    yield {"Pdf": pdf_url}



'''
scrapy runspider crawler/crawler.py \
  -a seed_urls="https://www.unibe.ch/innovation/index_ger.html,https://www.unibe.ch/innovation/fuer_studierende/ideenlabor/index_ger.html,https://lead.unibe.ch/forschung/lehre_im_ideenlabor/index_ger.html" \
  -a allowed_domains="www.unibe.ch,lead.unibe.ch" \
  -a allow="/innovationunibe/,/engaged_unibe/,/auf_einen_blick/,/stories_und_startups/,/partner_werden/,/innovation_guide/,/fuer_studierende/,/inspirationen_lehre/,/open_door_mornings/" \
  -a deny_domains="edit.cms.unibe.ch,edu.unibe.ch,gpv.psy.unibe.ch,ispw.unibe.ch,kpkj.psy.unibe.ch,kpp.psy.unibe.ch,philhum.unibe.ch" \
  -o data/raw/innovation.jsonl \
  -s FEED_FORMAT=jsonlines -s FEED_EXPORT_ENCODING=utf-8 \
  -s JOBDIR=data/raw/

'''