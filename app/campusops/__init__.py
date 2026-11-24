"""CampusOps Flask application factory."""

import os
from pathlib import Path

from flask import Flask

from . import db


def create_app(test_config=None):
    """Build an application with an optional isolated test configuration."""
    data_dir = Path(__file__).resolve().parents[2] / "instance"
    app = Flask(__name__, instance_path=str(data_dir))
    app.config.from_mapping(
        DATABASE=os.environ.get("CAMPUSOPS_DATABASE") or data_dir / "campusops.sqlite3",
    )
    if test_config is not None:
        app.config.update(test_config)

    db.init_app(app)
    return app
