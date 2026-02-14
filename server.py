"""
Lightweight dev server for the AI Portfolio Board Summary.

Serves static files AND provides a /api/use-cases endpoint that proxies
data from the Smartsheet API, transforming it into the same JSON shape
as data/use_cases.json.

Usage:
    # JSON mode (no token needed)
    python3 server.py

    # Smartsheet mode (token is auto-loaded from .env)
    # Just add SMARTSHEET_API_TOKEN=your_token to .env and run:
    python3 server.py

Then open http://localhost:8080
"""

import json
import os
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

PORT = 8080
ENV_PATH = Path(__file__).parent / ".env"
CONFIG_PATH = Path(__file__).parent / "data" / "smartsheet_config.json"


def load_dotenv(path: Path = ENV_PATH) -> None:
    """Read a .env file and inject KEY=VALUE pairs into os.environ.

    - Skips blank lines and comments (lines starting with #).
    - Strips optional 'export ' prefix so the same file works with `source`.
    - Does NOT override variables that are already set in the environment.
    """
    if not path.is_file():
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Allow optional 'export ' prefix
            if line.startswith("export "):
                line = line[len("export "):]
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


def load_smartsheet_config() -> dict[str, Any]:
    """Load Smartsheet settings from the config file."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_smartsheet_data() -> dict[str, Any]:
    """
    Call the Smartsheet API and return data in the same shape as use_cases.json.

    Requires SMARTSHEET_API_TOKEN env var and a valid sheet_id in
    data/smartsheet_config.json.
    """
    token = os.environ.get("SMARTSHEET_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "SMARTSHEET_API_TOKEN environment variable is not set. "
            "Export it before starting the server for Smartsheet mode."
        )

    config = load_smartsheet_config()
    sheet_id = config["sheet_id"]
    col_map = config["column_map"]

    # Fetch the full sheet (columns + rows in one call)
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
    col_id_to_title: dict[int, str] = {}
    for col in sheet.get("columns", []):
        col_id_to_title[col["id"]] = col["title"]

    # Invert col_map: json_field → sheet_column_title
    # e.g. {"name": "Use Case", ...}
    field_to_title = col_map

    # Build title → json_field reverse lookup
    title_to_field: dict[str, str] = {v: k for k, v in field_to_title.items()}

    # Parse rows into use_case dicts
    use_cases: list[dict[str, Any]] = []
    for idx, row in enumerate(sheet.get("rows", []), start=1):
        record: dict[str, Any] = {"id": idx}
        for cell in row.get("cells", []):
            col_title = col_id_to_title.get(cell.get("columnId", 0), "")
            field = title_to_field.get(col_title)
            if field:
                record[field] = cell.get("displayValue") or cell.get("value") or ""
        # Only include rows that have at least a name
        if record.get("name"):
            use_cases.append(record)

    # Compute summary counts from the rows (KPI aggregation is done client-side)
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


class AppHandler(SimpleHTTPRequestHandler):
    """Extends the static file server with an API route."""

    def do_GET(self) -> None:
        if self.path == "/api/use-cases":
            self._handle_api()
        else:
            super().do_GET()

    def _handle_api(self) -> None:
        """Serve Smartsheet data as JSON."""
        try:
            payload = fetch_smartsheet_data()
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)
        except RuntimeError as exc:
            self._send_error(503, str(exc))
        except urllib.error.HTTPError as exc:
            self._send_error(
                502,
                f"Smartsheet API returned {exc.code}: {exc.reason}",
            )
        except Exception as exc:
            self._send_error(500, f"Internal error: {exc}")

    def _send_error(self, code: int, message: str) -> None:
        body = json.dumps({"error": message}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        # Cleaner log output
        print(f"[server] {args[0]} {args[1]}")


if __name__ == "__main__":
    load_dotenv()
    server = HTTPServer(("", PORT), AppHandler)
    print(f"[server] Serving on http://localhost:{PORT}")
    print(f"[server] Dashboard: http://localhost:{PORT}")
    if os.environ.get("SMARTSHEET_API_TOKEN"):
        print("[server] Smartsheet API token detected — /api/use-cases is available")
    else:
        print("[server] No SMARTSHEET_API_TOKEN set — /api/use-cases will return 503")
    print("[server] Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] Stopped.")
        server.server_close()
