"""Insert the fictional CampusOps event catalog."""

import sqlite3

import click
from flask.cli import with_appcontext

from .db import get_db

SAMPLE_EVENTS = (
    (
        "cloud-build-lab",
        "Cloud Build Lab",
        "2027-02-12T10:00:00+05:30",
        "Innovation Lab",
        "Build a small cloud service with the Campus Computing Club. "
        "Bring a laptop and work through a guided deployment with a partner.",
    ),
    (
        "design-studio",
        "Design Thinking Studio",
        "2027-02-18T14:00:00+05:30",
        "Design Commons",
        "Bring an everyday problem and turn it into a paper prototype. "
        "The Campus Design Collective will lead a short round of peer feedback.",
    ),
    (
        "campus-live",
        "Campus Live: Acoustic Night",
        "2027-02-26T18:30:00+05:30",
        "Cedar Courtyard",
        "Settle in for an evening of acoustic sets by campus performers. "
        "The Campus Arts Collective will host a short open-mic session between sets.",
    ),
)


@click.command("seed-events")
@with_appcontext
def seed_events_command():
    """Add missing sample events without modifying existing records."""
    try:
        connection = get_db()
        with connection:
            connection.executemany(
                """
                INSERT INTO events (slug, title, starts_at, venue, description)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(slug) DO NOTHING
                """,
                SAMPLE_EVENTS,
            )
    except sqlite3.Error as error:
        raise click.ClickException(
            "Could not seed events. Run init-db first and check database access."
        ) from error

    click.echo("CampusOps sample events are ready.")
