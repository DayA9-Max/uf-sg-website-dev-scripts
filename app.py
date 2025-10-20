"""Utilities for downloading UF SG Senate legislation PDFs."""

from __future__ import annotations
from bs4 import BeautifulSoup
import requests

from config import DOWNLOAD_DIR, PDF_URLS_PATH, SCRAPER_SOURCE_URL

download_folder = DOWNLOAD_DIR

# Create the download folder if it doesn't exist
download_folder.mkdir(parents=True, exist_ok=True)

response = requests.get(SCRAPER_SOURCE_URL)
soup = BeautifulSoup(response.content, 'html.parser')

def _write_url_list(urls: Iterable[str], destination: str) -> None:
    os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
    with open(destination, "w", encoding="utf-8") as file:
        for pdf_url in urls:
            file.write(pdf_url + "\n")


with PDF_URLS_PATH.open('w') as file:
    for url in pdf_links_with_keywords:
        file.write(url + '\n')

    pdf_links_with_keywords = _extract_pdf_links(url)

    # Construct the full path to save the file
    file_path = download_folder / filename

    # Download the PDF file
    pdf_response = requests.get(pdf_link)
    with file_path.open('wb') as pdf_file:
        pdf_file.write(pdf_response.content)
        print(f"Downloaded: {filename}")

    return downloaded_files


def main() -> None:
    """CLI entry point to download PDFs using default settings."""
    download_legislation_pdfs()


if __name__ == "__main__":
    main()
    # Script to download UF SG Senate legislation PDFs

