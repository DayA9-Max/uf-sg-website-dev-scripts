"""Export and normalize UF SG legislation records from Firestore."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import firebase_admin
from firebase_admin import firestore

from config import LEGISLATION_DATA_PATH
from firebase_credentials import load_service_account_credentials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_firestore_client():
    if not firebase_admin._apps:
        cred = load_service_account_credentials()
        firebase_admin.initialize_app(cred)
    return firestore.client()


def _normalize_existing_records(existing_records: List[dict]) -> List[dict]:
    filtered_legislation_data = [
        entry for entry in existing_records if str(entry.get("id", "")).startswith("SSB")
    ]
    for entry in filtered_legislation_data:
        entry["verified"] = entry.get("verified", False)
    return filtered_legislation_data


def export_data(output_file_path: str | Path = LEGISLATION_DATA_PATH) -> List[dict]:
    output_path = Path(output_file_path)
    if output_path.exists():
        logger.info("%s already exists; normalizing in place", output_path)
        existing_legislation_data = json.loads(output_path.read_text(encoding="utf-8"))
        normalized = _normalize_existing_records(existing_legislation_data)
        output_path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
        logger.info("Filtered and updated %s with %d documents", output_path, len(normalized))
        return normalized

    db = _get_firestore_client()
    legislation_docs = db.collection("legislation").stream()
    legislation_data = [doc.to_dict() for doc in legislation_docs]
    output_path.write_text(json.dumps(legislation_data, indent=2), encoding="utf-8")
    logger.info("Exported %d documents to %s", len(legislation_data), output_path)
    return legislation_data


def main() -> None:
    export_data()


if __name__ == "__main__":
    main()
