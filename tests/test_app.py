"""End-to-end tests for the Breakout web app (no pytest needed).

Run with:   python tests/test_app.py
Uses a temporary SQLite database so your real data is untouched.
"""

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

TEST_DB = Path(tempfile.gettempdir()) / "breakout_test_users.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["BREAKOUT_DB_PATH"] = str(TEST_DB)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app as game  # noqa: E402


def check(name, condition):
    assert condition, f"FAILED: {name}"
    print(f"OK: {name}")


c = game.app.test_client()

r = c.get("/")
check("game page redirects to login when logged out", r.status_code == 302 and "/login" in r.headers["Location"])

r = c.post("/register", data={"username": "ab", "password": "secret1", "confirm": "secret1"}, follow_redirects=True)
check("short username rejected", "3-20" in r.get_data(as_text=True))

r = c.post("/register", data={"username": "testplayer", "password": "secret1", "confirm": "secret1"}, follow_redirects=True)
check("registration succeeds", "log in now" in r.get_data(as_text=True))

r = c.post("/login", data={"username": "testplayer", "password": "wrong"}, follow_redirects=True)
check("wrong password rejected", "Invalid username or password" in r.get_data(as_text=True))

r = c.post("/login", data={"username": "testplayer", "password": "secret1"}, follow_redirects=True)
html = r.get_data(as_text=True)
check("game page shows username and game", "testplayer" in html and "Start Game" in html and "Breakout" in html)

r = game.app.test_client().post("/api/score", json={"score": 10})
check("score API blocked when logged out", r.status_code == 401)

r = c.post("/api/score", json={"score": 55})
check("score 55 saved", r.get_json() == {"best": 55})
r = c.post("/api/score", json={"score": 20})
check("lower score ignored", r.get_json() == {"best": 55})
r = c.post("/api/score", json={"score": 70})
check("higher score replaces best", r.get_json() == {"best": 70})

r = c.get("/")
check("best score rendered", 'id="best">70</strong>' in r.get_data(as_text=True))

r = game.app.test_client().post(
    "/register", data={"username": "testplayer", "password": "secret1", "confirm": "secret1"}, follow_redirects=True
)
check("duplicate username rejected", "already taken" in r.get_data(as_text=True))

r = c.post("/logout", follow_redirects=True)
check("logout shows login page", "Log in to play" in r.get_data(as_text=True))
check("game page blocked after logout", c.get("/").status_code == 302)

db = sqlite3.connect(TEST_DB)
row = db.execute("SELECT password_hash FROM users WHERE username = ?", ("testplayer",)).fetchone()
db.close()
check("password stored hashed", row is not None and "secret1" not in row[0] and row[0].startswith("scrypt:"))

TEST_DB.unlink(missing_ok=True)
print("\nALL BREAKOUT WEB APP TESTS PASSED")
