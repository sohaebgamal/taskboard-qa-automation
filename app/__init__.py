"""TaskBoard: a small demo app that exists only to be tested. Never deploy it."""
import os
import secrets
import sqlite3
import time
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

MAX_TITLE_LENGTH = 120
MAX_FAILED_LOGINS = 5
LOCK_SECONDS = 300

# Fake demo accounts, seeded fresh on every reset.
DEMO_USERS = (
    ("alice", "alice-demo-pass", "user"),
    ("bob", "bob-demo-pass", "user"),
    ("admin", "admin-demo-pass", "admin"),
)

# Bugs that can be switched on to prove the test suite catches them.
# See scripts/fault_check.py. They are off unless TASKBOARD_FAULTS names them.
KNOWN_FAULTS = {
    "idor",
    "admin_open",
    "no_lockout",
    "user_enum",
    "xss",
    "no_title_validation",
    "done_not_saved",
    "no_security_headers",
}

SCHEMA = """
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS login_failures;
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL
);
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE login_failures (
    username TEXT PRIMARY KEY,
    count INTEGER NOT NULL,
    locked_until REAL NOT NULL DEFAULT 0
);
"""


def create_app(db_path, faults=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("TASKBOARD_SECRET") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if faults is None:
        faults = {f for f in os.environ.get("TASKBOARD_FAULTS", "").split(",") if f}
    unknown = set(faults) - KNOWN_FAULTS
    if unknown:
        raise ValueError(f"unknown faults: {sorted(unknown)}")

    db_path = str(Path(db_path))
    password_hashes = [
        (name, generate_password_hash(password), role) for name, password, role in DEMO_USERS
    ]

    def reset_data():
        with sqlite3.connect(db_path) as conn:
            conn.executescript(SCHEMA)
            conn.executemany(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                password_hashes,
            )

    app.reset_data = reset_data
    reset_data()

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(db_path)
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    @app.after_request
    def security_headers(response):
        if "no_security_headers" not in faults:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

    def current_user():
        user_id = session.get("user_id")
        if user_id is None:
            return None
        return db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    def login_required(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None:
                return jsonify(error="authentication required"), 401
            g.user = user
            return view(*args, **kwargs)

        return wrapper

    def json_body():
        """Return the JSON object in the request, or None if there isn't one."""
        if not request.is_json:
            return None
        body = request.get_json(silent=True)
        return body if isinstance(body, dict) else None

    def task_json(task):
        return {"id": task["id"], "title": task["title"], "done": bool(task["done"])}

    def validate_title(title):
        if not isinstance(title, str):
            return "title must be a string"
        if "no_title_validation" in faults:
            return None
        if not title.strip():
            return "title must not be blank"
        if len(title) > MAX_TITLE_LENGTH:
            return f"title must be at most {MAX_TITLE_LENGTH} characters"
        return None

    def visible_task(task_id):
        """Return the task only if the current user may see it."""
        if "idor" in faults:
            return db().execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return (
            db()
            .execute("SELECT * FROM tasks WHERE id = ? AND owner_id = ?", (task_id, g.user["id"]))
            .fetchone()
        )

    def is_locked(username):
        if "no_lockout" in faults:
            return False
        row = db().execute(
            "SELECT locked_until FROM login_failures WHERE username = ?", (username,)
        ).fetchone()
        return row is not None and row["locked_until"] > time.time()

    def record_failure(username):
        conn = db()
        row = conn.execute(
            "SELECT count FROM login_failures WHERE username = ?", (username,)
        ).fetchone()
        count = (row["count"] if row else 0) + 1
        locked_until = time.time() + LOCK_SECONDS if count >= MAX_FAILED_LOGINS else 0
        conn.execute(
            "INSERT OR REPLACE INTO login_failures (username, count, locked_until) VALUES (?, ?, ?)",
            (username, count, locked_until),
        )
        conn.commit()

    # ---------- pages ----------

    @app.get("/")
    def board_page():
        if current_user() is None:
            return redirect("/login")
        return render_template("board.html", unsafe_render="xss" in faults)

    @app.get("/login")
    def login_page():
        return render_template("login.html")

    # ---------- API ----------

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.post("/api/login")
    def login():
        if not request.is_json:
            return jsonify(error="JSON body required"), 415
        body = json_body() or {}
        username, password = body.get("username"), body.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            return jsonify(error="username and password are required"), 400

        if is_locked(username):
            return jsonify(error="too many failed attempts, try again later"), 429

        user = db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user is None and "user_enum" in faults:
            return jsonify(error="user does not exist"), 404
        if user is None or not check_password_hash(user["password_hash"], password):
            record_failure(username)
            return jsonify(error="invalid username or password"), 401

        db().execute("DELETE FROM login_failures WHERE username = ?", (username,))
        db().commit()
        session.clear()
        session["user_id"] = user["id"]
        return jsonify(username=user["username"], role=user["role"])

    @app.post("/api/logout")
    def logout():
        session.clear()
        return "", 204

    @app.get("/api/me")
    @login_required
    def me():
        return jsonify(username=g.user["username"], role=g.user["role"])

    @app.get("/api/tasks")
    @login_required
    def list_tasks():
        rows = db().execute(
            "SELECT * FROM tasks WHERE owner_id = ? ORDER BY id", (g.user["id"],)
        ).fetchall()
        return jsonify(tasks=[task_json(row) for row in rows])

    @app.post("/api/tasks")
    @login_required
    def create_task():
        if not request.is_json:
            return jsonify(error="JSON body required"), 415
        body = json_body() or {}
        error = validate_title(body.get("title"))
        if error:
            return jsonify(error=error), 400
        conn = db()
        cursor = conn.execute(
            "INSERT INTO tasks (owner_id, title) VALUES (?, ?)", (g.user["id"], body["title"])
        )
        conn.commit()
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(task_json(task)), 201

    @app.get("/api/tasks/<int:task_id>")
    @login_required
    def get_task(task_id):
        task = visible_task(task_id)
        if task is None:
            return jsonify(error="task not found"), 404
        return jsonify(task_json(task))

    @app.patch("/api/tasks/<int:task_id>")
    @login_required
    def update_task(task_id):
        if not request.is_json:
            return jsonify(error="JSON body required"), 415
        task = visible_task(task_id)
        if task is None:
            return jsonify(error="task not found"), 404
        body = json_body() or {}
        title, done = task["title"], task["done"]
        if "title" in body:
            error = validate_title(body["title"])
            if error:
                return jsonify(error=error), 400
            title = body["title"]
        if "done" in body:
            if not isinstance(body["done"], bool):
                return jsonify(error="done must be true or false"), 400
            if "done_not_saved" not in faults:
                done = int(body["done"])
        conn = db()
        conn.execute("UPDATE tasks SET title = ?, done = ? WHERE id = ?", (title, done, task_id))
        conn.commit()
        return jsonify(task_json(conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()))

    @app.delete("/api/tasks/<int:task_id>")
    @login_required
    def delete_task(task_id):
        if visible_task(task_id) is None:
            return jsonify(error="task not found"), 404
        conn = db()
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        return "", 204

    @app.get("/api/admin/users")
    @login_required
    def admin_users():
        if g.user["role"] != "admin" and "admin_open" not in faults:
            return jsonify(error="admin role required"), 403
        rows = db().execute("SELECT username, role FROM users ORDER BY id").fetchall()
        return jsonify(users=[dict(row) for row in rows])

    return app
