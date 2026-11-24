from concurrent.futures import ThreadPoolExecutor
import re
import secrets
from threading import Barrier

import pytest

from app.campusops import create_app
from app.campusops.db import get_db

FORM = "/events/1/register"
CONFIRMATION = "/events/1/registration-confirmation"
NAME = "Test Attendee"
EMAIL = "attendee@example.test"


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "DATABASE": tmp_path / "registration.sqlite3",
            "SECRET_KEY": secrets.token_hex(32),
        }
    )
    cli = application.test_cli_runner()
    for command in ("init-db", "seed-events"):
        result = cli.invoke(args=[command])
        assert result.exit_code == 0, result.output
    return application


def form_token(client, url=FORM):
    response = client.get(url)
    assert response.status_code == 200
    assert response.cache_control.no_store
    match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    assert match
    return match.group(1).decode()


def submit(client, *, url=FORM, name=NAME, email=EMAIL):
    token = form_token(client, url)
    return client.post(url, data={"name": name, "email": email, "csrf_token": token})


def saved_registrations(app):
    with app.app_context():
        return [
            tuple(row)
            for row in get_db().execute(
                "SELECT event_id, name, email FROM registrations ORDER BY id"
            )
        ]


def test_event_page_links_to_accessible_registration_form(app):
    client = app.test_client()
    detail = client.get("/events/1")
    assert b'href="/events/1/register"' in detail.data

    response = client.get(FORM)
    assert response.status_code == 200
    assert client.head(FORM).status_code == 200
    assert b"Cloud Build Lab" in response.data
    assert b"Innovation Lab" in response.data
    assert b"UTC+05:30" in response.data
    assert b'<label for="name">' in response.data
    assert b'<label for="email">' in response.data
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_success_commits_before_303_and_confirmation_refresh_does_not_write(app):
    client = app.test_client()
    response = submit(client)

    assert response.status_code == 303
    assert response.location == CONFIRMATION
    assert response.cache_control.no_store
    assert saved_registrations(app) == [(1, NAME, EMAIL)]

    for _ in range(2):
        page = client.get(response.location)
        assert page.status_code == 200
        assert page.cache_control.no_store
        assert b"Registration confirmed" in page.data
        assert b"Cloud Build Lab" in page.data
        assert NAME.encode() not in page.data
        assert EMAIL.encode() not in page.data

    assert saved_registrations(app) == [(1, NAME, EMAIL)]


def test_confirmation_requires_success_in_the_same_session(app):
    client = app.test_client()
    assert submit(client).status_code == 303
    response = app.test_client().get(CONFIRMATION)

    assert response.status_code == 302
    assert response.location == FORM
    assert b"Registration confirmed" not in response.data


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("name", None, "Enter your name."),
        ("name", "   ", "Enter your name."),
        ("name", "N" * 101, "Enter a name of 100 characters or fewer."),
        ("email", None, "Enter your email address."),
        ("email", "   ", "Enter your email address."),
        ("email", "invalid-email", "Enter a valid email address"),
        ("email", "a..b@example.test", "Enter a valid email address"),
        ("email", "a@" + "b" * 250 + ".test", "Enter an email address of 254 characters or fewer."),
    ],
)
def test_invalid_input_returns_field_error_and_retains_the_other_value(app, field, value, message):
    client = app.test_client()
    data = {"name": NAME, "email": EMAIL, "csrf_token": form_token(client)}
    if value is None:
        del data[field]
    else:
        data[field] = value

    response = client.post(FORM, data=data)

    assert response.status_code == 400
    assert message.encode() in response.data
    assert f'aria-invalid="true" aria-describedby="{field}-error"'.encode() in response.data
    assert f'href="#{field}"'.encode() in response.data
    assert f'value="{EMAIL if field == "name" else NAME}"'.encode() in response.data
    assert response.cache_control.no_store
    assert saved_registrations(app) == []


def test_redisplayed_name_is_html_escaped(app):
    client = app.test_client()
    response = submit(client, name='<b>"Name"</b>', email="invalid")

    assert response.status_code == 400
    assert b"&lt;b&gt;&#34;Name&#34;&lt;/b&gt;" in response.data
    assert b'<b>"Name"</b>' not in response.data


