from contextlib import closing
import sqlite3

import pytest

from app.campusops import create_app


def make_app(database):
    return create_app({"TESTING": True, "DATABASE": database, "SECRET_KEY": None})


def assert_unavailable(response):
    assert response.status_code == 503
    assert response.get_json() == {"status": "unavailable"}
    assert response.cache_control.no_store
    assert "Set-Cookie" not in response.headers


def test_initialized_schema_is_healthy_without_seed_data_or_session_key(tmp_path):
    database = tmp_path / "empty-initialized.sqlite3"
    app = make_app(database)
    cli = app.test_cli_runner()
    result = cli.invoke(args=["init-db"])
    assert result.exit_code == 0, result.output
    original = database.read_bytes()

    response = app.test_client().get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    assert response.cache_control.no_store
    assert "Set-Cookie" not in response.headers
    assert database.read_bytes() == original


def test_unavailable_database_returns_503_without_creating_a_file(tmp_path):
    database = tmp_path / "missing.sqlite3"
    app = make_app(database)
    assert not database.exists()

    assert_unavailable(app.test_client().get("/health"))
    assert not database.exists()


def test_uninitialized_database_returns_503_without_initializing_it(tmp_path):
    database = tmp_path / "uninitialized.sqlite3"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE unused (id INTEGER PRIMARY KEY)")
        connection.commit()
    original = database.read_bytes()

    assert_unavailable(make_app(database).test_client().get("/health"))
    assert database.read_bytes() == original


def test_incomplete_registration_schema_returns_503(tmp_path):
    database = tmp_path / "incomplete.sqlite3"
    app = make_app(database)
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0, result.output
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("ALTER TABLE registrations RENAME COLUMN email TO unused")
        connection.commit()

    assert_unavailable(app.test_client().get("/health"))


def test_invalid_database_file_returns_503_without_exposing_details(tmp_path):
    database = tmp_path / "invalid.sqlite3"
    database.write_bytes(b"not a SQLite database")

    response = make_app(database).test_client().get("/health")

    assert_unavailable(response)
    assert database.name.encode() not in response.data
    assert b"not a SQLite database" not in response.data


@pytest.mark.parametrize("path", ["/", "/events", "/events/1"])
def test_catalog_database_failure_has_generic_503_page(tmp_path, path):
    database = tmp_path / "catalog-missing.sqlite3"
    response = make_app(database).test_client().get(path)

    assert response.status_code == 503
    assert response.cache_control.no_store
    assert b"Events temporarily unavailable" in response.data
    assert database.name.encode() not in response.data
    assert b"Traceback" not in response.data
    assert not database.exists()
