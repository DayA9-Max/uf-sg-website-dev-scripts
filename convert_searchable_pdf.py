"""OCR helpers for converting PDFs into searchable versions."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pytesseract
from dotenv import load_dotenv
from pdf2image import convert_from_path
from PyPDF2 import PdfReader, PdfWriter

from config import PDF_CONVERSION_INPUT_DIR, PDF_CONVERSION_OUTPUT_DIR

load_dotenv()

POPPLER_PATH = os.getenv("POPPLER_PATH")
TESSERACT_PATH = os.getenv("TESSERACT_PATH")
if TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

logger = logging.getLogger(__name__)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _save_manifest(path: Path, payload: Dict[str, str]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def is_text_searchable(pdf_path: Path) -> bool:
    """Return True if first page contains selectable text."""
    try:
        reader = PdfReader(str(pdf_path))
        if not reader.pages:
            return False
        text = (reader.pages[0].extract_text() or "").strip()
        return bool(text)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Failed reading %s; assuming OCR needed (%s)", pdf_path, exc)
        return False


def convert_pdf_to_text_searchable(pdf_path: Path, output_path: Path) -> None:
    """Convert an image-based PDF file into a text-searchable PDF."""
    kwargs = {}
    if POPPLER_PATH:
        kwargs["poppler_path"] = POPPLER_PATH

    images = convert_from_path(str(pdf_path), **kwargs)
    pdf_writer = PdfWriter()

    for image in images:
        text_pdf = pytesseract.image_to_pdf_or_hocr(image, extension="pdf")
        page_pdf = PdfReader(io.BytesIO(text_pdf))
        pdf_writer.add_page(page_pdf.pages[0])

    with output_path.open("w+b") as file:
        pdf_writer.write(file)


def _iter_pdf_paths(input_dir: Path, output_dir: Path) -> Iterable[Tuple[Path, Path]]:
    for entry in sorted(input_dir.iterdir()):
        if entry.is_file() and entry.suffix.lower() == ".pdf":
            yield entry, output_dir / entry.name


def convert_directory(
    input_dir: str | Path = PDF_CONVERSION_INPUT_DIR,
    output_dir: str | Path = PDF_CONVERSION_OUTPUT_DIR,
) -> List[Tuple[str, bool]]:
    """Convert PDFs in ``input_dir`` into searchable PDFs within ``output_dir``.

    Returns tuples of (output_path, converted) where converted indicates OCR was run.
    """

    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {input_path}")

    output_path.mkdir(parents=True, exist_ok=True)
    manifest_path = output_path / ".ocr_manifest.json"
    prior_manifest = _load_manifest(manifest_path)
    next_manifest: Dict[str, str] = {}

    results: List[Tuple[str, bool]] = []

    for pdf_path, destination in _iter_pdf_paths(input_path, output_path):
        source_hash = _sha256_file(pdf_path)
        next_manifest[pdf_path.name] = source_hash

        if destination.exists() and prior_manifest.get(pdf_path.name) == source_hash:
            logger.info("Skipping unchanged OCR artifact: %s", pdf_path.name)
            results.append((str(destination), False))
            continue

        try:
            if is_text_searchable(pdf_path):
                shutil.copy2(pdf_path, destination)
                logger.info("Copied searchable PDF: %s", pdf_path.name)
                results.append((str(destination), False))
            else:
                convert_pdf_to_text_searchable(pdf_path, destination)
                logger.info("OCR converted: %s", pdf_path.name)
                results.append((str(destination), True))
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Error converting %s: %s", pdf_path, exc)

    _save_manifest(manifest_path, next_manifest)
    return results


def main() -> None:
    """CLI entry point to convert PDFs using default settings."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    convert_directory()


if __name__ == "__main__":
    main()
