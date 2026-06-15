"""
Google OAuth helper — Sheets and Drive access.
Run directly to authenticate: python tools/google_auth.py
Saves token.json to project root for subsequent runs.

On Render (ephemeral filesystem), set these env vars instead of using files:
  GOOGLE_TOKEN_JSON       — contents of token.json
  GOOGLE_CREDENTIALS_JSON — contents of credentials.json
"""

import json
import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send",
]

ROOT = Path(__file__).parent.parent
CREDENTIALS_FILE = ROOT / "credentials.json"
TOKEN_FILE = ROOT / "token.json"


def get_credentials() -> Credentials:
    creds = None

    # Load token: file first, env var fallback (for Render)
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    elif os.environ.get("GOOGLE_TOKEN_JSON"):
        creds = Credentials.from_authorized_user_info(
            json.loads(os.environ["GOOGLE_TOKEN_JSON"]), SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Persist refreshed token locally if possible
            try:
                TOKEN_FILE.write_text(creds.to_json())
            except OSError:
                pass
        else:
            # Load credentials.json: file first, env var fallback
            if CREDENTIALS_FILE.exists():
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            elif os.environ.get("GOOGLE_CREDENTIALS_JSON"):
                flow = InstalledAppFlow.from_client_config(
                    json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"]), SCOPES
                )
            else:
                raise FileNotFoundError(
                    f"credentials.json not found at {CREDENTIALS_FILE} and "
                    "GOOGLE_CREDENTIALS_JSON env var is not set.\n"
                    "Download credentials.json from Google Cloud Console > APIs & Services > Credentials."
                )
            creds = flow.run_local_server(port=0)
            try:
                TOKEN_FILE.write_text(creds.to_json())
            except OSError:
                pass

    return creds


def sheets_service():
    return build("sheets", "v4", credentials=get_credentials())


def drive_service():
    return build("drive", "v3", credentials=get_credentials())


if __name__ == "__main__":
    get_credentials()
    print("Authentication successful. token.json saved.")
