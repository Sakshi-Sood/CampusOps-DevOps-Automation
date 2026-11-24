"""Event registration form, submission, and confirmation."""

import re
import secrets
import sqlite3

from flask import (
    Blueprint, abort, current_app, redirect, render_template, request, session, url_for,
)

from .db import get_db
from .events import get_event_or_404

bp = Blueprint("registration", __name__)
NAME_LIMIT = 100
EMAIL_LIMIT = 254
EMAIL_ATOM = r"[a-z0-9!#$%&'*+/=?^_`{|}~-]+"
DOMAIN_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
EMAIL_PATTERN = re.compile(
    rf"{EMAIL_ATOM}(?:\.{EMAIL_ATOM})*@(?:{DOMAIN_LABEL}\.)+{DOMAIN_LABEL}",
    re.ASCII,
)


@bp.after_request
def keep_registration_responses_out_of_cache(response):
    response.cache_control.no_store = True
    return response


@bp.route("/events/<int:event_id>/register", methods=["GET", "POST"])
def register(event_id):
    event = get_event_or_404(event_id)
    if not current_app.secret_key:
        return registration_unavailable()

    if request.method != "POST":
        token = session.get("registration_csrf")
        if token is None:
            token = secrets.token_urlsafe(32)
            session["registration_csrf"] = token
        return render_form(event, token)

    request.max_content_length = 16 * 1024
    token = session.get("registration_csrf")
    submitted_token = request.form.get("csrf_token", "")
    if not token or not secrets.compare_digest(token.encode(), submitted_token.encode()):
        return render_template(
            "registration/problem.html",
            title="Form verification failed",
            message="Open a fresh registration form and submit it again.",
            event_id=event_id,
        ), 400

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    errors = {}
    if not name:
        errors["name"] = "Enter your name."
    elif len(name) > NAME_LIMIT:
        errors["name"] = "Enter a name of 100 characters or fewer."

    if not email:
        errors["email"] = "Enter your email address."
    elif len(email) > EMAIL_LIMIT:
        errors["email"] = "Enter an email address of 254 characters or fewer."
    elif len(email.partition("@")[0]) > 64 or not EMAIL_PATTERN.fullmatch(email):
        errors["email"] = "Enter a valid email address, such as name@example.test."

    if errors:
        # Preserve usable input without sending oversized values back to the browser.
        values = {
            "name": name if len(name) <= NAME_LIMIT else "",
            "email": email if len(email) <= EMAIL_LIMIT else "",
        }
        return render_form(event, token, values, errors), 400

    connection = get_db()
    with connection:
        inserted = connection.execute(
            """
            INSERT INTO registrations (event_id, name, email)
            VALUES (?, ?, ?)
            ON CONFLICT (event_id, email) DO NOTHING
            """,
            (event["id"], name, email),
        ).rowcount

    if not inserted:
        return render_form(
            event,
            token,
            {"name": name, "email": email},
            {"email": "This email is already registered for this event."},
        ), 409

    session["confirmed_event_id"] = event["id"]
    return redirect(url_for("registration.confirmation", event_id=event["id"]), code=303)


@bp.get("/events/<int:event_id>/registration-confirmation")
def confirmation(event_id):
    event = get_event_or_404(event_id)
    if session.get("confirmed_event_id") != event["id"]:
        return redirect(url_for("registration.register", event_id=event["id"]))
    return render_template("registration/confirmation.html", event=event)


def render_form(event, csrf_token, values=None, errors=None):
    return render_template(
        "registration/form.html",
        event=event,
        csrf_token=csrf_token,
        values=values or {},
        errors=errors or {},
        name_limit=NAME_LIMIT,
        email_limit=EMAIL_LIMIT,
    )


@bp.errorhandler(413)
def form_too_large(_error):
    return render_template(
        "registration/problem.html",
        title="Registration form is too large",
        message="Open a fresh form and enter only your name and email address.",
        event_id=request.view_args["event_id"],
    ), 413


@bp.errorhandler(OSError)
@bp.errorhandler(sqlite3.Error)
def registration_database_error(error):
    current_app.logger.error("Registration database operation failed: %s", type(error).__name__)
    return registration_unavailable()


def registration_unavailable():
    return render_template(
        "registration/problem.html",
        title="Registration unavailable",
        message="Registration could not be completed right now. Please try again later.",
    ), 503
