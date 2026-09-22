"""
Initialize the SQLite database for Hobby Server Monitor.
Run: python3 init_db.py
Safe to re-run - uses CREATE TABLE IF NOT EXISTS.
"""
import sqlite3
import os

DB_PATH = os.environ.get("SQLITE_DB_PATH", "./data/app.db")

SCHEMA = """
-- Users who have signed in via Google OAuth
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    google_sub TEXT UNIQUE,              -- Google's stable user id (set on first login)
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    role TEXT NOT NULL CHECK(role IN ('admin', 'user')) DEFAULT 'user',
    status TEXT NOT NULL CHECK(status IN ('invited', 'active', 'revoked')) DEFAULT 'invited',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_login_at TEXT
);

-- Server-side sessions (cookie stores only the session id)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,                 -- random token
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL
);

-- Per-user resource quota (max the user's containers may collectively consume)
CREATE TABLE IF NOT EXISTS quotas (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    max_ram_mb INTEGER NOT NULL DEFAULT 1024,
    max_cpu_cores INTEGER NOT NULL DEFAULT 1,
    max_disk_gb INTEGER NOT NULL DEFAULT 10
);

-- Local cache/registry of containers this app knows about
-- (source of truth for resource usage is LXD; this table maps LXD names to app metadata)
CREATE TABLE IF NOT EXISTS containers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lxd_name TEXT UNIQUE NOT NULL,       -- name in LXD at creation time
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT                      -- soft delete marker; keeps history/metrics valid
);

-- Which users can access which containers
CREATE TABLE IF NOT EXISTS assignments (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    container_id INTEGER NOT NULL REFERENCES containers(id) ON DELETE CASCADE,
    assigned_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, container_id)
);

-- Audit trail for destructive / limit-changing actions
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,                -- e.g. 'container.delete', 'container.limits.update'
    target TEXT,                         -- e.g. container lxd_name
    details TEXT,                        -- JSON blob with before/after values
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_assignments_user ON assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_assignments_container ON assignments(container_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor_user_id);
"""

def main():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    main()