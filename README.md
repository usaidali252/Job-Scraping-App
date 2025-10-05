# Job Listing Web App (Flask + React + Selenium)

A clean full-stack app for actuarial jobs.  
**Backend**: Flask + SQLAlchemy + Neon (Postgres)  
**Frontend**: React (Create React App style)  
**Scraper**: Selenium (headless Chrome) that bulk-inserts via the API

---

## Table of Contents
- [What’s Included](#whats-included)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Install & Run](#install--run)
  - [1) Backend (Flask API + Neon)](#1-backend-flask-api--neon)
  - [2) Frontend (React)](#2-frontend-react)
  - [3) Scraper (Selenium)](#3-scraper-selenium)
- [API Endpoints](#api-endpoints)
- [Manual Test Plan](#manual-test-plan)
- [How This Meets the Rubric](#how-this-meets-the-rubric)
- [Troubleshooting](#troubleshooting)
- [Deployment Notes](#deployment-notes)
- [Roadmap](#roadmap)
- [License](#license)

---

## What’s Included

- **Jobs list** with filters (keyword, location, job type, tags) and sorting.
- **Add / Edit / Delete** jobs with inline validation and toasts.
- **Responsive UI**: filters stack gracefully on small screens (no overflow or “squish”).
- **“Fetch latest”** button triggers Selenium scraping via the backend.  
  Shows a **progress bar** with `N / limit` while scraping runs, then refreshes results.
- **Data model**: Jobs + Tags (many-to-many), long **description** field supported.
- **Bulk insert** with **de-dup** (`source_url` or `(title, company, location, posting_date)`).

---

## Repository Layout

```
APP/
├─ backend/
│  ├─ app.py
│  ├─ config.py
│  ├─ db.py
│  ├─ models/
│  │  └─ job.py
│  ├─ routes/
│  │  ├─ job_routes.py
│  │  └─ scrape_routes.py
│  ├─ requirement.txt            # backend + scraper Python dependencies (single file)
│  └─ .env                      
├─ frontend/
│  ├─ public/
│  │  └─ index.html
│  └─ src/
│     ├─ App.css
│     ├─ App.js
│     ├─ index.js
│     ├─ api.js
│     ├─ Components/
│     │  ├─ Confirm.js
│     │  ├─ ConfirmDialog.jsx
│     │  ├─ DeleteJob.js
│     │  └─ ToastProvider.jsx
│     └─ Pages/
│        ├─ AddEditJob.js
│        └─ JobsList.js          
└─ Scraper/
   └─ scrape.py
```

> **Note**  
> The frontend uses `REACT_APP_API_BASE` (Create React App env style).  
> The backend keeps a single `requirement.txt` that also includes the scraper deps.

---

## Prerequisites

- **Python** 3.10+
- **Node** 18+ (and npm 9+)
- **Neon Postgres** database (cloud) — with `sslmode=require`
- **Google Chrome / Chromium** installed on the machine that runs the scraper  
  (Selenium uses `webdriver-manager` to fetch a matching ChromeDriver)

---

## Environment Variables

### Backend — `APP/backend/.env`
```
# Neon (Postgres). Include sslmode=require for Neon.
DATABASE_URL=postgresql+psycopg2://<user>:<password>@<neon-host>/<database>?sslmode=require

# CORS origins that are allowed to call the API (comma-separated)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Optional
PAGINATION_DEFAULT_PAGE_SIZE=10
PAGINATION_MAX_PAGE_SIZE=50
FLASK_ENV=development
```

### Frontend — `APP/frontend/.env`
```
REACT_APP_API_BASE=http://localhost:5000
```

---

## Install & Run

### 1) Backend (Flask API + Neon)

From the backend folder:

```bash
cd APP/backend
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

pip install --upgrade pip
pip install -r requirement.txt
```

Your **`requirement.txt`** should include both API and scraper deps (single file):

```
Flask>=3.0.0
Flask-CORS>=4.0.0
SQLAlchemy>=2.0.0
psycopg2-binary>=2.9.9
python-dotenv>=1.0.1
python-dateutil>=2.9.0
requests>=2.32.3
selenium>=4.21.0
webdriver-manager>=4.0.2
beautifulsoup4>=4.12.3
lxml>=5.2.2
```

Run the API:

```bash
python app.py
# → http://localhost:5000
# Health: http://localhost:5000/healthz ({"status":"ok"})
```

On first run, tables are created automatically.

---

### 2) Frontend (React)

From the frontend folder:

```bash
cd APP/frontend
npm install
# Create APP/frontend/.env with REACT_APP_API_BASE=http://localhost:5000
npm start
# → http://localhost:3000
```

---

### 3) Scraper (Selenium)

**Via the UI**  
- Open the app at `http://localhost:3000`.
- On the Jobs page, click **Fetch latest**.  
- A progress bar shows, e.g., “Fetching… 17 / 50”.  
- When finished, a toast appears and the list refreshes.

**Via the API**
```bash
# Start
curl -X POST http://localhost:5000/api/scrape/start \
  -H "Content-Type: application/json" \
  -d '{"limit":50,"headless":true}'

# Poll
curl http://localhost:5000/api/scrape/status
```

**Via the CLI (optional)**
```bash
# Use the same Python venv so the scraper sees the installed packages
cd APP/Scraper
python scrape.py --limit 50 --headless --save api --api-base http://localhost:5000/api
```

> If Selenium reports it cannot find a Chrome binary, install Chrome/Chromium on that machine and retry.

---

## API Endpoints

Base URL: `http://localhost:5000/api`

- `GET /jobs`
  - **Filters**:  
    `q` (title/company contains),  
    `location` (contains, case-insensitive),  
    `job_type`,  
    **repeatable** `tag`
  - **Sort**: `posting_date_desc | posting_date_asc | title_asc | title_desc`
  - **Pagination**: `page`, `page_size`
- `GET /jobs/<id>`
- `POST /jobs`  
  **Required**: `title`, `company`, `location`  
  Optional: `description`, `posting_date` (ISO date), `posted_at` (ISO datetime), `job_type`, `salary_text`, `tags[]`, `source_url`
- `PATCH /jobs/<id>`
- `DELETE /jobs/<id>`
- `POST /jobs/bulk`  
  `{ "items": [...], "dry_run": false }`  
  De-dups by `source_url` or `(title, company, location, posting_date)`.

Scraper control:
- `POST /scrape/start` — `{ limit, headless, api_base?, base_url? }`
- `GET /scrape/status` — `{ running, fetched, limit, error, started_at, finished_at }`


## Deployment Notes

- **Backend**  
  - Set `CORS_ORIGINS` to your deployed frontend origin(s).  
  - Example with Gunicorn:
    ```bash
    cd APP/backend
    source .venv/bin/activate
    pip install gunicorn
    gunicorn -w 2 -b 0.0.0.0:5000 app:app
    ```
- **Database**  
  - Use Neon connection string with `sslmode=require`.
- **Scraper in production**  
  - Ensure Chrome/Chromium is installed on the worker host.  
  - Consider running the scraper on a separate machine or background worker.




