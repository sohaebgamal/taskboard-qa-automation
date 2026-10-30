import pytest

pytestmark = pytest.mark.security

MAX_FAILED_LOGINS = 5


def fail_login(client, username, times):
    for _ in range(times):
        client.post("/api/login", json={"username": username, "password": "wrong"})


def test_account_locks_after_repeated_failures(anonymous):
    fail_login(anonymous, "alice", MAX_FAILED_LOGINS)
    response = anonymous.post(
        "/api/login", json={"username": "alice", "password": "alice-demo-pass"}
    )
    assert response.status_code == 429


def test_failures_below_the_limit_do_not_lock(anonymous):
    fail_login(anonymous, "alice", MAX_FAILED_LOGINS - 1)
    response = anonymous.post(
        "/api/login", json={"username": "alice", "password": "alice-demo-pass"}
    )
    assert response.status_code == 200


def test_successful_login_clears_the_failure_count(anonymous):
    fail_login(anonymous, "alice", MAX_FAILED_LOGINS - 1)
    anonymous.login("alice", "alice-demo-pass")
    fail_login(anonymous, "alice", MAX_FAILED_LOGINS - 1)
    anonymous.login("alice", "alice-demo-pass")


def test_lockout_of_one_user_does_not_affect_another(anonymous):
    fail_login(anonymous, "alice", MAX_FAILED_LOGINS)
    anonymous.login("bob", "bob-demo-pass")


def test_login_does_not_reveal_which_usernames_exist(anonymous):
    known = anonymous.post("/api/login", json={"username": "alice", "password": "wrong"})
    unknown = anonymous.post("/api/login", json={"username": "ghost", "password": "wrong"})
    assert known.status_code == unknown.status_code == 401
    assert known.json() == unknown.json()


@pytest.mark.parametrize("payload", ["' OR '1'='1", "alice'--", '" OR ""="'])
def test_sql_injection_in_login_does_not_sign_in(anonymous, payload):
    response = anonymous.post("/api/login", json={"username": payload, "password": payload})
    assert response.status_code == 401


def test_sql_in_task_title_is_stored_as_plain_text(alice):
    title = "'); DROP TABLE tasks;--"
    task = alice.create_task(title)
    assert alice.get(f"/api/tasks/{task['id']}").json()["title"] == title
    assert len(alice.get("/api/tasks").json()["tasks"]) == 1


def test_session_cookie_flags(anonymous):
    response = anonymous.post(
        "/api/login", json={"username": "alice", "password": "alice-demo-pass"}
    )
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


@pytest.mark.parametrize(
    "header,value",
    [
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", "DENY"),
        ("Content-Security-Policy", "default-src 'self'"),
    ],
)
def test_security_headers(anonymous, header, value):
    assert anonymous.get("/login").headers.get(header) == value
