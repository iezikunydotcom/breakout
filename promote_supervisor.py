"""Promote an existing player to supervisor.

Usage:  python promote_supervisor.py player@example.com
"""

import sqlite3
import sys
from pathlib import Path

db_path = Path(__file__).resolve().parent / "breakout.db"
if not db_path.exists():
    print("No breakout.db found - start the app once first.")
    sys.exit(1)

email = sys.argv[1].strip().lower() if len(sys.argv) > 1 else ""
if not email:
    print("Usage: python promote_supervisor.py player@example.com")
    sys.exit(1)

db = sqlite3.connect(db_path)
cur = db.execute("UPDATE users SET role = 'supervisor' WHERE email = ?", (email,))
db.commit()
db.close()

if cur.rowcount:
    print(f"Promoted {email} to supervisor.")
else:
    print(f"No account found with email {email}.")
