"""OCR helpers for converting PDFs into searchable versions."""

import io
import os
import shutil
from typing import Iterable, List, Tuple
import pytesseract
from pdf2image import convert_from_path
from PyPDF2 import PdfReader, PdfWriter
from dotenv import load_dotenv
load_dotenv()

from config import PDF_CONVERSION_INPUT_DIR, PDF_CONVERSION_OUTPUT_DIR

POPPLER_PATH = os.getenv("POPPLER_PATH")
TESSERACT_PATH = os.getenv("TESSERACT_PATH")
if TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def is_text_searchable(pdf_path, output_path):
    """Checks if a PDF file is text-searchable.
    Args:
      pdf_path: The path to the PDF file.

    Returns:
      True if the PDF file is text-searchable, False otherwise.
    """
    try:
        reader = PdfReader(pdf_path)
        text = (reader.pages[0].extract_text() or "") # handle None
        print(text)
        if len(text) > 0:
            shutil.copy(pdf_path, output_path) # cross-platform copy
            print("copied")
            return True
        else:
            return False
    except Exception as e:
        print(f"Error on {pdf_path}: {e}")
        return True  # Don't try converting


def convert_pdf_to_text_searchable(pdf_path, output_path):
    """Converts a PDF file to a text-searchable PDF file using Tesseract.
    Args:
      pdf_path: The path to the PDF file to convert.

    Returns:
      A tuple of (output_path, converted) where converted is True if the file was newly 
      created and False if the output already existed.
    """

    # Don't process pdfs that are already converted
    if os.path.isfile(output_path) == True:
        print("ALREADY CONVERTED")
        return output_path, False
    kwargs = {}
    if POPPLER_PATH:
        kwargs["poppler_path"] = POPPLER_PATH
    images = convert_from_path(pdf_path, **kwargs)
    pdf_pages = []
    for image in images:
        text = pytesseract.image_to_pdf_or_hocr(image, extension="pdf")
        pdf_pages.append(text)

    pdf_writer = PdfWriter()
    for page in pdf_pages:
        pdf = PdfReader(io.BytesIO(page))
        pdf_writer.add_page(pdf.pages[0])

    with open(output_path, "w+b") as file:
        pdf_writer.write(file)

    return output_path, True


def _iter_pdf_paths(input_dir: str, output_dir: str) -> Iterable[Tuple[str, str]]:
    """Yield pairs of input and output PDF paths for files in ``input_dir``."""

    for entry in sorted(os.listdir(input_dir)):
        if entry.lower().endswith(".pdf"):
            yield os.path.join(input_dir, entry), os.path.join(output_dir, entry)


def convert_directory(
    input_dir: str = PDF_CONVERSION_INPUT_DIR,
    output_dir: str = PDF_CONVERSION_OUTPUT_DIR,
) -> List[Tuple[str, bool]]:
    """Convert PDFs in ``input_dir`` into searchable PDFs within ``output_dir``."""

    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    print("Beginning OCR scan")
    os.makedirs(output_dir, exist_ok=True)

    results: List[Tuple[str, bool]] = []
    for pdf_path, output_path in _iter_pdf_paths(input_dir, output_dir):
        output_pdf_path = None
        converted = False
        skip_message = None

        try:
            if is_text_searchable(pdf_path, output_path):
                output_pdf_path = output_path
                skip_message = (
                    f"Skipped conversion for {pdf_path} (already text-searchable)."
                )
            else:
                output_pdf_path, converted = convert_pdf_to_text_searchable(
                    pdf_path, output_path
                )
        except Exception as exc:
            print(f"Error converting {pdf_path}: {exc}")
        else:
            if converted and output_pdf_path:
                print(f"Converted {pdf_path} to {output_pdf_path}.")
            elif skip_message:
                print(skip_message)
            elif output_pdf_path:
                print(
                    f"Skipped conversion for {pdf_path} (already converted output exists)."
                )

        if output_pdf_path:
            results.append((output_pdf_path, converted))

    return results


def main() -> None:
    """CLI entry point to convert PDFs using default settings."""

    input_dir = PDF_CONVERSION_INPUT_DIR
    output_dir = PDF_CONVERSION_OUTPUT_DIR

    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    os.makedirs(output_dir, exist_ok=True)

    for pdf_path, output_path in _iter_pdf_paths(input_dir, output_dir):
        output_pdf_path = None
        converted = False
        skip_message = None

        try:
            if is_text_searchable(pdf_path, output_path):
                output_pdf_path = output_path
                skip_message = (
                    f"Skipped conversion for {pdf_path} (already text-searchable)."
                )
            else:
                output_pdf_path, converted = convert_pdf_to_text_searchable(
                    pdf_path, output_path
                )
        except Exception as exc:
            print(f"Error converting {pdf_path}: {exc}")
        else:
            if converted and output_pdf_path:
                print(f"Converted {pdf_path} to {output_pdf_path}.")
            elif skip_message:
                print(skip_message)
            elif output_pdf_path:
                print(
                    f"Skipped conversion for {pdf_path} (already converted output exists)."
                )

        if output_pdf_path:
            print(f"Searchable PDF available at {output_pdf_path}")

if __name__ == "__main__":
    main()
