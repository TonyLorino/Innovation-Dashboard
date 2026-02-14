"""
Vercel Python serverless function — Smartsheet API proxy.

Mapped to /api/use-cases by filename convention.
Reads SMARTSHEET_API_TOKEN from Vercel Environment Variables.
"""

import json
import os
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "smartsheet_config.json"


def _load_config() -> dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _fetch_smartsheet_data() -> dict[str, Any]:
    """Call the Smartsheet API and return data in the same shape as use_cases.json."""
    token = os.environ.get("SMARTSHEET_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SMARTSHEET_API_TOKEN is not configured.")

    config = _load_config()
    sheet_id = config["sheet_id"]
    col_map = config["column_map"]

    url = f"https://api.smartsheet.com/2.0/sheets/{sheet_id}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        sheet = json.loads(resp.read().decode("utf-8"))

    # Build column-id → column-title lookup
    col_id_to_title: dict[int, str] = {
        col["id"]: col["title"] for col in sheet.get("columns", [])
    }

    # Build title → json_field reverse lookup
    title_to_field: dict[str, str] = {v: k for k, v in col_map.items()}

    # Parse rows into use_case dicts
    use_cases: list[dict[str, Any]] = []
    for idx, row in enumerate(sheet.get("rows", []), start=1):
        record: dict[str, Any] = {"id": idx}
        for cell in row.get("cells", []):
            col_title = col_id_to_title.get(cell.get("columnId", 0), "")
            field = title_to_field.get(col_title)
            if field:
                record[field] = cell.get("displayValue") or cell.get("value") or ""
        if record.get("name"):
            use_cases.append(record)

    statuses = [uc.get("status", "") for uc in use_cases]
    summary = {
        "total_initiatives": len(use_cases),
        "in_production": statuses.count("In Production"),
        "poc_done": statuses.count("POC Done"),
        "poc_in_progress": statuses.count("POC In Progress"),
    }

    return {
        "metadata": {
            "title": sheet.get("name", "AI Use Cases"),
            "source": "Smartsheet (live)",
            "last_updated": "live",
        },
        "summary": summary,
        "use_cases": use_cases,
    }


class handler(BaseHTTPRequestHandler):
    """Vercel serverless handler for GET /api/use-cases."""

    def do_GET(self) -> None:
        try:
            payload = _fetch_smartsheet_data()
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "s-maxage=60, stale-while-revalidate=300")
            self.end_headers()
            self.wfile.write(body)
        except RuntimeError as exc:
            self._send_error(503, str(exc))
        except urllib.error.HTTPError as exc:
            self._send_error(502, f"Smartsheet API returned {exc.code}: {exc.reason}")
        except Exception as exc:
            self._send_error(500, f"Internal error: {exc}")

    def _send_error(self, code: int, message: str) -> None:
        body = json.dumps({"error": message}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)
