import pytest

pytestmark = pytest.mark.api

MAX_TITLE = 120


def test_create_task(alice):
    response = alice.post("/api/tasks", json={"title": "Review PRD"})
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Review PRD"
    assert body["done"] is False
    assert isinstance(body["id"], int)


def test_list_returns_tasks_in_creation_order(alice):
    first = alice.create_task("first")
    second = alice.create_task("second")
    assert alice.get("/api/tasks").json()["tasks"] == [first, second]


def test_get_single_task(alice):
    task = alice.create_task()
    response = alice.get(f"/api/tasks/{task['id']}")
    assert response.status_code == 200
    assert response.json() == task


def test_edit_title_is_saved(alice):
    task = alice.create_task("old")
    assert alice.patch(f"/api/tasks/{task['id']}", json={"title": "new"}).status_code == 200
    assert alice.get(f"/api/tasks/{task['id']}").json()["title"] == "new"


@pytest.mark.parametrize("done", [True, False])
def test_done_flag_is_saved(alice, done):
    task = alice.create_task()
    alice.patch(f"/api/tasks/{task['id']}", json={"done": not done})
    assert alice.patch(f"/api/tasks/{task['id']}", json={"done": done}).status_code == 200
    assert alice.get(f"/api/tasks/{task['id']}").json()["done"] is done


def test_editing_one_field_keeps_the_other(alice):
    task = alice.create_task("keep me")
    alice.patch(f"/api/tasks/{task['id']}", json={"done": True})
    assert alice.get(f"/api/tasks/{task['id']}").json()["title"] == "keep me"
    alice.patch(f"/api/tasks/{task['id']}", json={"title": "changed"})
    assert alice.get(f"/api/tasks/{task['id']}").json()["done"] is True


def test_delete_task(alice):
    task = alice.create_task()
    assert alice.delete(f"/api/tasks/{task['id']}").status_code == 204
    assert alice.get(f"/api/tasks/{task['id']}").status_code == 404
    assert alice.get("/api/tasks").json()["tasks"] == []


@pytest.mark.parametrize(
    "title",
    ["", "   ", "x" * (MAX_TITLE + 1), None, 123, ["list"]],
    ids=["empty", "spaces", "too-long", "null", "number", "list"],
)
def test_create_rejects_invalid_title(alice, title):
    assert alice.post("/api/tasks", json={"title": title}).status_code == 400
    assert alice.get("/api/tasks").json()["tasks"] == []


def test_create_accepts_title_at_the_length_limit(alice):
    title = "x" * MAX_TITLE
    assert alice.post("/api/tasks", json={"title": title}).json()["title"] == title


def test_edit_rejects_invalid_title_and_keeps_the_old_one(alice):
    task = alice.create_task("original")
    assert alice.patch(f"/api/tasks/{task['id']}", json={"title": ""}).status_code == 400
    assert alice.get(f"/api/tasks/{task['id']}").json()["title"] == "original"


@pytest.mark.parametrize("done", ["true", 1, None], ids=["string", "number", "null"])
def test_edit_rejects_non_boolean_done(alice, done):
    task = alice.create_task()
    assert alice.patch(f"/api/tasks/{task['id']}", json={"done": done}).status_code == 400


def test_create_rejects_non_json_body(alice):
    assert alice.post("/api/tasks", data={"title": "x"}).status_code == 415


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_unknown_task_returns_404(alice, method):
    kwargs = {"json": {"title": "x"}} if method == "patch" else {}
    assert getattr(alice, method)("/api/tasks/999999", **kwargs).status_code == 404
