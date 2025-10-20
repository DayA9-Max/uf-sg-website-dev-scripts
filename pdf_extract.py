"""Extract structured bill metadata from PDFs using OpenAI."""

from __future__ import annotations
import os

import pdfplumber
import json
import logging
from typing import Callable, Iterable, List
from textwrap import dedent
from dotenv import load_dotenv
from pydantic import ValidationError

from schemas import BillMetadata

from config import BILL_RESULTS_PATH, PDF_EXTRACTION_INPUT_DIR

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


PRIMARY_PROMPT = dedent(
    """
    You are a helpful assistant that returns to me properly formatted json objects in the format
    {"id": "", "title":  "",  "author": "", "sponsor": "", "summary": "",  "status": ""} extracted from the text I provide. Id is at the beginning of the text in the format "XXXX-XXXX" where X is an integer. Summary is a 100 word max summary that does not include authors or sponsors in the summary. Do not include any special escaping characters such as line breaks.
    If the data includes 3000 J. Wayne Reitz Union PO ... or similar, ensure the "status" is "PASSED". Else the "status" property is "TBD".
    This summary is bad: Resolution Celebrating 50 Years of Women’s Athletics at the University of Florida. Sponsored by Senator Jonathan Stephens, Senator Oscar Santiago, Senator Raj Mia, Senator Catherine Gomez, Senator Taylor Hoerle, Senator Isabelle Gerzenshtein, Senator Hana Ali, Senator Savanah Partridge, Deputy Minority Party Leader Mohammed Faisal, Member-at-Large Jacey Cable, Judiciary Vice-Chair Mason Solomon, Senator Bronson Allemand, Senator Saketh Damera, Senator Jacob Ka.
    This summary is good: The University of Florida Student Senate acknowledges the remarkable achievements of the Women's Athletics program, which has produced 92 Olympians earning a total of 64 Olympic medals. In recognition of the program's 50th anniversary and the pioneering efforts of Dr. Ruth Alexander, Donna Deutsch, Linda Hall Thornton, and Mimi Ryan in advocating for Women's Athletics in 1972, the Student Senate honors their contributions. Additionally, the Senate expresses admiration for the female athletes representing the Florida Gators, applauding their dedication, perseverance, and commitment to the university. Lastly, the University of Florida Student Senate celebrates the 50th anniversary of the Women's Athletics program at the university.
    This summary is bad: This bill, authored by Judiciary Chairman John Brinkman, aims to modernize and reform Senate meetings. It has several sponsors, including Judiciary Vice-Chairman Mason Solomon, Senator Mara Vaknin, Senator Julia Haley, Senator Taylor Soukup, Member-at-Large Jacey Cable, Senator Jagger Leach, and Senator Sidney Ruedas. The bill proposes amendments to Rule I, which governs the officers of the Senate. One of the key changes is the process for electing the Senate President, which would occur at the first meeting following the validation of Senate election results. The bill seeks to bring efficiency and transparency to Senate meetings.
    This summary is good: This bill, authored by Judiciary Chairman John Brinkman, aims to modernize and reform Senate meetings by proposing amendments to Rule I, which governs the officers of the Senate. The key change includes a revised process for electing the Senate President immediately after validating Senate election results. The bill's objective is to enhance efficiency and transparency in Senate meetings.
    This is a bad summary: "Each February commemorates Black History Month, a period which honors and appreciates the rich culture, history, and contributions of Black and African Americans throughout their continuous str", it is not fully complete
    Summaries must be full senetences
    """
).strip()

SECONDARY_PROMPT = dedent(
    """
    Please return a PROPERLY formatted JSON string, your last response was not properly formatted. The json should be parseable by python. You are a helpful assistant that returns to me properly formatted json objects in the format
    {"id": "", "title":  "",  "author": "", "sponsor": "", "summary": "",  "status": "TBD"} extracted from the text I provide. Id is at the beginning of the text in the format "XXXX-XXXX" where X is an integer. Summary is a 100 word max summary that does not include authors or sponsors in the summary. Do not include any special escaping characters such as line breaks.
    This summary is bad: Resolution Celebrating 50 Years of Women’s Athletics at the University of Florida. Sponsored by Senator Jonathan Stephens, Senator Oscar Santiago, Senator Raj Mia, Senator Catherine Gomez, Senator Taylor Hoerle, Senator Isabelle Gerzenshtein, Senator Hana Ali, Senator Savanah Partridge, Deputy Minority Party Leader Mohammed Faisal, Member-at-Large Jacey Cable, Judiciary Vice-Chair Mason Solomon, Senator Bronson Allemand, Senator Saketh Damera, Senator Jacob Ka.
    This summary is good: The University of Florida Student Senate acknowledges the remarkable achievements of the Women's Athletics program, which has produced 92 Olympians earning a total of 64 Olympic medals. In recognition of the program's 50th anniversary and the pioneering efforts of Dr. Ruth Alexander, Donna Deutsch, Linda Hall Thornton, and Mimi Ryan in advocating for Women's Athletics in 1972, the Student Senate honors their contributions. Additionally, the Senate expresses admiration for the female athletes representing the Florida Gators, applauding their dedication, perseverance, and commitment to the university. Lastly, the University of Florida Student Senate celebrates the 50th anniversary of the Women's Athletics program at the university.
    This summary is bad: This bill, authored by Judiciary Chairman John Brinkman, aims to modernize and reform Senate meetings. It has several sponsors, including Judiciary Vice-Chairman Mason Solomon, Senator Mara Vaknin, Senator Julia Haley, Senator Taylor Soukup, Member-at-Large Jacey Cable, Senator Jagger Leach, and Senator Sidney Ruedas. The bill proposes amendments to Rule I, which governs the officers of the Senate. One of the key changes is the process for electing the Senate President, which would occur at the first meeting following the validation of Senate election results. The bill seeks to bring efficiency and transparency to Senate meetings.
    This summary is good: This bill, authored by Judiciary Chairman John Brinkman, aims to modernize and reform Senate meetings by proposing amendments to Rule I, which governs the officers of the Senate. The key change includes a revised process for electing the Senate President immediately after validating Senate election results. The bill's objective is to enhance efficiency and transparency in Senate meetings.
    This is a bad summary: "Each February commemorates Black History Month, a period which honors and appreciates the rich culture, history, and contributions of Black and African Americans throughout their continuous str", it is not fully complete
    Summaries must be full senetences
    """
).strip()


