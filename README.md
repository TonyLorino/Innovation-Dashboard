# AI Portfolio — Executive Board Summary

A polished, print-ready executive one-pager for the **"Driving Results with AI"** initiative portfolio. Designed for board of directors and executive leadership review.

## Project Structure

```
├── index.html                  # Executive one-pager (root page, print/PDF-ready)
├── board-summary/
│   └── index.html              # Legacy path (kept for backwards compat)
├── api/
│   └── use-cases.py            # Vercel serverless function (Smartsheet proxy)
├── data/
│   ├── use_cases.json          # Local data (manual/offline mode)
│   └── smartsheet_config.json  # Smartsheet sheet ID & column mapping
├── server.py                   # Local dev server + Smartsheet API proxy
├── vercel.json                 # Vercel deployment config
├── .env.example                # Template for API token
├── .gitignore
└── README.md
```

## Prerequisites

- **Python 3.9+** (ships with macOS; verify with `python3 --version`)
- A modern browser (Chrome, Edge, Safari, Firefox)
- *(Optional)* A Smartsheet account with API access for live data mode

## Quick Start (Local Install)

```bash
# 1. Clone the repo
git clone <repo-url> && cd Innovation-Dashboard

# 2. (Optional) Set up Smartsheet — copy .env and add your token
cp .env.example .env
# Edit .env and paste your Smartsheet API token

# 3. Start the server
python3 server.py

# 4. Open in your browser
open http://localhost:8080
```

