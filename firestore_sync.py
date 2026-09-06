"""Sync normalized legislation JSON data into Firestore."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

import firebase_admin
from firebase_admin import firestore
from pydantic import ValidationError

from config import LEGISLATION_DATA_PATH
from firebase_credentials import load_service_account_credentials
from schemas import BillMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_firestore_client():
    if not firebase_admin._apps:
        cred = load_service_account_credentials()
        firebase_admin.initialize_app(cred)
    return firestore.client()


def upload_data(data: Iterable[dict]) -> None:
    db = _get_firestore_client()
    for entry in data:
        try:
            bill = BillMetadata(**entry)
        except ValidationError as exc:
            logger.warning("Skipping invalid document %s: %s", entry.get("id", "<unknown>"), exc)
            continue

        try:
            db.collection("legislation").document(bill.id).set(bill.dict())
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to upload %s: %s", bill.id, exc)


def sync_from_json(json_file_path: str | Path = LEGISLATION_DATA_PATH) -> None:
    path = Path(json_file_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    upload_data(data)
    logger.info("Data uploaded to Cloud Firestore successfully")


def main() -> None:
    sync_from_json()


if __name__ == "__main__":
    main()
