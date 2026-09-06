import unittest

from app import _extract_pdf_links
from config import BILL_RESULTS_PATH, DOWNLOAD_DIR, PDF_CONVERSION_OUTPUT_DIR, PDF_URLS_PATH, SCRAPER_SOURCE_URL
from pdf_extract import _build_offline_metadata, extract_bill_number
import pipeline


class AppAndExtractionUtilsTest(unittest.TestCase):
    def test_extract_pdf_links_filters_and_deduplicates(self) -> None:
        html = """
        <html><body>
            <a href="/docs/SSB-2024-0001.pdf">Bill 1</a>
            <a href="https://example.com/docs/other.pdf">misc</a>
            <a href="/docs/SSB-2024-0001.pdf">Bill 1 duplicate</a>
            <a href="/docs/something-bill-2024.pdf">Legislation</a>
        </body></html>
        """
        links = _extract_pdf_links(html, "https://sg.ufl.edu/path/")
        self.assertEqual(
            links,
            [
                "https://sg.ufl.edu/docs/SSB-2024-0001.pdf",
                "https://sg.ufl.edu/docs/something-bill-2024.pdf",
            ],
        )

    def test_extract_bill_number_formats_id(self) -> None:
        self.assertEqual(extract_bill_number("draft-2024-0009.pdf"), "SSB 2024-0009")

    def test_offline_metadata_sets_status_from_known_phrase(self) -> None:
        metadata = _build_offline_metadata(
            "SSB-2024-0001.pdf",
            "Resolution\nSponsored by: Jane Doe\n3000 J. Wayne Reitz Union PO Box 113111",
        )
        self.assertEqual(metadata["status"], "PASSED")
        self.assertEqual(metadata["id"], "SSB 2024-0001")

    def test_pipeline_parser_defaults_match_config(self) -> None:
        parser = pipeline.build_parser()

        args = parser.parse_args(["download"])
        self.assertEqual(args.url, SCRAPER_SOURCE_URL)
        self.assertEqual(args.download_dir, str(DOWNLOAD_DIR))
        self.assertEqual(args.urls_file, str(PDF_URLS_PATH))

        args = parser.parse_args(["ocr"])
        self.assertEqual(args.input_dir, str(DOWNLOAD_DIR))
        self.assertEqual(args.output_dir, str(PDF_CONVERSION_OUTPUT_DIR))

        args = parser.parse_args(["extract"])
        self.assertEqual(args.input_dir, str(PDF_CONVERSION_OUTPUT_DIR))
        self.assertEqual(args.output_json, str(BILL_RESULTS_PATH))


if __name__ == "__main__":
    unittest.main()
