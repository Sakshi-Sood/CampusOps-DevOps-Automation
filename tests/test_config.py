import secrets

import pytest

from app.campusops import create_app


@pytest.mark.parametrize("key", [None, "too-short"])
def test_config_check_explains_missing_or_short_signing_key(tmp_path, monkeypatch, key):
    if key is None:
        monkeypatch.delenv("CAMPUSOPS_SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("CAMPUSOPS_SECRET_KEY", key)

    database = tmp_path / "absent.sqlite3"
    app = create_app({"DATABASE": database})
    result = app.test_cli_runner().invoke(args=["check-config"])

    assert result.exit_code == 1
    assert "CAMPUSOPS_SECRET_KEY" in result.output
    assert key is None or key not in result.output
    assert app.test_client().get("/health").status_code == 503
    assert not database.exists()


def test_config_check_rejects_relative_database_path(monkeypatch):
    monkeypatch.setenv("CAMPUSOPS_SECRET_KEY", secrets.token_hex(32))
    monkeypatch.setenv("CAMPUSOPS_DATABASE", "relative/path.sqlite3")

    result = create_app().test_cli_runner().invoke(args=["check-config"])

    assert result.exit_code == 1
    assert "absolute file path" in result.output
    assert "relative/path.sqlite3" not in result.output


def test_config_check_uses_environment_without_touching_storage(tmp_path, monkeypatch):
    database = tmp_path / "data dir" / "campusops.sqlite3"
    key = secrets.token_hex(32)
    monkeypatch.setenv("CAMPUSOPS_DATABASE", str(database))
    monkeypatch.setenv("CAMPUSOPS_SECRET_KEY", key)
    monkeypatch.setenv("CAMPUSOPS_SECURE_COOKIES", "1")

    app = create_app()
    result = app.test_cli_runner().invoke(args=["check-config"])

    assert result.exit_code == 0, result.output
    assert "configuration check passed" in result.output
    assert app.config["DATABASE"] == str(database)
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert key not in result.output
    assert str(database) not in result.output
    assert not database.parent.exists()
