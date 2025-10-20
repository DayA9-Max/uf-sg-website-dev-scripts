"""Command-line orchestration for the UF SG legislative document pipeline."""

from __future__ import annotations

import argparse
import logging
from typing import Callable, Sequence

from app import DEFAULT_URL, download_legislation_pdfs
from convert_searchable_pdf import convert_directory
from pdf_extract import extract_metadata


def _configure_logging(level: str) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=numeric_level, format="%(levelname)s: %(message)s")


def _run_download(args: argparse.Namespace) -> None:
    logging.info("Downloading PDFs from %s", args.url)
    download_legislation_pdfs(
        url=args.url,
        download_folder=args.download_dir,
        url_output_path=args.urls_file,
    )


def _run_ocr(args: argparse.Namespace) -> None:
    logging.info(
        "Converting PDFs in %s into searchable copies in %s",
        args.input_dir,
        args.output_dir,
    )
    convert_directory(input_dir=args.input_dir, output_dir=args.output_dir)


def _run_extract(args: argparse.Namespace) -> None:
    logging.info(
        "Extracting structured data from PDFs in %s", args.input_dir
    )
    extract_metadata(pdf_folder=args.input_dir, output_json=args.output_json)


def _run_all(args: argparse.Namespace) -> None:
    logging.info("Starting full pipeline")
    download_legislation_pdfs(
        url=args.url,
        download_folder=args.download_dir,
        url_output_path=args.urls_file,
    )
    convert_directory(input_dir=args.download_dir, output_dir=args.converted_dir)
    extract_metadata(pdf_folder=args.converted_dir, output_json=args.output_json)
    logging.info("Pipeline complete")


def _add_download_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "download", description="Download Senate legislation PDFs"
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Page containing bill links")
    parser.add_argument(
        "--download-dir",
        default="bills",
        help="Directory where the PDFs will be stored",
    )
    parser.add_argument(
        "--urls-file",
        default="pdf_urls.txt",
        help="Where to write the list of discovered PDF URLs",
    )
    parser.set_defaults(func=_run_download)


def _add_ocr_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "ocr", description="Convert PDFs into searchable PDFs using OCR"
    )
    parser.add_argument(
        "--input-dir",
        default="bills",
        help="Directory containing the source PDFs",
    )
    parser.add_argument(
        "--output-dir",
        default="bills-converted",
        help="Directory for the searchable output PDFs",
    )
    parser.set_defaults(func=_run_ocr)


def _add_extract_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "extract", description="Extract structured bill data via OpenAI"
    )
    parser.add_argument(
        "--input-dir",
        default="bills-converted",
        help="Directory containing searchable PDFs to analyze",
    )
    parser.add_argument(
        "--output-json",
        default="bill_results.json",
        help="Destination JSON file for extracted bill metadata",
    )
    parser.set_defaults(func=_run_extract)


def _add_run_all_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "run-all", description="Execute download, OCR, and extraction steps"
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Page containing bill links")
    parser.add_argument(
        "--download-dir",
        default="bills",
        help="Directory where the downloaded PDFs will be stored",
    )
    parser.add_argument(
        "--urls-file",
        default="pdf_urls.txt",
        help="Where to write the list of discovered PDF URLs",
    )
    parser.add_argument(
        "--converted-dir",
        default="bills-converted",
        help="Directory for the OCR-converted PDFs",
    )
    parser.add_argument(
        "--output-json",
        default="bill_results.json",
        help="Destination JSON file for extracted bill metadata",
    )
    parser.set_defaults(func=_run_all)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Utilities for orchestrating the UF SG legislative pipeline",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    _add_download_parser(subparsers)
    _add_ocr_parser(subparsers)
    _add_extract_parser(subparsers)
    _add_run_all_parser(subparsers)

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.log_level)

    action: Callable[[argparse.Namespace], None] = args.func
    action(args)


if __name__ == "__main__":
    main()