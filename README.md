# Trekking Management Application (MAD-I Project)

A multi-role web application for managing trekking activities, built for the
Modern Application Development I course project (May 2026 term).

## Roles

- **Admin** — pre-existing superuser. Manages treks, approves/blacklists staff,
  assigns staff to treks, views/searches all users, staff, treks, and bookings.
- **Trek Staff** — registers and logs in after admin approval. Manages assigned
  treks: slots, status, participant lists, marking treks started/completed.
- **User (Trekker)** — registers, browses/searches open treks, books treks,
  views booking status and trekking history.

## Tech Stack

- Flask (backend)
- Jinja2 + HTML + CSS + Bootstrap (frontend)
- SQLite via Flask-SQLAlchemy (database, created programmatically)

## Running Locally

```bash
pip install -r requirements.txt
python app.py
```

The database is created automatically on first run, with the admin user
pre-seeded (see `app.py`).

Default admin login: `admin@tma.com` / `admin123`

## Issue Log

Issues encountered and their resolutions are recorded here as development
progresses.

| # | Issue | Resolution |
|---|-------|------------|
| 1 | — | — |
