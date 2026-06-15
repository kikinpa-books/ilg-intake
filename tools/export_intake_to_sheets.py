"""
Log a client intake JSON file as a new row in the ILG Client Intake Google Sheet.

Usage:
    python tools/export_intake_to_sheets.py .tmp/client_intake_Jane_Doe.json

Requires:
    INTAKE_SHEET_ID in .env — the Google Sheet ID (from its URL)
    credentials.json + token.json in project root (run google_auth.py first)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from google_auth import sheets_service

SHEET_ID = os.getenv("INTAKE_SHEET_ID")
SHEET_NAME = "Client Intake"

HEADERS = [
    "Timestamp",
    "Client 1 Name",
    "Client 2 Name",
    "Property Address",
    "Date of Loss",
    "Insurance Company",
    "Policy Number",
    "Has Mortgage",
    "Mortgage Company",
    "Loan Number",
    "Co-Borrower Name",
]


def ensure_header(service) -> None:
    """Write header row if the sheet is empty."""
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_NAME}!A1:A1",
    ).execute()

    if not result.get("values"):
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{SHEET_NAME}!A1",
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute()
        print("Header row created.")


def append_row(service, data: dict) -> None:
    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data.get("client1_name", ""),
        data.get("client2_name", ""),
        data.get("property_address", ""),
        data.get("date_of_loss", ""),
        data.get("insurance_company", ""),
        data.get("policy_number", ""),
        "Yes" if data.get("has_mortgage") else "No",
        data.get("mortgage_company", ""),
        data.get("loan_number", ""),
        data.get("coborrower_name", ""),
    ]

    service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_NAME}!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python tools/export_intake_to_sheets.py <client_data.json>", file=sys.stderr)
        sys.exit(1)

    if not SHEET_ID:
        print("ERROR: INTAKE_SHEET_ID not set in .env", file=sys.stderr)
        sys.exit(1)

    json_path = sys.argv[1]
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    service = sheets_service()
    ensure_header(service)
    append_row(service, data)

    client = data.get("client1_name", "unknown")
    print(f"Logged {client} to Google Sheet: {SHEET_NAME}")


if __name__ == "__main__":
    main()
