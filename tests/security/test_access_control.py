import pytest

pytestmark = pytest.mark.security


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/me"),
        ("get", "/api/tasks"),
        ("post", "/api/tasks"),
        ("get", "/api/tasks/1"),
        ("patch", "/api/tasks/1"),
        ("delete", "/api/tasks/1"),
        ("get", "/api/admin/users"),
    ],
)
def test_protected_endpoints_need_a_session(anonymous, method, path):
    assert getattr(anonymous, method)(path).status_code == 401


def test_user_cannot_read_another_users_task(alice, bob):
    task = alice.create_task("private")
    assert bob.get(f"/api/tasks/{task['id']}").status_code == 404


def test_user_cannot_edit_another_users_task(alice, bob):
    task = alice.create_task("private")
    assert bob.patch(f"/api/tasks/{task['id']}", json={"title": "hacked"}).status_code == 404
    assert alice.get(f"/api/tasks/{task['id']}").json()["title"] == "private"


def test_user_cannot_delete_another_users_task(alice, bob):
    task = alice.create_task("private")
    assert bob.delete(f"/api/tasks/{task['id']}").status_code == 404
    assert alice.get(f"/api/tasks/{task['id']}").status_code == 200


def test_task_list_only_shows_own_tasks(alice, bob):
    alice.create_task("alice's")
    assert bob.get("/api/tasks").json()["tasks"] == []


def test_regular_user_cannot_list_users(alice):
    assert alice.get("/api/admin/users").status_code == 403


def test_admin_user_list_has_no_password_data(admin):
    response = admin.get("/api/admin/users")
    assert response.status_code == 200
    assert {"username": "alice", "role": "user"} in response.json()["users"]
    assert "password" not in response.text
