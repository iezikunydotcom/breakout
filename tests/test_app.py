"""End-to-end tests for the Rainbow Blocks web app (no pytest needed).

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
# The very first registration below uses this email -> becomes supervisor.
os.environ["SUPERVISOR_EMAIL"] = "boss@example.com"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app as game  # noqa: E402

conn = sqlite3.connect(TEST_DB)


def check(name, condition):
    assert condition, f"FAILED: {name}"
    print(f"OK: {name}")


c = game.app.test_client()

# 1. Game requires login.
r = c.get("/")
check("game page redirects to login when logged out", r.status_code == 302 and "/login" in r.headers["Location"])

# 2. Registration validation: bad email.
r = c.post(
    "/register",
    data={"name": "Alice", "email": "not-an-email", "password": "secret1", "confirm": "secret1"},
    follow_redirects=True,
)
check("invalid email rejected", "valid email" in r.get_data(as_text=True))

# 3. Register a normal player.
r = c.post(
    "/register",
    data={"name": "Alice", "email": "alice@example.com", "password": "secret1", "confirm": "secret1"},
    follow_redirects=True,
)
check("player registration succeeds", "log in now" in r.get_data(as_text=True))

# 4. Wrong password rejected.
r = c.post("/login", data={"email": "alice@example.com", "password": "wrong"}, follow_redirects=True)
check("wrong password rejected", "Invalid email or password" in r.get_data(as_text=True))

# 5. Alice logs in and sees the game.
r = c.post("/login", data={"email": "alice@example.com", "password": "secret1"}, follow_redirects=True)
html = r.get_data(as_text=True)
check("game page shows player and controls", "Alice" in html and "Start Game" in html)
check("player has no manage link", "Manage Players" not in html)

# 6. Score API: requires login and keeps the highest score.
r = game.app.test_client().post("/api/score", json={"score": 10})
check("score API blocked when logged out", r.status_code == 401)
check("score 55 saved", c.post("/api/score", json={"score": 55}).get_json() == {"best": 55})
check("lower score ignored", c.post("/api/score", json={"score": 20}).get_json() == {"best": 55})

# 7. Leaderboard is login-protected and shows Alice.
check("leaderboard redirects when logged out", game.app.test_client().get("/leaderboard").status_code == 302)
lb = c.get("/leaderboard").get_data(as_text=True)
check("leaderboard shows player", "Alice" in lb and "55" in lb)

# 8. A normal player cannot open the manage page.
r = c.get("/manage", follow_redirects=True)
check("player blocked from manage page", "supervisor access" in r.get_data(as_text=True))

# 9. Register with the SUPERVISOR_EMAIL -> becomes supervisor.
c2 = game.app.test_client()
c2.post(
    "/register",
    data={"name": "Boss", "email": "boss@example.com", "password": "secret1", "confirm": "secret1"},
)
c2.post("/login", data={"email": "boss@example.com", "password": "secret1"})
html2 = c2.get("/").get_data(as_text=True)
check("supervisor sees manage link", "Manage Players" in html2 and "Supervisor" in html2)

# 10. Supervisor can view manage page and manage Alice.
r = c2.get("/manage")
check("supervisor opens manage page", r.status_code == 200 and "alice@example.com" in r.get_data(as_text=True))

alice_id = conn.execute("SELECT id FROM users WHERE email = 'alice@example.com'").fetchone()[0]
r = c2.post(f"/manage/{alice_id}/reset", follow_redirects=True)
check("supervisor resets score", "Score reset" in r.get_data(as_text=True))
check("score really reset", conn.execute("SELECT best_score FROM users WHERE id = ?", (alice_id,)).fetchone()[0] == 0)

# 11. Supervisor can change a role and delete an account (not their own).
r = c2.post(f"/manage/{alice_id}/role", follow_redirects=True)
check("role toggle works", "Role updated" in r.get_data(as_text=True))
r = c2.post(f"/manage/{alice_id}/delete", follow_redirects=True)
check("account removed", "Account removed" in r.get_data(as_text=True))
check(
    "user really deleted",
    conn.execute("SELECT COUNT(*) FROM users WHERE id = ?", (alice_id,)).fetchone()[0] == 0,
)

# 12. Supervisor cannot delete or demote themselves.
boss_id = conn.execute("SELECT id FROM users WHERE email = 'boss@example.com'").fetchone()[0]
check(
    "cannot delete self",
    "cannot delete your own" in c2.post(f"/manage/{boss_id}/delete", follow_redirects=True).get_data(as_text=True),
)
check(
    "cannot change own role",
    "cannot change your own role" in c2.post(f"/manage/{boss_id}/role", follow_redirects=True).get_data(as_text=True),
)

# 13. Logout works and passwords are hashed.
r = c2.post("/logout", follow_redirects=True)
check("logout shows login page", "Log in with your email" in r.get_data(as_text=True))
row = conn.execute("SELECT password_hash FROM users WHERE email = 'boss@example.com'").fetchone()
check("password stored hashed", "secret1" not in row[0] and row[0].startswith("scrypt:"))

conn.close()
TEST_DB.unlink(missing_ok=True)
print("\nALL RAINBOW BLOCKS WEB APP TESTS PASSED")
