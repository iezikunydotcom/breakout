"""Breakout web app with user accounts stored in SQLite.

Run with:   python app.py
Then open:  http://127.0.0.1:5000
"""

import os
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
            created_at TEXT NOT NULL
        );
        """
    )
    db.commit()
    db.close()


def get_user_by_username(username):
    return get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def get_user_by_id(user_id):
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return get_user_by_id(user_id)


@app.route("/")
def index():
    user = current_user()
    if user is None:
        return redirect(url_for("login"))
    return render_template("game.html", user=user)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user() is not None:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        error = None

        if not (3 <= len(username) <= 20) or not username.isalnum():
            error = "Username must be 3-20 characters, letters and numbers only."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif get_user_by_username(username) is not None:
            error = "That username is already taken."
        else:
            db = get_db()
            db.execute(
                "INSERT INTO users (username, password_hash, best_score, created_at) "
                "VALUES (?, ?, 0, ?)",
                (username, generate_password_hash(password), datetime.now(timezone.utc).isoformat()),
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
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_user_by_username(username)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("index"))
    return render_template("login.html")


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
