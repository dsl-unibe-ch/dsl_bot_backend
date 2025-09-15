"""Convert .mht/.mhtml to plain text with inline URLs."""

import argparse
import logging
import re
from email import message_from_binary_file
from email.message import Message
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, FeatureNotFound, NavigableString
from lxml.etree import XMLSyntaxError

# logger
logger = logging.getLogger("convert-mht-to-txt-ideenlabor")
logger.setLevel(logging.DEBUG)
logger.propagate = False
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)


def pick_html_part(msg: Message) -> tuple[str, str]:
    """Return (html_string, base_url) from the first suitable text/html part."""
    candidate = None
    base = None

    for part in msg.walk():
        if part.get_content_type().lower().startswith("text/html"):
            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            html = payload.decode(charset, errors="replace")
            cl = part.get("Content-Location")
            if cl and not cl.lower().startswith(("cid:", "data:")):
                return html, cl
            if candidate is None:
                candidate = html
                base = cl
    if candidate is None:
        error_message = "No text/html found in this part of the MHT file"
        raise RuntimeError(error_message)
    return candidate, base


def html_to_text_with_links(html: str, base_url: str | None = None) -> str:
    """Convert HTML to plain text with resolved URL."""
    try:
        soup = BeautifulSoup(html, "lxml")
    except (XMLSyntaxError, FeatureNotFound):
        soup = BeautifulSoup(html, "html.parser")

    # Drop scripts/styles/noscript
    for t in soup(["script", "style", "noscript"]):
        t.decompose()

    # Determine base URL from <base> tag if present
    base_tag = soup.find("base", href=True)
    if base_tag and base_tag.get("href"):
        base_url = base_tag["href"]

    def is_http(u: str) -> bool:
        try:
            return urlparse(u).scheme in ("http", "https")
        except ValueError:
            return False

    # Replace each <a> with its text + (resolved URL) if applicable
    for a in soup.find_all("a"):
        href = a.get("href")
        text = a.get_text(" ", strip=True)
        if href:
            resolved = urljoin(base_url or "", href)
            if is_http(resolved):
                replacement = f"{text} ({resolved})" if text else resolved
                a.replace_with(NavigableString(replacement))
                continue
        # If no usable href, just keep the visible text
        a.replace_with(NavigableString(text))

    # Get text with reasonable newlines
    raw = soup.get_text(separator="\n")

    # Normalize whitespace/newlines
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    raw = re.sub(r" *\n *", "\n", raw)
    return raw.strip() + "\n"


def convert_mht_to_text(mht_path: Path, out_path: Path) -> None:
    """Convert .mht/.mhtml to plain text with inline URLs."""
    with Path(mht_path).open(mode="rb") as f:
        msg = message_from_binary_file(f)
    html, base = pick_html_part(msg)
    text = html_to_text_with_links(html, base_url=base)
    out_path.write_text(text, encoding="utf-8")


# ---- Argument parsing and execution at top level (no main function) ----
parser = argparse.ArgumentParser(
    description="Convert .mht/.mhtml to plain text with inline URLs."
)
parser.add_argument("input", help="Path to the .mht/.mhtml file")
parser.add_argument("output", help="Path to the output .txt file")
args = parser.parse_args()

mht = Path(args.input).expanduser()
out = Path(args.output).expanduser()
convert_mht_to_text(mht, out)
logger.debug("MHT file converted to text. Wrote: %s", out)
