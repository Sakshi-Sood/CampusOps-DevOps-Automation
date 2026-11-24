# CampusOps

CampusOps is a cloud provisioning, automated deployment, and monitoring project built around a campus event registration service. The target architecture uses Terraform for AWS infrastructure, Ansible for server configuration, and Nagios Core for health checks and alerting. Flask and SQLite provide the application workload. Nginx and Gunicorn are part of the planned Linux deployment.

## Current status

The Flask application includes a homepage, SQLite-backed event catalog, event details, and registration with validation and confirmation. A SQLite readiness endpoint is available at `/health`. Infrastructure provisioning, deployment automation, and monitoring are also planned.

## Run locally

Use Python 3.11 or newer. A virtual environment keeps the project's Python packages separate from other projects. Run these commands from the repository root in PowerShell.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r app/requirements-dev.txt
.\.venv\Scripts\python.exe -m flask --app app.campusops init-db
.\.venv\Scripts\python.exe -m flask --app app.campusops seed-events
$env:CAMPUSOPS_SECRET_KEY = (.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))").Trim()
.\.venv\Scripts\python.exe -m flask --app app.campusops run
```

On WSL Ubuntu, create the environment with `python3 -m venv .venv` and use `.venv/bin/python` for the remaining commands. Create separate virtual environments for Windows and Linux if switching between them. WSL is the planned control environment for Linux-based deployment tools.

Open [CampusOps](http://127.0.0.1:5000/) or go directly to [the event catalog](http://127.0.0.1:5000/events). Stop the development server with Ctrl+C. Gunicorn will load the same application factory on the deployed Linux host.

`init-db` creates the tables. `seed-events` inserts missing fictional events by slug. Both commands can be rerun without deleting registrations or overwriting event rows. The default database is `instance/campusops.sqlite3`, outside the application source directory. Set `CAMPUSOPS_DATABASE` to an absolute file path to override it. The planned EC2 deployment will use a persistent path such as `/var/lib/campusops/campusops.sqlite3` outside the release tree. Use synthetic data in local development and tests.

Open an event and choose **Register for this event**. Use synthetic values such as a test attendee name and an address ending in `@example.test`. Try registering the same address for the same event again to see the duplicate response.

`CAMPUSOPS_SECRET_KEY` signs Flask session cookies and must be set for registration. Keep it outside version control. On WSL, use `export CAMPUSOPS_SECRET_KEY="$(.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))')"`. Reuse the same securely stored key across deployment workers and restarts. With HTTPS, set `CAMPUSOPS_SECURE_COOKIES=1`. The session holds the CSRF token and most recently confirmed event ID. Changing the secret or clearing the cookie removes browser confirmation state. Saved registrations remain in SQLite.

## Check readiness

With the local server running, use `curl.exe -i http://127.0.0.1:5000/health` in PowerShell or `curl -i http://127.0.0.1:5000/health` in WSL.

- `200 {"status":"ok"}` means Flask could read the expected event and registration schema.
- `503 {"status":"unavailable"}` means Flask could not read that schema. Check the configured database path, initialization, and permissions in the application environment.

The readiness check leaves attendee data out of the response and does not initialize the database or attempt a write. A successful registration separately verifies the write path.

## Deployment entry point

On Linux, launch Gunicorn from the repository root with the WSGI target `'app.campusops:create_app()'`. Set `CAMPUSOPS_DATABASE` to a persistent absolute path writable by the service user and set a stable `CAMPUSOPS_SECRET_KEY` in the service environment before startup. Run `init-db` explicitly before starting the workers. App creation does not create a database or generate a signing key. A missing key leaves registration unavailable while the health check still reports SQLite readiness. The Nginx and Gunicorn integration will be verified during deployment.

## Test locally

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests use temporary SQLite databases. To exercise readiness failures safely, run `.\.venv\Scripts\python.exe -m pytest tests/test_health.py -q`.

## Repository layout

| Directory | Purpose |
| --- | --- |
| `app/campusops/` | Flask package, database schema, templates, and static assets |
| `tests/` | Automated tests with isolated databases |
| `docs/` | [Requirements](docs/requirements.md), [architecture](docs/architecture.md), and [acceptance checks](docs/acceptance-tests.md) |
| `infra/` | Planned Terraform infrastructure definitions |
| `ansible/` | Planned server configuration and deployment roles |
| `scripts/` | Planned deployment and inventory automation |