@pytest.mark.parametrize("token_kind", ["missing", "invalid", "other-session", "non-ascii"])
def test_invalid_csrf_returns_400_without_writing(app, token_kind):
    client = app.test_client()
    form_token(client)
    data = {"name": NAME, "email": EMAIL}
    if token_kind == "invalid":
        data["csrf_token"] = "incorrect"
    elif token_kind == "other-session":
        data["csrf_token"] = form_token(app.test_client())
    elif token_kind == "non-ascii":
        data["csrf_token"] = "✗"

    response = client.post(FORM, data=data)

    assert response.status_code == 400
    assert b"Form verification failed" in response.data
    assert NAME.encode() not in response.data
    assert EMAIL.encode() not in response.data
    assert saved_registrations(app) == []


@pytest.mark.parametrize("event_id", ["9999", "0", "not-an-id", "9223372036854775808"])
def test_unknown_event_returns_404_for_form_and_post(app, event_id):
    url = f"/events/{event_id}/register"
    client = app.test_client()
    token = form_token(client)
    assert client.get(url).status_code == 404
    assert client.post(url, data={"name": NAME, "email": EMAIL, "csrf_token": token}).status_code == 404
    assert saved_registrations(app) == []


def test_normalization_and_duplicate_handling_preserve_the_original(app):
    client = app.test_client()
    assert submit(client, name=f"  {NAME}  ", email="  ATTENDEE@EXAMPLE.TEST  ").status_code == 303

    duplicate = submit(client, name="Other Attendee", email=EMAIL)

    assert duplicate.status_code == 409
    assert b"This email is already registered for this event." in duplicate.data
    assert saved_registrations(app) == [(1, NAME, EMAIL)]


def test_same_email_can_register_for_different_events(app):
    client = app.test_client()
    assert submit(client).status_code == 303
    assert submit(client, url="/events/2/register").status_code == 303
    assert saved_registrations(app) == [(1, NAME, EMAIL), (2, NAME, EMAIL)]


def test_concurrent_duplicate_posts_create_one_registration(app):
    ready = Barrier(2, timeout=5)

    def post(email):
        client = app.test_client()
        token = form_token(client)
        ready.wait()
        return client.post(FORM, data={"name": NAME, "email": email, "csrf_token": token}).status_code

    with ThreadPoolExecutor(max_workers=2) as workers:
        responses = list(workers.map(post, [EMAIL, "  ATTENDEE@EXAMPLE.TEST  "]))

    assert sorted(responses) == [303, 409]
    assert saved_registrations(app) == [(1, NAME, EMAIL)]


def test_registration_survives_recreating_the_flask_app(app):
    assert submit(app.test_client()).status_code == 303
    restarted = create_app(
        {"TESTING": True, "DATABASE": app.config["DATABASE"], "SECRET_KEY": secrets.token_hex(32)}
    )

    assert saved_registrations(restarted) == [(1, NAME, EMAIL)]
    assert submit(restarted.test_client()).status_code == 409


def test_database_error_returns_generic_response_without_path_or_traceback(app, tmp_path):
    missing = tmp_path / "unavailable.sqlite3"
    app.config["DATABASE"] = missing
    response = app.test_client().get(FORM)

    assert response.status_code == 503
    assert b"Registration unavailable" in response.data
    assert b"unavailable.sqlite3" not in response.data
    assert b"Traceback" not in response.data
    assert not missing.exists()


def test_missing_session_key_fails_closed(app):
    app.config["SECRET_KEY"] = None
    response = app.test_client().get(FORM)
    assert response.status_code == 503
    assert b"Registration unavailable" in response.data
    assert saved_registrations(app) == []


def test_oversized_post_returns_branded_413_without_writing(app):
    client = app.test_client()
    token = form_token(client)
    response = client.post(
        FORM, data={"name": "x" * (16 * 1024), "email": EMAIL, "csrf_token": token}
    )

    assert response.status_code == 413
    assert b"Registration form is too large" in response.data
    assert saved_registrations(app) == []
