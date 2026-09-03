"""Rainbow Blocks web app with email accounts and supervisor management.

Run with:   python app.py
Then open:  http://127.0.0.1:5000

Roles:
- player     - registers with email, plays, and saves a best score
- supervisor - sees every player and can reset scores or remove accounts

To make a specific email register as a supervisor, set the environment
variable SUPERVISOR_EMAIL before the account is created, or run
python promote_supervisor.py email@example.com afterwards.
"""

import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("BREAKOUT_DB_PATH", BASE_DIR / "breakout.db"))

app = Flask(__name__)


def load_secret_key():
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    key_file = BASE_DIR / ".secret_key"
    if key_file.exists():
        return key_file.read_text().strip()
    key = secrets.token_hex(32)
    try:
        key_file.write_text(key)
    except OSError:
        pass
    return key


app.secret_key = load_secret_key()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            best_score INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            email TEXT,
            role TEXT NOT NULL DEFAULT 'player'
        );
        """
    )
    # Migrate databases created before email/role existed.
    columns = [row[1] for row in db.execute("PRAGMA table_info(users)")]
    if "email" not in columns:
        db.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if "role" not in columns:
        db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'player'")
    db.execute("UPDATE users SET email = username || '@players.local' WHERE email IS NULL OR email = ''")
    try:
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    except sqlite3.IntegrityError:
        pass
    db.commit()
    db.close()


def get_user_by_email(email):
    return get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def get_user_by_id(user_id):
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return get_user_by_id(user_id)


def is_supervisor(user):
    return user is not None and user["role"] == "supervisor"


def supervisor_guard():
    """Return (user, None) for supervisors, else (None, redirect)."""
    user = current_user()
    if user is None:
        return None, redirect(url_for("login"))
    if not is_supervisor(user):
        flash("You need supervisor access for that.", "error")
        return None, redirect(url_for("index"))
    return user, None


@app.route("/")
def index():
    user = current_user()
    if user is None:
        return redirect(url_for("login"))
    return render_template("game.html", user=user)


@app.route("/leaderboard")
def leaderboard():
    user = current_user()
    if user is None:
        return redirect(url_for("login"))
    db = get_db()
    top = db.execute(
        "SELECT username, email, best_score FROM users WHERE role = 'player' "
        "ORDER BY best_score DESC, id ASC LIMIT 10"
    ).fetchall()
    better = db.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'player' AND best_score > ?",
        (user["best_score"],),
    ).fetchone()[0]
    my_rank = better + 1
    return render_template("leaderboard.html", user=user, top=top, my_rank=my_rank)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user() is not None:
        return redirect(url_for("index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        error = None

        if not (1 <= len(name) <= 30):
            error = "Please enter a name (up to 30 characters)."
        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            error = "Please enter a valid email address."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif get_user_by_email(email) is not None:
            error = "An account with that email already exists."
        else:
            role = (
                "supervisor"
                if email == os.environ.get("SUPERVISOR_EMAIL", "").strip().lower()
                else "player"
            )
            db = get_db()
            db.execute(
                "INSERT INTO users (username, email, password_hash, best_score, role, created_at) "
                "VALUES (?, ?, ?, 0, ?, ?)",
                (
                    name,
                    email,
                    generate_password_hash(password),
                    role,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            db.commit()
            flash("Account created - you can log in now.", "success")
            return redirect(url_for("login"))
        flash(error, "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user() is not None:
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/manage")
def manage():
    user, redirect_to = supervisor_guard()
    if redirect_to is not None:
        return redirect_to
    users = get_db().execute(
        "SELECT id, username, email, best_score, role, created_at FROM users "
        "ORDER BY (role = 'supervisor') DESC, best_score DESC"
    ).fetchall()
    return render_template("manage.html", user=user, users=users)


@app.route("/manage/<int:user_id>/reset", methods=["POST"])
def reset_score(user_id):
    _, redirect_to = supervisor_guard()
    if redirect_to is not None:
        return redirect_to
    db = get_db()
    db.execute("UPDATE users SET best_score = 0 WHERE id = ?", (user_id,))
    db.commit()
    flash("Score reset.", "success")
    return redirect(url_for("manage"))


@app.route("/manage/<int:user_id>/role", methods=["POST"])
def toggle_role(user_id):
    user, redirect_to = supervisor_guard()
    if redirect_to is not None:
        return redirect_to
    if user_id == user["id"]:
        flash("You cannot change your own role.", "error")
        return redirect(url_for("manage"))
    db = get_db()
    target = db.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
    if target is not None:
        new_role = "player" if target["role"] == "supervisor" else "supervisor"
        db.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        db.commit()
        flash("Role updated.", "success")
    return redirect(url_for("manage"))


@app.route("/manage/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    user, redirect_to = supervisor_guard()
    if redirect_to is not None:
        return redirect_to
    if user_id == user["id"]:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("manage"))
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    flash("Account removed.", "success")
    return redirect(url_for("manage"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/api/score", methods=["POST"])
def save_score():
    user = current_user()
    if user is None:
        return jsonify({"error": "not logged in"}), 401
    data = request.get_json(silent=True) or {}
    try:
        score = int(data.get("score", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid score"}), 400
    score = max(0, min(score, 100000))

    db = get_db()
    if score > user["best_score"]:
        db.execute("UPDATE users SET best_score = ? WHERE id = ?", (score, user["id"]))
        db.commit()
        best = score
    else:
        best = user["best_score"]
    return jsonify({"best": best})


init_db()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
