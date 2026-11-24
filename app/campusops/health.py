"""Readiness probe for the CampusOps registration workload."""

import sqlite3

from flask import Blueprint, jsonify

from .db import get_db

bp = Blueprint("health", __name__)


@bp.get("/health")
def readiness():
    try:
        # Resolve the columns used by the app and read at most one row per table.
        # EXISTS lets the probe do this without retrieving any attendee data.
        get_db().execute(
            """
            SELECT
                EXISTS (SELECT id, slug, title, starts_at, venue, description FROM main.events),
                EXISTS (SELECT id, event_id, name, email, created_at FROM main.registrations)
            """
        ).fetchone()
    except (OSError, sqlite3.Error):
        response = jsonify(status="unavailable")
        response.status_code = 503
    else:
        response = jsonify(status="ok")

    response.cache_control.no_store = True
    return response
