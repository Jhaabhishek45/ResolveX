# ResolveX

ResolveX is a Flask and SQLite campus issue-resolution platform for SRM Institute of Science and Technology, Ramapuram Campus.

It turns a campus report into a structured workflow:

`Report -> Triage -> Assign -> In Progress -> Resolved -> Verified -> Closed`

## Features

- Reporter issue submission with category, location, impact, and specific area
- Transparent rule-based department triage
- Priority and target due-date calculation
- Recurring issue detection
- Admin issue register with search, filters, assignment, and reassignment
- Technician work queue with validated status transitions and work notes
- Reporter My Issues view with ownership checks
- Verification and reopening workflow
- SQLite-backed operations dashboard and analytics
- Session authentication, role authorization, CSRF protection, and friendly errors

## Stack

- Python
- Flask 3.1.3
- SQLite
- HTML, CSS, and JavaScript

## Local setup

PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
python app.py
```

Open `http://127.0.0.1:5000/`.

## Demo accounts

The academic MVP uses email-based demo authentication:

- `abhishek@resolvex.local` - reporter
- `technician@resolvex.local` - technician
- `admin@resolvex.local` - admin

This is intentionally documented as demo authentication, not production login. Set `RESOLVEX_SECRET_KEY` before deployment.

## Main routes

- `/` - public home
- `/login` - demo sign in
- `/report` - reporter issue submission
- `/my-issues` - reporter issue history
- `/staff` - technician work queue
- `/dashboard` - admin operations dashboard
- `/issues` - admin issue register

## Data policy

The seeded locations use verified major SRM Ramapuram landmarks. Exact room, floor, and laboratory details are not invented and can be added when verified.

## Project structure

- `app.py` - Flask routes and access control
- `database.py` - SQLite schema and data access
- `models.py` - simple domain objects
- `services.py` - triage, assignment, analytics, and business rules
- `seed.py` - master and demo data setup
- `templates/` - Jinja views
- `static/` - CSS and JavaScript

## Documentation

- [Architecture](docs/architecture.md)
- [Database](docs/database.md)
- [Workflow](docs/workflow.md)
- [Viva reference](docs/viva.md)

## Deployment

The production WSGI command is defined in `Procfile` and uses Gunicorn:

```text
gunicorn app:app
```

Set `RESOLVEX_SECRET_KEY` in the hosting environment. ResolveX uses SQLite for
the academic MVP; hosted filesystems may be ephemeral, so persistent production
data requires a persistent disk or a later database migration. The local
database is intentionally ignored by Git and can be recreated with `python
seed.py`.
