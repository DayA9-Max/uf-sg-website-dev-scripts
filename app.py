"""Utilities for downloading UF SG Senate legislation PDFs."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Iterable, List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import DOWNLOAD_DIR, PDF_URLS_PATH, SCRAPER_SOURCE_URL

DEFAULT_URL = SCRAPER_SOURCE_URL
REQUEST_TIMEOUT_SECONDS = 30
KEYWORD_FILTERS = ("ssb", "bill")

logger = logging.getLogger(__name__)


def _write_url_list(urls: Iterable[str], destination: str | Path) -> None:
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_text("\n".join(urls) + ("\n" if urls else ""), encoding="utf-8")


def _extract_pdf_links(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    candidates = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href:
            continue

        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        path_lower = parsed.path.lower()
        if not path_lower.endswith(".pdf"):
            continue

        candidate_text = f"{full_url} {anchor.get_text(' ', strip=True)}".lower()
        if any(keyword in candidate_text for keyword in KEYWORD_FILTERS):
            candidates.add(full_url)

    return sorted(candidates)


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _filename_from_url(pdf_url: str) -> str:
    parsed = urlparse(pdf_url)
    filename = Path(parsed.path).name
    return filename or "document.pdf"


def download_legislation_pdfs(
    url: str = DEFAULT_URL,
    download_folder: str | Path = DOWNLOAD_DIR,
    url_output_path: str | Path = PDF_URLS_PATH,
) -> List[Path]:
    """Scrape ``url`` and download matching Senate PDF documents.

    Existing files are only overwritten if the content hash changes.
    Returns a list of local paths for downloaded or reused files.
    """

    download_dir_path = Path(download_folder)
    download_dir_path.mkdir(parents=True, exist_ok=True)

    logger.info("Fetching senate resources page: %s", url)
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    pdf_links_with_keywords = _extract_pdf_links(response.text, url)
    _write_url_list(pdf_links_with_keywords, url_output_path)
    logger.info("Discovered %d matching PDF links", len(pdf_links_with_keywords))

    downloaded_files: List[Path] = []
    for pdf_link in pdf_links_with_keywords:
        filename = _filename_from_url(pdf_link)
        file_path = download_dir_path / filename

        try:
            pdf_response = requests.get(pdf_link, timeout=REQUEST_TIMEOUT_SECONDS)
            pdf_response.raise_for_status()
            remote_bytes = pdf_response.content
        except requests.RequestException as exc:
            logger.warning("Failed to download %s: %s", pdf_link, exc)
            continue

        if file_path.exists() and _sha256_file(file_path) == _sha256_bytes(remote_bytes):
            logger.info("Unchanged file, skipping rewrite: %s", file_path.name)
        else:
            file_path.write_bytes(remote_bytes)
            logger.info("Saved %s", file_path.name)

        downloaded_files.append(file_path)

    return downloaded_files


def main() -> None:
    """CLI entry point to download PDFs using default settings."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    download_legislation_pdfs()


if __name__ == "__main__":
    main()
