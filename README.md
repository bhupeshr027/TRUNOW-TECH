# TRUNOW Technologies Pvt Ltd Portal

A complete Flask and SQLite-based portal for TRUNOW Technologies Pvt Ltd with a public website, admin portal, employee portal, attendance tracking, task assignment, stock management, and analytics.

## Features

- Public corporate landing page
- Secure admin login and dashboard
- Employee login with profile and task views
- Attendance clock-in and clock-out with geolocation and photo upload
- Employee management CRUD
- Task management CRUD
- Stock tracking with low-stock awareness
- Reports with Chart.js analytics
- SQLite auto-initialization with default admin and employee accounts

## Project Structure

```text
trunow-portal/
├── app.py
├── trunow.db
├── requirements.txt
├── README.md
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   ├── images/
│   │   └── logo.png
│   └── uploads/
│       ├── attendance/
│       └── profiles/
└── templates/
```

## Setup Instructions

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

## Run

Open your browser at:

`http://127.0.0.1:5000`

## Railway Deployment

- Start command: `gunicorn app:app --bind 0.0.0.0:${PORT:-8080}`
- Set `SECRET_KEY` in Railway Variables
- Optional: set `DATABASE_PATH` to a mounted volume path such as `/data/trunow.db` if you want SQLite data to persist across restarts

## Notes

- Database file: `trunow.db`
- Uploaded files are stored in `static/uploads/`
- The database and sample records are created automatically when the app starts
