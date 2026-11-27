# CampusOps

CampusOps is a cloud provisioning, automated deployment, and monitoring project built around a campus event registration service. The target architecture uses Terraform for AWS infrastructure, Ansible for server configuration, and Nagios Core for health checks and alerting. Flask and SQLite provide the application workload. Nginx and Gunicorn are part of the planned Linux deployment.

## Current status

The local application provides a seeded campus event catalog, event details, registration with validation and CSRF protection, confirmation, and a SQLite read-readiness endpoint. Cloud provisioning, automated deployment, and infrastructure monitoring are planned.

| Layer | Technology |
| --- | --- |
| Application | Python 3.11+, Flask, Jinja, HTML and CSS |
| Storage | SQLite via Python's standard library |
| Local verification | pytest and isolated SQLite fixtures |
| Planned deployment | AWS EC2, Terraform, Ansible, Nginx, Gunicorn, systemd, and Nagios Core |

## Run locally

Create a virtual environment in your checkout. The development requirements include the pinned application runtime and pytest. Use a separate environment for each operating system.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r app/requirements-dev.txt
.\.venv\Scripts\python.exe -m flask --app app.campusops init-db
.\.venv\Scripts\python.exe -m flask --app app.campusops seed-events
$env:CAMPUSOPS_SECRET_KEY = (.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))").Trim()
.\.venv\Scripts\python.exe -m flask --app app.campusops check-config
.\.venv\Scripts\python.exe -m flask --app app.campusops run
```

### WSL Ubuntu

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r app/requirements-dev.txt
.venv/bin/python -m flask --app app.campusops init-db
.venv/bin/python -m flask --app app.campusops seed-events
export CAMPUSOPS_SECRET_KEY="$(.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))')"
.venv/bin/python -m flask --app app.campusops check-config
.venv/bin/python -m flask --app app.campusops run
```

Open the [event catalog](http://127.0.0.1:5000/events), select an event, and register using synthetic attendee data, such as `attendee@example.test`. Stop the local server with Ctrl+C.

`init-db` creates the schema. `seed-events` inserts missing fictional events by slug. Both commands can be rerun and preserve existing registrations and event rows.

## Environment variables

| Variable | Behavior |
| --- | --- |
| `CAMPUSOPS_DATABASE` | Absolute path to the SQLite file. Defaults to `instance/campusops.sqlite3` in the local checkout. Use an external data directory in a deployment, such as `/var/lib/campusops`. |
| `CAMPUSOPS_SECRET_KEY` | Required for registration. Supply a securely stored random signing key and reuse it across workers and restarts. Keep it outside version control. |
| `CAMPUSOPS_SECURE_COOKIES` | Set to `1` when serving over HTTPS. Leave unset for loopback HTTP development. |

`check-config` returns a nonzero exit status for a missing or short signing key or a relative database path. It performs no database operations and prints no secret values. Replacing the key or clearing the browser cookie invalidates browser confirmation state. The SQLite records persist.

## Readiness and tests

Run `curl.exe -i http://127.0.0.1:5000/health` in PowerShell or `curl -i http://127.0.0.1:5000/health` in WSL while the local server is running.

- `200 {"status":"ok"}` means Flask could read the initialized event and registration schema.
- `503 {"status":"unavailable"}` means the database or schema could not be read. Check the configured path, initialization, and permissions in the service environment.

The response is non-cacheable and includes only a status. The probe checks SQLite reads. A successful registration separately verifies the write path. Missing signing-key configuration prevents registration and leaves database-read readiness unchanged.

Run the full test suite with `.\.venv\Scripts\python.exe -m pytest -q` on PowerShell or `.venv/bin/python -m pytest -q` on WSL. Run `python -m pytest tests/test_health.py -q` with the virtual environment active to exercise the health cases. Tests use temporary SQLite databases.

## Deployment handoff

On Linux, Gunicorn will call `app.campusops:create_app()` from the release root. Nginx will proxy requests to Gunicorn through a Unix socket. systemd will supply the service environment and supervise Gunicorn under a dedicated user. Flask's development server is for local use.

Install the application packages from `app/requirements.txt`. The deployment role will need to install and pin Gunicorn separately. Provide a persistent database path writable by the service user and a protected signing key. Run `check-config` and initialize the database before starting workers. Keep the database outside the release directory so replacing code does not replace data.

## Current limitations

The catalog is seeded with fictional events. The demo uses local SQLite on one application host and browser-scoped confirmation without an account or email notification. Use synthetic data over HTTP. Linux service integration, deployment throughput, AWS infrastructure, and Nagios alerting remain to be verified in their implementation phases.

## Repository layout

| Directory | Purpose |
| --- | --- |
| `app/campusops/` | Flask package, database schema, templates, and static assets |
| `tests/` | Automated tests with isolated databases |
| `docs/` | [Requirements](docs/requirements.md), [architecture](docs/architecture.md), and [acceptance checks](docs/acceptance-tests.md) |
| `infra/` | [Terraform configuration and provisioning review](infra/README.md) |
| `ansible/` | Planned server configuration and deployment roles |
| `scripts/` | Planned deployment and inventory automation |
