import pytest

pytestmark = pytest.mark.api


def test_health_is_public(anonymous):
    response = anonymous.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_with_valid_credentials(anonymous):
    response = anonymous.post(
        "/api/login", json={"username": "alice", "password": "alice-demo-pass"}
    )
    assert response.status_code == 200
    assert response.json() == {"username": "alice", "role": "user"}


def test_login_with_wrong_password(anonymous):
    response = anonymous.post("/api/login", json={"username": "alice", "password": "wrong"})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "body",
    [{}, {"username": "alice"}, {"password": "x"}, {"username": 1, "password": 2}],
    ids=["empty", "no-password", "no-username", "wrong-types"],
)
def test_login_rejects_incomplete_body(anonymous, body):
    assert anonymous.post("/api/login", json=body).status_code == 400


def test_login_rejects_non_json_body(anonymous):
    response = anonymous.post("/api/login", data={"username": "alice", "password": "x"})
    assert response.status_code == 415


def test_me_returns_the_signed_in_user(alice):
    assert alice.get("/api/me").json() == {"username": "alice", "role": "user"}


def test_logout_ends_the_session(alice):
    assert alice.post("/api/logout").status_code == 204
    assert alice.get("/api/me").status_code == 401
