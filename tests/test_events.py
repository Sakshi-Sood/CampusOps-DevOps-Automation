import pytest

from app.campusops import create_app
from app.campusops.db import get_db
from app.campusops.seed import SAMPLE_EVENTS


def run_cli(app, command):
    result = app.test_cli_runner().invoke(args=[command])
    assert result.exit_code == 0, result.output


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {"TESTING": True, "DATABASE": tmp_path / "catalog.sqlite3"}
    )
    run_cli(application, "init-db")
    return application


@pytest.fixture
def seeded_app(app):
    run_cli(app, "seed-events")
    return app


def test_homepage_shows_featured_events_and_catalog_link(seeded_app):
    response = seeded_app.test_client().get("/")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Discover campus events." in page
    assert "Featured events" in page
    assert "Cloud Build Lab" in page
    assert 'href="/events"' in page


def test_catalog_lists_seeded_events_with_dates_venues_and_details_links(seeded_app):
    response = seeded_app.test_client().get("/events")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    with seeded_app.app_context():
        event_ids = {
            row["slug"]: row["id"]
            for row in get_db().execute("SELECT id, slug FROM events")
        }

    for slug, title, starts_at, venue, description in SAMPLE_EVENTS:
        assert title in page
        assert venue in page
        assert description in page
        assert f'datetime="{starts_at}"' in page
        event_url = f"/events/{event_ids[slug]}"
        assert f'href="{event_url}"' in page

        detail = seeded_app.test_client().get(event_url)
        assert detail.status_code == 200
        detail_page = detail.get_data(as_text=True)
        assert f"<h1>{title}</h1>" in detail_page
        assert f'datetime="{starts_at}"' in detail_page
        assert "UTC+05:30" in detail_page
        assert venue in detail_page
        assert description in detail_page
        assert f'href="{event_url}/register"' in detail_page
    assert page.count("UTC+05:30") == len(SAMPLE_EVENTS)


def test_event_detail_shows_only_the_requested_event(seeded_app):
    slug, title, starts_at, venue, description = SAMPLE_EVENTS[1]
    with seeded_app.app_context():
        event_id = get_db().execute(
            "SELECT id FROM events WHERE slug = ?", (slug,)
        ).fetchone()["id"]

    response = seeded_app.test_client().get(f"/events/{event_id}")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f"<h1>{title}</h1>" in page
    assert f'datetime="{starts_at}"' in page
    assert venue in page
    assert description in page
    assert 'href="#registration"' in page
    assert 'id="registration"' in page
    assert SAMPLE_EVENTS[0][1] not in page


@pytest.mark.parametrize(
    "path", ["/events/9999", "/events/0", "/events/-1", "/events/not-an-id", "/events/9223372036854775808"]
)
def test_invalid_or_unknown_event_returns_branded_404(app, path):
    response = app.test_client().get(path)

    assert response.status_code == 404
    assert b"Page not found" in response.data
    assert b"Browse events" in response.data


@pytest.mark.parametrize("path", ["/", "/events"])
def test_empty_event_catalog(app, path):
    response = app.test_client().get(path)

    assert response.status_code == 200
    assert b"No events scheduled" in response.data


def test_seeding_again_keeps_existing_events_and_registrations(seeded_app):
    with seeded_app.app_context():
        connection = get_db()
        before = [tuple(row) for row in connection.execute("SELECT * FROM events ORDER BY id")]
        with connection:
            connection.execute(
                "INSERT INTO registrations (event_id, name, email) VALUES (?, ?, ?)",
                (before[0][0], "Test Attendee", "attendee@example.test"),
            )
        registration_before = tuple(
            connection.execute("SELECT * FROM registrations").fetchone()
        )

    run_cli(seeded_app, "seed-events")

    with seeded_app.app_context():
        connection = get_db()
        after = [tuple(row) for row in connection.execute("SELECT * FROM events ORDER BY id")]
        registrations = [tuple(row) for row in connection.execute("SELECT * FROM registrations")]

    assert len(before) == len(SAMPLE_EVENTS)
    assert after == before
    assert registrations == [registration_before]
