from concurrent.futures import ThreadPoolExecutor
import sqlite3
from threading import Barrier

import pytest

from app.campusops import create_app
from app.campusops.db import get_db


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {"TESTING": True, "DATABASE": tmp_path / "isolated.sqlite3"}
    )
    result = application.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0, result.output
    return application


def add_event(connection, slug):
    with connection:
        cursor = connection.execute(
            "INSERT INTO events (slug, title, starts_at, venue, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (slug, "Platform Workshop", "2027-02-12T10:00:00+05:30", "Lab A", "Test fixture"),
        )
    return cursor.lastrowid


def register(connection, event_id, email="attendee@example.test"):
    with connection:
        connection.execute(
            "INSERT INTO registrations (event_id, name, email) VALUES (?, ?, ?)",
            (event_id, "Test Attendee", email),
        )


def test_app_creation_and_database_lookup_do_not_create_a_database(tmp_path):
    database = tmp_path / "missing.sqlite3"
    application = create_app({"TESTING": True, "DATABASE": database})

    with application.app_context(), pytest.raises(sqlite3.OperationalError):
        get_db()

    assert not database.exists()


def test_initialization_is_repeatable_and_data_survives_a_new_app(app):
    with app.app_context():
        event_id = add_event(get_db(), "platform-workshop")
        register(get_db(), event_id)

    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0, result.output

    restarted = create_app({"TESTING": True, "DATABASE": app.config["DATABASE"]})
    with restarted.app_context():
        row = get_db().execute(
            "SELECT event_id, created_at FROM registrations"
        ).fetchone()

    assert row["event_id"] == event_id
    assert row["created_at"].endswith("Z")


def test_foreign_key_rejects_registration_for_unknown_event(app):
    with app.app_context():
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            register(get_db(), 99)
        assert get_db().execute("SELECT count(*) FROM registrations").fetchone()[0] == 0


def test_email_can_register_once_per_event(app):
    with app.app_context():
        connection = get_db()
        first_event = add_event(connection, "platform-workshop")
        second_event = add_event(connection, "cloud-workshop")
        register(connection, first_event)

        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            register(connection, first_event)

        register(connection, second_event)
        assert connection.execute("SELECT count(*) FROM registrations").fetchone()[0] == 2


def test_concurrent_database_writes_accept_only_one_registration(app):
    with app.app_context():
        event_id = add_event(get_db(), "platform-workshop")
    ready = Barrier(2, timeout=5)

    def submit():
        with app.app_context():
            connection = get_db()
            ready.wait()
            try:
                register(connection, event_id)
            except sqlite3.IntegrityError as error:
                assert error.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_UNIQUE
                return False
        return True

    with ThreadPoolExecutor(max_workers=2) as workers:
        requests = [workers.submit(submit) for _ in range(2)]
        assert sorted(request.result() for request in requests) == [False, True]

    with app.app_context():
        assert get_db().execute("SELECT count(*) FROM registrations").fetchone()[0] == 1


def test_context_reuses_and_closes_its_database_connection(app):
    with app.app_context():
        connection = get_db()
        assert get_db() is connection
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        connection.execute("SELECT 1")
