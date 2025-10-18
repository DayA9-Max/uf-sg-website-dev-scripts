import json

import firebase_admin
from firebase_admin import firestore

from firebase_credentials import load_service_account_credentials

cred = load_service_account_credentials()
firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize Firestore client


def upload_data(data):
    for entry in data:
        try:
            doc_ref = db.collection("legislation").document(entry["id"])
            doc_ref.set(entry)
        except:
            print("Error")
            print(entry)


def main():
    json_file_path = "legislation_data.json"
    with open(json_file_path, 'r') as json_file:
        data = json.load(json_file)
        upload_data(data)
        print("Data uploaded to Cloud Firestore successfully!")


if __name__ == "__main__":
    main()
