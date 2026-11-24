"""Public, read-only event catalog views."""

from datetime import datetime

from flask import Blueprint, abort, render_template

from .db import get_db

bp = Blueprint("events", __name__)
EVENT_COLUMNS = "id, slug, title, starts_at, venue, description"
EVENT_PHOTOS = {
    "cloud-build-lab": "cloud-lab.webp",
    "design-studio": "design-studio.webp",
    "campus-live": "campus-live.webp",
}


@bp.app_template_global()
def event_photo(event):
    return f"images/{EVENT_PHOTOS.get(event['slug'], 'campus-commons.webp')}"


@bp.app_template_filter()
def event_schedule(value):
    start = datetime.fromisoformat(value)
    offset = start.strftime("%z")
    zone = f"UTC{offset[:3]}:{offset[3:]}" if offset else "local time"
    clock = start.strftime("%I:%M %p").lstrip("0")
    return f"{start:%a, %b} {start.day}, {start.year} · {clock} {zone}"


@bp.get("/")
def home():
    featured = get_db().execute(
        f"SELECT {EVENT_COLUMNS} FROM events ORDER BY julianday(starts_at), id LIMIT 3"
    ).fetchall()
    return render_template("home.html", events=featured)


@bp.get("/events")
def catalog():
    events = get_db().execute(
        f"SELECT {EVENT_COLUMNS} FROM events ORDER BY julianday(starts_at), id"
    ).fetchall()
    return render_template("events/catalog.html", events=events)


def get_event_or_404(event_id):
    # Python integers can exceed SQLite's signed 64-bit INTEGER range.
    if not 1 <= event_id <= 2**63 - 1:
        abort(404)

    event = get_db().execute(
        f"SELECT {EVENT_COLUMNS} FROM events WHERE id = ?", (event_id,)
    ).fetchone()
    if event is None:
        abort(404)
    return event


@bp.get("/events/<int:event_id>")
def detail(event_id):
    return render_template("events/detail.html", event=get_event_or_404(event_id))


@bp.app_errorhandler(404)
def page_not_found(_error):
    return render_template("404.html"), 404
