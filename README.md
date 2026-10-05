# MediCare+

**MediCare+: A Smart Medicine Reminder and Personal Health Management System** is a Flask + PostgreSQL mini-project for managing medicines, dose reminders, appointments, health records, prescriptions, emergency details, and a QR emergency health card.

## Included features

- Secure registration, login, password hashing, session protection, and CSRF checks
- Database-backed medicine, appointment, report, prescription, stock, notification, and history workflows
- Browser notifications and Web Speech API voice reminders for scheduled medicine doses
- Securely validated PDF/JPG/JPEG/PNG uploads, stored separately from database metadata
- Chart.js dashboard charts using the signed-in user’s database data
- Real QR code generation containing only emergency details (never passwords)
- Demo interaction checker with an explicit medical-information disclaimer
- Responsive desktop and mobile layout with a collapsible mobile sidebar

## Technology

- Python, Flask, Flask-SQLAlchemy, psycopg
- PostgreSQL 14+
- Bootstrap 5, vanilla JavaScript, Chart.js, Bootstrap Icons
- `qrcode[pil]` for health-card QR generation

## Setup

1. Create the PostgreSQL database and schema:

   ```powershell
   createdb -U postgres medicare
   psql -U postgres -d medicare -f database.sql
   ```

2. Create and activate a virtual environment, then install packages:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. The included `.env` file contains the local PostgreSQL connection settings. For a different environment, set these values in the shell instead:

   ```powershell
   $env:DATABASE_URL = 'postgresql://postgres:YOUR_PASSWORD@localhost:5432/medicare'
   $env:SECRET_KEY = 'use-a-long-random-production-secret'
   ```

4. Create tables and optional database-backed sample data:

   ```powershell
   flask --app app.py init-db
   flask --app app.py seed-demo
   ```

5. Start the application:

   ```powershell
   flask --app app.py run --debug
   ```

Open `http://127.0.0.1:5000`. The seed command creates `demo@medicare.local` with password `Demo@123` for a classroom demonstration. Change/remove this account in any non-demo deployment.

## Deploying on Render

MediCare+ is configured for seamless deployment on Render using either **Render Blueprints (Automated)** or **Manual Setup**:

### Method 1: Render Blueprint (Recommended - 1-Click Setup)

1. Push your repository to GitHub (ensure `.env` and `.venv/` are excluded, which `.gitignore` handles automatically).
2. Log into [Render](https://render.com) and click **New +** -> **Blueprint**.
3. Connect your GitHub repository.
4. Render will read `render.yaml` and automatically configure:
   - **PostgreSQL Database** (`medicare-db` on the Free tier)
   - **Web Service** (`medicare-web`)
   - Auto-generated `SECRET_KEY`
   - Linked `DATABASE_URL`
   - Auto-initialization of database tables on startup
5. Click **Apply**. Render will build and deploy the app!

### Method 2: Manual Web Service Setup

If you prefer to configure services manually in Render:

1. Create a **PostgreSQL Database** on Render:
   - Name: `medicare-db`
   - Copy the **Internal Database URL** (or External Database URL).
2. Create a **Web Service**:
   - Environment: `Python`
   - Root Directory: `medicare` (leave empty if repository root contains `app.py`)
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `flask --app app.py init-db && gunicorn app:app`
3. Under **Environment Variables**, add:
   - `DATABASE_URL`: Your Render PostgreSQL database URL
   - `SECRET_KEY`: A secure random string
   - `PYTHON_VERSION`: `3.11.9`
4. Deploy the service.

Optional: To seed demo data (`demo@medicare.local` / `Demo@123`), run `flask --app app.py seed-demo` from the Render Shell.

## Project structure

```text
├── render.yaml            # Render Blueprint for automated multi-service deploy
├── .gitignore             # Git ignore rules for virtual environments & secrets
└── medicare/
    ├── app.py             # Flask routes, models, validations & CLI commands
    ├── config.py          # Configuration & Render postgres:// URL parsing
    ├── database.sql       # PostgreSQL database schema definition
    ├── requirements.txt   # Production Python dependencies
    ├── Procfile           # Process definition for Render / Gunicorn
    ├── runtime.txt        # Specifies Python 3.11.9 runtime for Render
    ├── build.sh           # Shell build script for Render deployments
    ├── .env.example       # Example environment variables template
    ├── templates/         # Jinja2 templates (dashboard, auth, features)
    ├── static/css/        # Stylesheets (responsive healthcare UI)
    ├── static/js/         # Client-side scripts (charts, reminders)
    └── uploads/           # User uploads (reports, prescriptions, profiles)
```

## Future improvements

- Integrate a verified medicine-interaction provider and clinical review process.
- Send real SMS/email emergency alerts via a configured provider.
- Add password reset email, audit logs, and two-factor authentication.
- Add calendar export and a progressive web app/offline reminder service worker.

> Medical disclaimer: MediCare+ is an educational mini-project. Reminder and interaction features do not replace professional medical advice.
