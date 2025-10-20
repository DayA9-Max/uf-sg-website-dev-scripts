from bs4 import BeautifulSoup
import requests

from config import DOWNLOAD_DIR, PDF_URLS_PATH, SCRAPER_SOURCE_URL

download_folder = DOWNLOAD_DIR

# Create the download folder if it doesn't exist
download_folder.mkdir(parents=True, exist_ok=True)

response = requests.get(SCRAPER_SOURCE_URL)
soup = BeautifulSoup(response.content, 'html.parser')

pdf_links_with_keywords = []

for link in soup.find_all('a', href=True):
    href = link['href'].lower()
    if href.endswith('.pdf') and ('ssb' in href or 'bill' in href):
        pdf_links_with_keywords.append(link['href'])

with PDF_URLS_PATH.open('w') as file:
    for url in pdf_links_with_keywords:
        file.write(url + '\n')

for pdf_link in pdf_links_with_keywords:
    # Extract the filename from the URL
    filename = pdf_link.split('/')[-1]

    # Construct the full path to save the file
    file_path = download_folder / filename

    # Download the PDF file
    pdf_response = requests.get(pdf_link)
    with file_path.open('wb') as pdf_file:
        pdf_file.write(pdf_response.content)
        print(f"Downloaded: {filename}")
