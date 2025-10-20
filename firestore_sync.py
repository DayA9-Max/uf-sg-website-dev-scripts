import json
import logging
from typing import Iterable

import firebase_admin
from firebase_admin import firestore
from pydantic import ValidationError

from firebase_credentials import load_service_account_credentials
from schemas import BillMetadata

cred = load_service_account_credentials()
firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize Firestore client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upload_data(data: Iterable[dict]):
    for entry in data:
        try:
            bill = BillMetadata(**entry)
        except ValidationError as exc:
            logger.warning("Skipping invalid document %s: %s", entry.get("id", "<unknown>"), exc)
            continue

        try:
            doc_ref = db.collection("legislation").document(bill.id)
            doc_ref.set(bill.dict())
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to upload %s: %s", bill.id, exc)


def main():
    json_file_path = "legislation_data.json"
    with open(json_file_path, 'r') as json_file:
        data = json.load(json_file)
        upload_data(data)
        print("Data uploaded to Cloud Firestore successfully!")


if __name__ == "__main__":
    main()
