"""CampusOps Flask application factory."""

import os
from pathlib import Path

import click
from flask import Flask, current_app
from flask.cli import with_appcontext

from . import db, events, health, registration, seed


@click.command("check-config")
@with_appcontext
def check_config():
    """Check deployment settings without creating files or printing secrets."""
    key = current_app.secret_key
    if not key or len(key.strip()) < 32:
        raise click.ClickException(
            "Set CAMPUSOPS_SECRET_KEY to a stable, randomly generated value "
            "of at least 32 characters."
        )
    if not Path(current_app.config["DATABASE"]).is_absolute():
        raise click.ClickException("Set CAMPUSOPS_DATABASE to an absolute file path.")
    click.echo("CampusOps configuration check passed.")


def create_app(test_config=None):
    """Build an application with an optional isolated test configuration."""
    data_dir = Path(__file__).resolve().parents[2] / "instance"
    app = Flask(__name__, instance_path=str(data_dir))
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("CAMPUSOPS_SECRET_KEY"),
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("CAMPUSOPS_SECURE_COOKIES") == "1",
        DATABASE=os.environ.get("CAMPUSOPS_DATABASE") or data_dir / "campusops.sqlite3",
    )
    if test_config is not None:
        app.config.update(test_config)

    db.init_app(app)
    app.register_blueprint(events.bp)
    app.register_blueprint(health.bp)
    app.register_blueprint(registration.bp)
    app.cli.add_command(seed.seed_events_command)
    app.cli.add_command(check_config)
    return app
