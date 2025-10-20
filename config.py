"""Centralized configuration for UF SG website automation scripts."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


FIREBASE_SERVICE_ACCOUNT_ENV_VAR = "FIREBASE_SERVICE_ACCOUNT"


def _resolve_path(value: str | None, *, default: Path) -> Path:
    if value:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = BASE_DIR / candidate
        return candidate
    return default


SCRAPER_SOURCE_URL = os.getenv(
    "UFSG_SCRAPER_SOURCE_URL",
    "https://sg.ufl.edu/branches/legislative/senate-resources/",
)
DOWNLOAD_DIR = _resolve_path(
    os.getenv("UFSG_DOWNLOAD_DIR"),
    default=BASE_DIR / "bills",
)
PDF_URLS_PATH = _resolve_path(
    os.getenv("UFSG_PDF_URLS_PATH"),
    default=BASE_DIR / "pdf_urls.txt",
)
PDF_CONVERSION_INPUT_DIR = _resolve_path(
    os.getenv("UFSG_CONVERSION_INPUT_DIR"),
    default=DOWNLOAD_DIR,
)
PDF_CONVERSION_OUTPUT_DIR = _resolve_path(
    os.getenv("UFSG_CONVERSION_OUTPUT_DIR"),
    default=BASE_DIR / "bills-converted",
)
PDF_EXTRACTION_INPUT_DIR = _resolve_path(
    os.getenv("UFSG_EXTRACTION_INPUT_DIR"),
    default=BASE_DIR / "test",
)
BILL_RESULTS_PATH = _resolve_path(
    os.getenv("UFSG_BILL_RESULTS_PATH"),
    default=BASE_DIR / "bill_results.json",
)
LEGISLATION_DATA_PATH = _resolve_path(
    os.getenv("UFSG_LEGISLATION_DATA_PATH"),
    default=BASE_DIR / "legislation_data.json",
)

FIREBASE_SERVICE_ACCOUNT = os.getenv(FIREBASE_SERVICE_ACCOUNT_ENV_VAR)

__all__ = [
    "BASE_DIR",
    "SCRAPER_SOURCE_URL",
    "DOWNLOAD_DIR",
    "PDF_URLS_PATH",
    "PDF_CONVERSION_INPUT_DIR",
    "PDF_CONVERSION_OUTPUT_DIR",
    "PDF_EXTRACTION_INPUT_DIR",
    "BILL_RESULTS_PATH",
    "LEGISLATION_DATA_PATH",
    "FIREBASE_SERVICE_ACCOUNT",
    "FIREBASE_SERVICE_ACCOUNT_ENV_VAR",
]