def extract_bill_number(title: str) -> str:
    """Return the bill number extracted from ``title`` if present."""

    pattern = re.compile(r"\d\d\d\d-\d\d\d\d", re.IGNORECASE)
    match = re.search(pattern, title)
    if match:
        return "SSB " + match.group()
    return title

def _safe_extract_text(page) -> str:
    """Return extracted text for a pdfplumber page, defaulting to an empty string."""
    return page.extract_text() or ""


def extract_beginning(pdf_path: str) -> str:
    """Read the opening pages of ``pdf_path`` and return their text."""
    with pdfplumber.open(pdf_path) as pdf:
        page_texts = []
        page_count = len(pdf.pages)
        for index in range(min(2, page_count)):
            text = _safe_extract_text(pdf.pages[index])
            if text:
                page_texts.append(text)

        combined_text = "\n".join(page_texts)

        if not combined_text:
            logger.warning("No text extracted from %s", pdf_path)

        if len(combined_text) > 800:
            return combined_text[:800]
        return combined_text


def _build_messages(prompt: str, content: str) -> List[dict]:
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": content},
    ]


def generate_message(content: str) -> List[dict]:
    return _build_messages(PRIMARY_PROMPT, content)


def generate_message_second(content: str) -> List[dict]:
    return _build_messages(SECONDARY_PROMPT, content)


def get_gpt_info(message: Iterable[dict]) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=list(message),
        temperature=1,
        max_tokens=1500,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    return response["choices"][0]["message"]["content"]


def _process_file(
    pdf_folder: str,
    filename: str,
    message_builder: Callable[[str], Iterable[dict]],
) -> dict:
    pdf_path = os.path.join(pdf_folder, filename)
    message = message_builder(extract_beginning(pdf_path))
    logger.info("Sending extracted text for %s", filename)

    bill_info = get_gpt_info(message)
    bill_as_json = json.loads(bill_info)
    bill_as_json["id"] = extract_bill_number(filename)
    return bill_as_json


# pdf_folder = 'bills-converted'
pdf_folder = PDF_EXTRACTION_INPUT_DIR

if not os.path.isdir(pdf_folder):
    raise FileNotFoundError(f"PDF folder does not exist: {pdf_folder}")

for pdf_file in sorted(pdf_folder.glob("*.pdf")):
    message = generate_message(extract_beginning(pdf_file))
    print("Extraction complete: " + pdf_file.name)
    print("="*40)

    bill_info = get_gpt_info(message)
    try:
        bill_as_json = json.loads(bill_info)
        bill_as_json["id"] = extract_bill_number(pdf_file.name)
        results.append(bill_as_json)
    except:
        print("Error " + pdf_file.name)
        error_paths.append(pdf_file)
    print(len(results))

for pdf_file in error_paths:
    if pdf_file.suffix.lower() == '.pdf':
        message = generate_message_second(extract_beginning(pdf_file))
        print("Extraction complete: " + pdf_file.name)
        print("="*40)

    second_pass_failures: List[str] = []
    for filename in error_paths:
        try:
            bill_as_json = json.loads(bill_info)
            bill_as_json["id"] = extract_bill_number(pdf_file.name)
            results.append(bill_as_json)
        except:
            print("Error " + pdf_file.name)
            error_paths.append(pdf_file)
        print(len(results))

    logging.basicConfig(level=logging.INFO)
    extract_metadata()

with BILL_RESULTS_PATH.open('w') as json_file:
    json.dump(results, json_file, indent=4)

if __name__ == "__main__":
    main()