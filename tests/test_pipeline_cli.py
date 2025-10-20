import unittest
from unittest.mock import patch

import pipeline


class PipelineCLITest(unittest.TestCase):
    def test_download_command_invokes_downloader(self) -> None:
        with patch("pipeline.download_legislation_pdfs") as mock_download:
            pipeline.main(
                [
                    "download",
                    "--url",
                    "http://example.com",
                    "--download-dir",
                    "tmp",
                    "--urls-file",
                    "urls.txt",
                ]
            )

        mock_download.assert_called_once_with(
            url="http://example.com",
            download_folder="tmp",
            url_output_path="urls.txt",
        )

    def test_ocr_command_invokes_converter(self) -> None:
        with patch("pipeline.convert_directory") as mock_convert:
            pipeline.main(
                [
                    "ocr",
                    "--input-dir",
                    "source",
                    "--output-dir",
                    "dest",
                ]
            )

        mock_convert.assert_called_once_with(input_dir="source", output_dir="dest")

    def test_extract_command_invokes_metadata_extractor(self) -> None:
        with patch("pipeline.extract_metadata") as mock_extract:
            pipeline.main(
                [
                    "extract",
                    "--input-dir",
                    "converted",
                    "--output-json",
                    "output.json",
                ]
            )

        mock_extract.assert_called_once_with(
            pdf_folder="converted", output_json="output.json"
        )

    def test_run_all_command_invokes_all_steps(self) -> None:
        with patch("pipeline.download_legislation_pdfs") as mock_download, patch(
            "pipeline.convert_directory"
        ) as mock_convert, patch("pipeline.extract_metadata") as mock_extract:
            pipeline.main(
                [
                    "run-all",
                    "--url",
                    "http://example.com",
                    "--download-dir",
                    "tmp",
                    "--urls-file",
                    "urls.txt",
                    "--converted-dir",
                    "converted",
                    "--output-json",
                    "output.json",
                ]
            )

        mock_download.assert_called_once_with(
            url="http://example.com",
            download_folder="tmp",
            url_output_path="urls.txt",
        )
        mock_convert.assert_called_once_with(input_dir="tmp", output_dir="converted")
        mock_extract.assert_called_once_with(
            pdf_folder="converted", output_json="output.json"
        )


if __name__ == "__main__":
    unittest.main()