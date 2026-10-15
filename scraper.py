from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import (
    parse_qsl,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
)
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

BASE_DIR = Path("data")

HTML_DIR = BASE_DIR / "raw" / "html"
PDF_DIR = BASE_DIR / "raw" / "pdf"
TEXT_DIR = BASE_DIR / "processed"

METADATA_FILE = BASE_DIR / "metadata.jsonl"

SEEDS = [
    "https://bdlaws.minlaw.gov.bd/act-print-1014.html",
    "https://bdlaws.minlaw.gov.bd/act-details-1014.html",
]

ALLOWED_DOMAINS = {
    "bdlaws.minlaw.gov.bd",
}

# Keep the initial corpus focused on the Consumer Rights
# Protection Act, 2009. Add verified amendment/rules URLs
# explicitly after reviewing official sources.
TARGET_ACT_ID = "1014"

MAX_PAGES = 20
DELAY_SECONDS = 1.5
REQUEST_TIMEOUT = 30

USER_AGENT = (
    "BanglaLawAI-ResearchBot/0.1 "
    "(educational legal research project)"
)

HEADERS = {
    "User-Agent": USER_AGENT,
}

for directory in (HTML_DIR, PDF_DIR, TEXT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update(HEADERS)

robots_cache: dict[str, RobotFileParser] = {}


def allowed_domain(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()

    return any(
        host == domain or host.endswith("." + domain)
        for domain in ALLOWED_DOMAINS
    )


def normalize_url(url: str) -> str:
    """
    Normalize URLs for crawl deduplication.

    Preserve language query parameters because Bangla and English
    versions may contain different text.
    """
    parsed = urlparse(url)

    query_params = [
        (key, value)
        for key, value in parse_qsl(parsed.query)
        if key.lower() == "lang"
    ]

    normalized_query = urlencode(query_params)

    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            "",
            normalized_query,
            "",
        )
    )


def make_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def is_target_act_url(url: str) -> bool:
    """
    Accept printable/details pages for Act 1014 only.
    Ignore search pages and unrelated Acts.
    """
    parsed = urlparse(url)

    if not allowed_domain(url):
        return False

    match = re.fullmatch(
        rf"/act-(?:print|details)-{TARGET_ACT_ID}\.html",
        parsed.path,
        flags=re.IGNORECASE,
    )

    return match is not None


def is_candidate_url(url: str) -> bool:
    """
    Limit automatic crawling to the target Act's pages.

    PDFs are not automatically accepted here because a PDF's
    relevance cannot safely be established from its extension.
    Add verified official PDF URLs to SEEDS explicitly if needed.
    """
    return is_target_act_url(url)


def robots_allowed(url: str) -> bool:
    """Respect the site's robots.txt; fail closed if unavailable."""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    if origin not in robots_cache:
        robots_url = urljoin(origin, "/robots.txt")
        parser = RobotFileParser()
        parser.set_url(robots_url)

        try:
            response = session.get(
                robots_url,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[ROBOTS ERROR] {robots_url}: {exc}")
            return False

        parser.parse(response.text.splitlines())
        robots_cache[origin] = parser

    return robots_cache[origin].can_fetch(USER_AGENT, url)


def extract_html_text(html: str) -> tuple[str, list[dict]]:
    soup = BeautifulSoup(html, "html.parser")

    links = []

    for anchor in soup.find_all("a", href=True):
        links.append(
            {
                "label": anchor.get_text(" ", strip=True),
                "url": anchor["href"],
            }
        )

    # Remove page chrome and non-content elements.
    for element in soup.select(
        "script, style, nav, footer, header, "
        "noscript, form, button"
    ):
        element.decompose()

    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.body
        or soup
    )

    text = main.get_text("\n", strip=True)
    text = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text)

    return text, links


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        pages.append(
            f"[PDF page {page_number}]\n{page_text}"
        )

    return "\n\n".join(pages)


