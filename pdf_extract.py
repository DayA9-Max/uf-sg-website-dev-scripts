"""Extract structured bill metadata from PDFs using offline parsing + OpenAI fallback."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from textwrap import dedent
from typing import Dict, Iterable, List

import pdfplumber
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from config import BILL_RESULTS_PATH, PDF_EXTRACTION_INPUT_DIR
from schemas import BillMetadata

load_dotenv()

logger = logging.getLogger(__name__)

PRIMARY_PROMPT = dedent(
    """
    You are a helpful assistant that returns to me properly formatted json objects in the format
    {"id": "", "title":  "",  "author": "", "sponsor": "", "summary": "",  "status": ""} extracted from the text I provide. Id is at the beginning of the text in the format "XXXX-XXXX" where X is an integer. Summary is a 100 word max summary that does not include authors or sponsors in the summary. Do not include any special escaping characters such as line breaks.
    If the data includes 3000 J. Wayne Reitz Union PO ... or similar, ensure the "status" is "PASSED". Else the "status" property is "TBD".
    Summaries must be full sentences.
    """
).strip()

SECONDARY_PROMPT = dedent(
    """
    Please return a PROPERLY formatted JSON string, your last response was not properly formatted.
    Return only parseable JSON in this shape:
    {"id": "", "title": "", "author": "", "sponsor": "", "summary": "", "status": "TBD"}
    Id is in the form XXXX-XXXX. Summary is <=100 words and should not include author/sponsor lists.
    """
).strip()


def extract_bill_number(title: str) -> str:
    """Return canonical bill identifier extracted from ``title`` when present."""
    match = re.search(r"\d{4}-\d{4}", title, re.IGNORECASE)
    if match:
        return f"SSB {match.group()}"
    return title


def _safe_extract_text(page) -> str:
    return page.extract_text() or ""


def extract_beginning(pdf_path: str | Path) -> str:
    """Read the opening pages of ``pdf_path`` and return bounded text."""
    with pdfplumber.open(pdf_path) as pdf:
        page_texts: List[str] = []
        for index in range(min(2, len(pdf.pages))):
            text = _safe_extract_text(pdf.pages[index]).strip()
            if text:
                page_texts.append(text)

    combined_text = "\n".join(page_texts)
    if not combined_text:
        logger.warning("No text extracted from %s", pdf_path)
    return combined_text[:1200]


def _build_messages(prompt: str, content: str) -> List[dict]:
    return [{"role": "system", "content": prompt}, {"role": "user", "content": content}]


def _build_offline_metadata(filename: str, text: str) -> Dict[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    joined = " ".join(lines)

    title = lines[0] if lines else filename
    author = ""
    sponsor = ""

    author_match = re.search(r"(?:author|authored by)\s*[:\-]\s*([^\n\.]+)", joined, re.IGNORECASE)
    if author_match:
        author = author_match.group(1).strip()

    sponsor_match = re.search(r"(?:sponsor|sponsored by)\s*[:\-]\s*([^\n\.]+)", joined, re.IGNORECASE)
    if sponsor_match:
        sponsor = sponsor_match.group(1).strip()

    summary_words = joined.split()[:100]
    summary = " ".join(summary_words)
    status = "PASSED" if "3000 J. Wayne Reitz Union" in joined else "TBD"

    return {
        "id": extract_bill_number(filename),
        "title": title,
        "author": author,
        "sponsor": sponsor,
        "summary": summary,
        "status": status,
    }


def _get_openai_client() -> OpenAI | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def _get_gpt_info(client: OpenAI, messages: Iterable[dict]) -> str:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=list(messages),
        temperature=0.2,
        max_tokens=1000,
    )
    return response.choices[0].message.content or "{}"


def _load_existing_results(path: Path) -> Dict[str, dict]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, list):
        return {}
    existing = {}
    for item in data:
        if isinstance(item, dict):
            bill_id = str(item.get("id", "")).strip()
            if bill_id:
                existing[bill_id] = item
    return existing


def _load_hash_cache(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_with_optional_llm(client: OpenAI | None, filename: str, text: str) -> Dict[str, str]:
    offline = _build_offline_metadata(filename, text)
    if client is None:
        return offline

    for prompt in (PRIMARY_PROMPT, SECONDARY_PROMPT):
        try:
            message = _build_messages(prompt, text)
            raw = _get_gpt_info(client, message)
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                merged = offline.copy()
                for key in ("title", "author", "sponsor", "summary", "status"):
                    value = parsed.get(key)
                    if value is not None and str(value).strip():
                        merged[key] = str(value).strip()
                merged["id"] = extract_bill_number(filename)
                return merged
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("LLM extraction failed for %s: %s", filename, exc)

    return offline


def extract_metadata(
    pdf_folder: str | Path = PDF_EXTRACTION_INPUT_DIR,
    output_json: str | Path = BILL_RESULTS_PATH,
) -> List[dict]:
    """Extract and validate metadata for PDFs in ``pdf_folder``.

    Uses hash cache + prior output to safely skip unchanged files.
    """

    pdf_dir = Path(pdf_folder)
    if not pdf_dir.is_dir():
        raise FileNotFoundError(f"PDF folder does not exist: {pdf_dir}")

    output_path = Path(output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    hash_path = output_path.with_suffix(output_path.suffix + ".hashes.json")
    previous_results = _load_existing_results(output_path)
    previous_hashes = _load_hash_cache(hash_path)
    updated_hashes: Dict[str, str] = {}

    client = _get_openai_client()
    if client is None:
        logger.info("OPENAI_API_KEY not set; using offline extraction only")

    results: List[dict] = []

    for pdf_file in sorted(pdf_dir.glob("*.pdf")):
        file_hash = _sha256_file(pdf_file)
        cache_key = pdf_file.name
        bill_id = extract_bill_number(pdf_file.name)
        updated_hashes[cache_key] = file_hash

        if previous_hashes.get(cache_key) == file_hash and bill_id in previous_results:
            logger.info("Reusing cached extraction for %s", pdf_file.name)
            cached_item = previous_results[bill_id]
            try:
                results.append(BillMetadata(**cached_item).dict())
            except ValidationError:
                logger.warning("Cached record failed validation for %s; reprocessing", bill_id)
            else:
                continue

        text = extract_beginning(pdf_file)
        payload = _extract_with_optional_llm(client, pdf_file.name, text)
        payload["id"] = extract_bill_number(pdf_file.name)

        try:
            normalized = BillMetadata(**payload).dict()
        except ValidationError as exc:
            logger.warning("Skipping invalid extraction for %s: %s", pdf_file.name, exc)
            continue

        results.append(normalized)
        logger.info("Extraction complete: %s", pdf_file.name)

    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    hash_path.write_text(json.dumps(updated_hashes, indent=2), encoding="utf-8")
    logger.info("Wrote %d records to %s", len(results), output_path)
    return results


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    extract_metadata()


if __name__ == "__main__":
    main()
