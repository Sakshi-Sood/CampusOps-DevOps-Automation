# CampusOps

CampusOps is a cloud provisioning, automated deployment, and monitoring project built around a campus event registration service. The target architecture uses Terraform for AWS infrastructure, Ansible for server configuration, and Nagios Core for health checks and alerting. Flask and SQLite provide the application workload. Nginx and Gunicorn are part of the planned Linux deployment.

## Current status

The Flask application includes a homepage, SQLite-backed event catalog, and event detail pages. Registration submission and the health endpoint are planned. Infrastructure provisioning, deployment automation, and monitoring are also planned.

## Run locally

Use Python 3.11 or newer. A virtual environment keeps the project's Python packages separate from other projects. Run these commands from the repository root in PowerShell.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r app/requirements-dev.txt
.\.venv\Scripts\python.exe -m flask --app app.campusops init-db
.\.venv\Scripts\python.exe -m flask --app app.campusops seed-events
.\.venv\Scripts\python.exe -m flask --app app.campusops run
```

On WSL Ubuntu, create the environment with `python3 -m venv .venv` and use `.venv/bin/python` for the remaining commands. Create separate virtual environments for Windows and Linux if switching between them. WSL is the planned control environment for Linux-based deployment tools.

Open [CampusOps](http://127.0.0.1:5000/) or go directly to [the event catalog](http://127.0.0.1:5000/events). Stop the development server with Ctrl+C. Gunicorn will load the same application factory on the deployed Linux host.

`init-db` creates the tables. `seed-events` inserts missing fictional events by slug. Both commands can be rerun without deleting registrations or overwriting event rows. The default database is `instance/campusops.sqlite3`, outside the application source directory. Set `CAMPUSOPS_DATABASE` to an absolute file path to override it. The planned EC2 deployment will use a persistent path such as `/var/lib/campusops/campusops.sqlite3` outside the release tree. Use synthetic data in local development and tests.

## Test locally

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests use temporary SQLite databases.

## Repository layout

| Directory | Purpose |
| --- | --- |
| `app/campusops/` | Flask package, database schema, templates, and static assets |
| `tests/` | Automated tests with isolated databases |
| `docs/` | [Requirements](docs/requirements.md), [architecture](docs/architecture.md), and [acceptance checks](docs/acceptance-tests.md) |
| `infra/` | Planned Terraform infrastructure definitions |
| `ansible/` | Planned server configuration and deployment roles |
| `scripts/` | Planned deployment and inventory automation |
