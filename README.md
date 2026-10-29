# HLB Jim Roberts Performance Hub — FastAPI Starter

A firm-wide starter application for employee KPI capture, review/approval, partner dashboards and Excel migration.

## Quick start
1. Install Python 3.11+.
2. Copy `.env.example` to `.env` and change `SECRET_KEY`.
3. Create and activate a virtual environment.
4. Run `pip install -r requirements.txt`.
5. Run `python -m app.seed` to create demo-safe roles and an admin account.
6. Start with `uvicorn app.main:app --reload`.
7. Browse to `http://127.0.0.1:8000` and API docs at `/docs`.

## Password reset email
Forgot-password links are delivered through SMTP. Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM_EMAIL` in `.env`; `SMTP_USE_TLS=true` enables STARTTLS. `SMTP_USERNAME` and `SMTP_PASSWORD` may be left empty for an SMTP relay that does not require authentication. Set `FRONTEND_URL` to the React app's public base URL so reset links return to the correct site, then restart the API. Reset links expire after 30 minutes and can only be used once.

Default seeded admin: `admin@hlb.local` / `ChangeMe123!` — change immediately.

## Import the HLB workbook
Place `HLB_Master_Performance_System_advanced.xlsx` in the project root, then run:
`python -m app.import_excel HLB_Master_Performance_System_advanced.xlsx`

The importer reads `Employees`, `KPI_Definitions`, and `Entries`, upserts records, and does not invent performance values.

## Features
- JWT login endpoint and role model: Employee, Manager, Partner, Admin
- Employees, KPIs and monthly Entries CRUD/API
- Idempotent monthly KPI generation
- Submit/review/approve/reject workflow
- Partner dashboard API and HTML page
- SQLite development database, configurable for PostgreSQL using `DATABASE_URL`
- HLB blue-led UI with red accents

## Production notes
Use PostgreSQL, HTTPS, a managed secret store, backups, Microsoft Entra ID/SSO, audit logging and migrations (Alembic). SQLite is for development only.
