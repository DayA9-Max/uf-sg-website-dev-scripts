# UF Student Government Legislative Tracker Scripts

This repository contains standalone Python scripts that power the legislative document pipeline for the University of Florida Student Government (UF SG) website. Each script focuses on a specific step in moving Senate legislation from the public resources page into a structured, searchable dataset backed by Firestore.

## Repository Structure
- **`pipeline.py`** – Provides a command-line interface (CLI) that orchestrates the download, OCR conversion, and metadata extraction steps.
- **`app.py`** – Scrapes the UF SG Senate resources page, records PDF URLs containing "ssb" or "bill", and downloads them into the local `bills/` directory.
- **`convert_searchable_pdf.py`** – Detects which downloaded PDFs are image-only and converts them into searchable PDFs via `pdf2image`, `pytesseract`, and `PyPDF2`, writing results to `bills-converted/`.
- **`pdf_extract.py`** – Opens PDFs (currently pointing to the `test/` directory, will default to the `bills-converted/`), captures first-page text with `pdfplumber`, and calls the OpenAI Chat Completions API to extract structured bill metadata into `bill_results.json`.
- **`export_data.py`** – Exports the Firestore `legislation` collection into `legislation_data.json` and normalizes records (e.g., ensuring an `verified` flag) to simplify downstream processing.
- **`firestore_sync.py`** – Reads `legislation_data.json` and pushes each record back into Firestore, overwriting or creating documents keyed by `id`.
- **Supporting data files** – Artifacts such as `pdf_urls.txt`, `bill_results.json`, and `legislation_data.json` capture intermediate results or exported datasets that other scripts reuse.

## Getting Started

1. **Install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Prepare directories** – Create the `bills/` and `bills-converted/` folders (or override defaults via environment variables). The scraper and converter will create directories automatically when they are missing.
3. **Configure credentials** – Provide a Firebase Admin service-account JSON for Firestore access and set the `OPENAI_API_KEY` environment variable (or load both via `.env`). The Firestore scripts read `FIREBASE_SERVICE_ACCOUNT`, which can contain either the absolute path to the service-account JSON file or the raw JSON string. For example:
   ```env
   FIREBASE_SERVICE_ACCOUNT=/absolute/path/to/firebase-admin.json
   OPENAI_API_KEY=sk-...
   ```
   If you prefer storing the JSON directly, paste it on a single line (escaping quotes as needed) or use shell quoting when exporting the variable. Ensure sensitive files stay out of version control.

   ## Configuration

   All scripts pull their settings from `config.py`, which reads environment variables via `python-dotenv`. Copy `.env.example` to `.env` and adjust the values for your environment; any variables you omit fall back to the defaults listed below. Paths can be absolute or relative to the repository root unless otherwise noted.

   | Variable | Default | Purpose |
   | --- | --- | --- |
   | `UFSG_SCRAPER_SOURCE_URL` | `https://sg.ufl.edu/branches/legislative/senate-resources/` | Source page for the PDF scraper (`app.py`). |
   | `UFSG_DOWNLOAD_DIR` | `bills/` | Directory where PDFs are downloaded. |
   | `UFSG_PDF_URLS_PATH` | `pdf_urls.txt` | File that stores the list of discovered PDF URLs. |
   | `UFSG_CONVERSION_INPUT_DIR` | `bills/` | Directory scanned for PDFs that might require OCR conversion. |
   | `UFSG_CONVERSION_OUTPUT_DIR` | `bills-converted/` | Destination directory for converted, searchable PDFs. |
   | `UFSG_EXTRACTION_INPUT_DIR` | `bills-converted/` | Directory that `pdf_extract.py` scans when building `bill_results.json`. |
   | `UFSG_BILL_RESULTS_PATH` | `bill_results.json` | Location of the JSON metadata exported by `pdf_extract.py`. |
   | `UFSG_LEGISLATION_DATA_PATH` | `legislation_data.json` | Shared path used by `export_data.py` and `firestore_sync.py`. |
   | `FIREBASE_SERVICE_ACCOUNT` | _(required)_ | Path to your Firebase Admin SDK service-account JSON or the raw JSON document. |
   | `OPENAI_API_KEY` | _(required)_ | API key for the OpenAI Chat Completions API used in `pdf_extract.py`. |

   When `FIREBASE_SERVICE_ACCOUNT` points to a file, the credential loader reads directly from disk. If you prefer embedding the JSON contents instead, paste them as a single-line string (escaping quotes if necessary). Ensure `.env` remains untracked so secrets stay private.

4. **Install OCR tooling** – Tesseract OCR and Ghostscript must be available on your system for `convert_searchable_pdf.py` to run successfully.

## Typical Workflow
1. Run `app.py` to refresh the list of Senate legislation PDFs and download them locally.
2. Run `convert_searchable_pdf.py` to create searchable copies of any image-only PDFs.
3. Run `pdf_extract.py` to produce structured metadata with offline-first extraction; OpenAI is used only when `OPENAI_API_KEY` is set.
4. Use `export_data.py` to snapshot the current Firestore data or to filter data down to Senate bills.
5. Apply updates with `firestore_sync.py`, which writes the normalized records back to Firestore.

## Command-Line Workflow
Run the orchestration CLI to execute individual stages or the full pipeline:

```bash
# Show command help
python pipeline.py --help

# Download PDFs only
python pipeline.py download --download-dir bills --urls-file pdf_urls.txt

# Convert a directory of PDFs into searchable PDFs
python pipeline.py ocr --input-dir bills --output-dir bills-converted

# Extract bill metadata into bill_results.json
python pipeline.py extract --input-dir bills-converted --output-json bill_results.json

# Perform all steps in sequence (download -> ocr -> extract)
python pipeline.py run-all
```

Use `export_data.py` to snapshot the current Firestore data or to filter data down to Senate bills, and `firestore_sync.py` to write the normalized records back to Firestore when you are ready to publish updates.


## Next Steps and Enhancements

- **Automation** – Orchestrate the scripts with a task runner (such as `invoke`, `prefect`, or GitHub Actions) for end-to-end updates.
- **Schema validation** – Introduce Pydantic models or dataclasses to validate OpenAI responses before persisting them.
- **UI or API integration** – Build a lightweight service (Flask/FastAPI) or integrate with an existing site to visualize and search the `legislation_data.json` data in real time.
- **Testing & linting** – Add unit tests for parsing and conversion logic and adopt tooling like `pytest`, `black`, or `ruff` to maintain code quality.

## Additional Tips

- Re-runs are idempotent for unchanged files: downloader and extraction steps cache artifacts using file hashes.
- Monitor storage usage in Firestore and local directories to avoid stale or duplicated artifacts.