def write_metadata_record(record: dict) -> None:
    """
    Upsert by source URL so repeated runs don't duplicate records.
    """
    records_by_url = {}

    if METADATA_FILE.exists():
        with METADATA_FILE.open("r", encoding="utf-8") as file:
            for line in file:
                try:
                    existing = json.loads(line)
                except json.JSONDecodeError:
                    continue

                source_url = existing.get("source_url")

                if source_url:
                    records_by_url[source_url] = existing

    records_by_url[record["source_url"]] = record

    with METADATA_FILE.open("w", encoding="utf-8") as file:
        for existing in records_by_url.values():
            file.write(
                json.dumps(existing, ensure_ascii=False) + "\n"
            )


def save_record(
    url: str,
    title: str,
    document_type: str,
    text: str,
    raw_path: str,
) -> None:
    if not text.strip():
        print(f"[WARN] No text extracted: {url}")
        return

    doc_id = make_id(url)
    text_path = TEXT_DIR / f"{doc_id}.txt"

    text_path.write_text(text, encoding="utf-8")

    record = {
        "id": doc_id,
        "title": title,
        "source_url": url,
        "document_type": document_type,
        "raw_path": raw_path,
        "text_path": str(text_path),
        "language": "bn-or-en",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "verification_status": "pending",
        "last_verified_at": None,
    }

    write_metadata_record(record)

    print(f"[SAVED] {title or url}")


def fetch_document(url: str) -> list[tuple[str, str]]:
    """
    Fetch a permitted target-Act page and return relevant
    internal links for further crawling.
    """
    url = normalize_url(url)

    if not allowed_domain(url):
        print(f"[SKIP] Outside allowed domain: {url}")
        return []

    if not is_candidate_url(url):
        print(f"[SKIP] Not a target-Act page: {url}")
        return []

    if not robots_allowed(url):
        print(f"[SKIP] robots.txt disallows or unavailable: {url}")
        return []

    try:
        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[ERROR] {url}: {exc}")
        return []

    time.sleep(DELAY_SECONDS)

    content_type = response.headers.get(
        "Content-Type", ""
    ).lower()

    doc_id = make_id(url)

    if (
        "application/pdf" in content_type
        or url.lower().endswith(".pdf")
    ):
        raw_path = PDF_DIR / f"{doc_id}.pdf"
        raw_path.write_bytes(response.content)

        try:
            text = extract_pdf_text(raw_path)
        except Exception as exc:
            print(f"[WARN] PDF extraction failed: {url}: {exc}")
            return []

        save_record(
            url=url,
            title=raw_path.name,
            document_type="pdf",
            text=text,
            raw_path=str(raw_path),
        )

        return []

    if (
        "html" not in content_type
        and not response.text.lstrip().startswith("<")
    ):
        print(f"[SKIP] Unsupported content type: {url}")
        return []

    raw_path = HTML_DIR / f"{doc_id}.html"
    raw_path.write_text(response.text, encoding="utf-8")

    text, discovered_links = extract_html_text(response.text)

    soup = BeautifulSoup(response.text, "html.parser")
    title = (
        soup.title.get_text(" ", strip=True)
        if soup.title
        else url
    )

    save_record(
        url=url,
        title=title,
        document_type="html",
        text=text,
        raw_path=str(raw_path),
    )

    relevant_links = []

    for link in discovered_links:
        absolute_url = normalize_url(
            urljoin(url, link["url"])
        )

        if not allowed_domain(absolute_url):
            continue

        if is_candidate_url(absolute_url):
            relevant_links.append(
                (link["label"], absolute_url)
            )

    return relevant_links


def main() -> None:
    queue = []

    for seed in SEEDS:
        normalized = normalize_url(seed)

        if is_candidate_url(normalized):
            queue.append(normalized)
        else:
            print(f"[SEED SKIP] Not a target-Act URL: {seed}")

    seen = set()

    while queue and len(seen) < MAX_PAGES:
        url = queue.pop(0)

        if url in seen:
            continue

        seen.add(url)

        print(f"[FETCH {len(seen)}/{MAX_PAGES}] {url}")

        discovered = fetch_document(url)

        for _, linked_url in discovered:
            linked_url = normalize_url(linked_url)

            if (
                linked_url not in seen
                and linked_url not in queue
            ):
                queue.append(linked_url)

    print(f"\nFinished. Visited {len(seen)} URLs.")
    print(f"Extracted text: {TEXT_DIR.resolve()}")
    print(f"Metadata: {METADATA_FILE.resolve()}")


if __name__ == "__main__":
    main()