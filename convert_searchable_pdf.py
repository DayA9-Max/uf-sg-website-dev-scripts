"""OCR helpers for converting PDFs into searchable versions."""

import io
import os
from typing import List, Tuple
import pytesseract
from pdf2image import convert_from_path
from PyPDF2 import PdfReader, PdfWriter

from config import PDF_CONVERSION_INPUT_DIR, PDF_CONVERSION_OUTPUT_DIR


def is_text_searchable(pdf_path, output_path):
    """Checks if a PDF file is text-searchable.
    Args:
      pdf_path: The path to the PDF file.

    Returns:
      True if the PDF file is text-searchable, False otherwise.
    """
    try:
        reader = PdfReader(pdf_path)
        text = reader.pages[0].extract_text()
        print(text)
        if len(text) > 0:
            os.system(f'cp {pdf_path} {output_path}')
            print("copied")
            return True
        else:
            return False
    except:
        print("Error on " + pdf_path)
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

    images = convert_from_path(pdf_path)
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


def convert_directory(
    input_dir: str = "bills", output_dir: str = "bills-converted") -> List[Tuple[str, bool]]:
    """Convert PDFs in ``input_dir`` into searchable PDFs within ``output_dir``."""

    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    input_dir = PDF_CONVERSION_INPUT_DIR
    output_dir = PDF_CONVERSION_OUTPUT_DIR
    print("Beginning OCR scan")
    os.makedirs(output_dir, exist_ok=True)

        if not is_text_searchable(input_path, output_path):
            print("Text is not searchable")
            try:
                output_pdf_path, converted = convert_pdf_to_text_searchable(
                    input_path, output_path
                )
            except Exception as exc:
                print(f"Error converting {input_path}: {exc}")
            else:
                if converted:
                    print(f"Converted {input_path} to {output_pdf_path}.")
                else:
                    print(
                        "Skipped conversion for {} (already converted output exists).".format(
                            input_path
                        )
                    )
                results.append((output_pdf_path, converted))
        else:
            print(
                "Skipped conversion for {} (already text-searchable).".format(
                    input_path
                )
            )
            results.append((output_path, False))

    return results


def main() -> None:
    """CLI entry point to convert PDFs using default settings."""
    convert_directory()

if __name__ == "__main__":
    main()