The page loads data from `data/use_cases.json` by default. To pull live data from the [AI Innovation List](https://app.smartsheet.com/sheets/c9xQm5P5Vp4Gph8Xq2hCw9jWw9vWJjC8R78xchh1?view=grid) Smartsheet, set up a `.env` file (see [Smartsheet Setup](#smartsheet-setup)) and switch `DATA_SOURCE` to `"smartsheet"` in `index.html`.

To export as PDF, use **Cmd + P** (or Ctrl + P) and select **Save as PDF**.

## Switching Between JSON and Smartsheet

The data source is controlled by a single constant in `index.html` (near line 468):

```js
const DATA_SOURCE = "smartsheet";  // ← live from Smartsheet API (default)
const DATA_SOURCE = "json";        // ← local file
```

The default is `"smartsheet"`. Change the value and refresh the page. Only one line should be active (the other should be deleted or commented out).

| Mode | What it does | Server command |
|---|---|---|
| `"json"` | Reads `data/use_cases.json` — no network needed | `python3 server.py` |
| `"smartsheet"` | Fetches live data from Smartsheet via the proxy server | `python3 server.py` |

> **Note:** The server auto-loads your `.env` file at startup. You no longer need to run `source .env` before starting it (though that still works too).

## Smartsheet Setup

This dashboard is configured to pull live data from the **[AI Innovation List](https://app.smartsheet.com/sheets/c9xQm5P5Vp4Gph8Xq2hCw9jWw9vWJjC8R78xchh1?view=grid)** Smartsheet. When running in Smartsheet mode, the dashboard reflects the current state of that sheet — any changes made in Smartsheet will appear on the next page refresh.

### Smartsheet Columns

The dashboard reads the following columns from the AI Innovation List. When editing the sheet, these are the columns that drive the dashboard:

| Smartsheet Column | Dashboard Field | How it's used |
|---|---|---|
| **Project Name** | Initiative name | Displayed on cards, table rows, and highlights |
| **Status** | Pipeline stage | Groups initiatives into columns: `In Production`, `POC Done`, `POC In Progress` |
| **Department** | Owning department | Shown in the portfolio table and used for highlight cards |
| **Sponsor** | Executive owner | Displayed in the table; `TBD` values trigger a "next steps" recommendation |
| **Headline Impact** | Business impact summary | Shown on cards/table; dollar amounts (`$300K`) and FTE counts (`4-6 FTEs`) are auto-parsed to compute KPI totals |

> **Tip:** Only rows with a **Project Name** are included. To hide a row from the dashboard, clear its Project Name cell.

### 1. Get your API token

1. Log in to [Smartsheet](https://app.smartsheet.com)
2. Click your **profile icon** (bottom-left) → **Personal Settings**
3. Select **API Access** → **Generate new access token**
4. Copy the token

### 2. Configure locally

Create a `.env` file in the project root (this file is git-ignored):

```bash
cp .env.example .env
```

Then paste your token:

```
export SMARTSHEET_API_TOKEN=your_token_here
```

The sheet ID and column mapping are already configured in `data/smartsheet_config.json` for the AI Innovation List. You should not need to change them unless the sheet or its column names change.

### 3. Start the server

```bash
python3 server.py
```

The server auto-loads the `.env` file on startup — no need to `source` it manually. Then set `DATA_SOURCE = "smartsheet"` in `index.html` (see above) and refresh.

## Updating the JSON File (Manual Mode)

If you prefer to manage data manually instead of using Smartsheet, edit `data/use_cases.json` directly.

### Adding a new initiative

Add an entry to the `use_cases` array:

```json
{
  "id": 15,
  "name": "New Initiative",
  "status": "POC In Progress",
  "department": "Engineering",
  "owner": "J. Smith",
  "headline_impact": "$500K annual savings; 3 FTEs"
}
```

### Required fields

| Field | Description | Valid values |
|---|---|---|
| `id` | Unique integer | Any unique number |
| `name` | Initiative name | Free text |
| `status` | Pipeline stage | `"In Production"`, `"POC Done"`, `"POC In Progress"` |
| `department` | Owning department | Free text |
| `owner` | Executive sponsor | Free text (use `"TBD"` if unassigned) |
| `headline_impact` | Business impact summary | Free text — dollar amounts (`$300K`) and FTE counts (`4-6 FTEs`) are auto-parsed for KPIs |

### Removing an initiative

Delete the entire `{ ... }` block for that entry and ensure the remaining JSON array has no trailing commas.

After editing, refresh the page (make sure `DATA_SOURCE = "json"`).

## Deploy to Vercel

The project is ready to deploy to [Vercel](https://vercel.com) with zero build configuration. The dashboard is served as a static page at the root URL, and the Smartsheet proxy runs as a Python serverless function at `/api/use-cases`.

### 1. Import the repo

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repository
3. Leave all build settings at their defaults — no framework, no build command needed

### 2. Add your API token

1. In the Vercel project dashboard, go to **Settings → Environment Variables**
2. Add a variable:
   - **Name:** `SMARTSHEET_API_TOKEN`
   - **Value:** your Smartsheet API token
3. Click **Save**

### 3. Deploy

Click **Deploy** (or push to your main branch). The site will be live at your Vercel URL with live Smartsheet data — no further configuration needed.

> **How it works:** The `api/use-cases.py` serverless function reads the token from the environment variable, calls the Smartsheet API, and returns the data. The API key never reaches the browser. Responses are cached for 60 seconds with stale-while-revalidate for performance.

## Features

- **4 headline KPI boxes** — total initiatives, estimated annual impact, FTE savings, production count (all computed from data)
- **3-column initiative pipeline** — In Production, POC Done, POC In Progress with individual cards
- **Full portfolio table** — status, use case, department, headline impact, owner
- **3 strategic highlight cards** — auto-generated from live data
- **Recommended next steps** — auto-generated based on data patterns (TBD owners, unscored items, etc.)
- **Dark mode toggle** — persisted across sessions; applies to exports too
- **Export to slide** — three buttons capture page sections as 1920x1080 PNG images sized for PowerPoint
- **Print-optimized layout** — letter-size, clean PDF export via Cmd/Ctrl + P
- **Plug-and-play data source** — switch between local JSON and live Smartsheet with one line change
