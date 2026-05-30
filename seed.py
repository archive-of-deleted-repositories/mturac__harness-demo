"""Create a throwaway SQLite DB with sample users for the demo."""

from __future__ import annotations

import os
import sqlite3


def seed(db_path: str = "demo.db", n_active: int = 200, n_inactive: int = 12) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)  # fresh DB each run (no destructive SQL needed)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""CREATE TABLE users (
        id INTEGER PRIMARY KEY, handle TEXT, tier TEXT,
        archived INTEGER DEFAULT 0, last_login TEXT)""")
    rows = []
    for i in range(n_active):
        rows.append((f"user{i}", "free", 0, "2026-05-01"))
    for i in range(n_inactive):
        rows.append((f"old{i}", "free", 0, "2024-03-01"))
    c.executemany("INSERT INTO users (handle, tier, archived, last_login) VALUES (?,?,?,?)", rows)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed()
    print("seeded demo.db")
