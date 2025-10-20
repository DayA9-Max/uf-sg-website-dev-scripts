"""Utilities for downloading UF SG Senate legislation PDFs."""

from __future__ import annotations
from bs4 import BeautifulSoup
import requests
import os
from typing import Iterable, List
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

DEFAULT_URL = "https://sg.ufl.edu/branches/legislative/senate-resources/"


def _extract_pdf_links(url: str) -> List[str]:
    """Return PDF URLs containing key phrases from the Senate resources page."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    pdf_links_with_keywords: List[str] = []

    for link in soup.find_all("a", href=True):
        href = link["href"].lower()
        if href.endswith(".pdf") and ("ssb" in href or "bill" in href):
            pdf_links_with_keywords.append(urljoin(url, link["href"]))

    return pdf_links_with_keywords


def _write_url_list(urls: Iterable[str], destination: str) -> None:
    os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
    with open(destination, "w", encoding="utf-8") as file:
        for pdf_url in urls:
            file.write(pdf_url + "\n")


def download_legislation_pdfs(
    url: str = DEFAULT_URL,
    download_folder: str = "bills",
    url_output_path: str = "pdf_urls.txt",
    ) -> List[str]:
    """Download Senate legislation PDFs and return a list of saved file paths."""
    
    # Create the download folder if it doesn't exist
    os.makedirs(download_folder, exist_ok=True)

    pdf_links_with_keywords = _extract_pdf_links(url)

    if url_output_path:
        _write_url_list(pdf_links_with_keywords, url_output_path)

    downloaded_files: List[str] = []
    for pdf_link in pdf_links_with_keywords:
        # Extract the filename from the URL
        filename = pdf_link.split("/")[-1]
        # Construct the full path to save the file
        file_path = os.path.join(download_folder, filename)
        # Download the PDF file
        pdf_response = requests.get(pdf_link, timeout=60)
        pdf_response.raise_for_status()
        with open(file_path, "wb") as pdf_file:
            pdf_file.write(pdf_response.content)
        downloaded_files.append(file_path)
        print(f"Downloaded: {filename}")

    return downloaded_files


def main() -> None:
    """CLI entry point to download PDFs using default settings."""
    download_legislation_pdfs()


if __name__ == "__main__":
    main()
    # Script to download UF SG Senate legislation PDFs

