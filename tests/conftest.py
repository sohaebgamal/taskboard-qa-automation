"""Shared fixtures: a real server on a free local port, reset before every test."""
import threading

import pytest
from werkzeug.serving import make_server

from app import create_app
from tests.helpers import ApiClient


@pytest.fixture(scope="session")
def live_app(tmp_path_factory):
    return create_app(tmp_path_factory.mktemp("db") / "test.db")


@pytest.fixture(scope="session")
def base_url(live_app):
    server = make_server("127.0.0.1", 0, live_app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join()


@pytest.fixture(autouse=True)
def clean_data(live_app):
    live_app.reset_data()


@pytest.fixture
def anonymous(base_url):
    return ApiClient(base_url)


@pytest.fixture
def alice(base_url):
    return ApiClient(base_url).login("alice", "alice-demo-pass")


@pytest.fixture
def bob(base_url):
    return ApiClient(base_url).login("bob", "bob-demo-pass")


@pytest.fixture
def admin(base_url):
    return ApiClient(base_url).login("admin", "admin-demo-pass")
