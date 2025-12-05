import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

SHEET_ID = "1KkDjnkKBKETEnBNvERbvjFq22ZtHBrFrkJ14m85UXnc"   # ← replace with your actual sheet ID


def log_to_google_sheets(final_archetype, stability, shadow, scores, raw_answers):

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "service_account.json",
        scope
    )

    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1

    shadow_name, shadow_pct = shadow

    row = [
        datetime.utcnow().isoformat(),
        final_str(final_archetype),
        round(stability, 2),
        f"{shadow_name} ({round(shadow_pct, 2)}%)",
        scores.get("thinking", 0),
        scores.get("execution", 0),
        scores.get("risk", 0),
        scores.get("motivation", 0),
        scores.get("team", 0),
        scores.get("commercial", 0),
        json.dumps(raw_answers)
    ]

    sheet.append_row(row)

