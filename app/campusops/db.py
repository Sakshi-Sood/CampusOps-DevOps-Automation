"""SQLite connection lifecycle and non-destructive schema initialization."""

import sqlite3
from contextlib import closing
from pathlib import Path

import click
from flask import current_app, g
from flask.cli import with_appcontext


def _connect(path, *, create=False):
    mode = "rwc" if create else "rw"
    database_uri = f"{Path(path).resolve().as_uri()}?mode={mode}"
    connection = sqlite3.connect(database_uri, uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_db():
    """Reuse one connection during the current Flask application context."""
    if "db" not in g:
        g.db = _connect(current_app.config["DATABASE"])
    return g.db


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Create the database schema while preserving existing records."""
    path = Path(current_app.config["DATABASE"])
    try:
        with current_app.open_resource("schema.sql", mode="r") as schema_file:
            schema = schema_file.read()
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(_connect(path, create=True)) as connection:
            connection.executescript(schema)
    except (OSError, sqlite3.Error) as error:
        raise click.ClickException(
            "Could not initialize the database. Check the configured path and permissions."
        ) from error
    click.echo("CampusOps database schema initialized.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
