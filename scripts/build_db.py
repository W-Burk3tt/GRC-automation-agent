import sqlite3
import json
import os

DB_PATH = "data/grc.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS controls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    framework TEXT NOT NULL,
    control_id TEXT NOT NULL,
    title TEXT,
    text TEXT NOT NULL,
    source_page INTEGER,
    UNIQUE(framework, control_id)
);

CREATE TABLE IF NOT EXISTS crosswalk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cmmc_control_id TEXT NOT NULL,
    pcidss_control_id TEXT NOT NULL,
    mapping_rationale TEXT,
    confidence TEXT,
    requires_human_review INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS poam (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    control_id TEXT NOT NULL,
    gap_description TEXT,
    remediation_plan TEXT,
    owner TEXT,
    due_date TEXT,
    status TEXT DEFAULT 'open',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,
    source_control_id TEXT,
    details TEXT
);
"""

def build_schema(conn):
    conn.executescript(SCHEMA)
    conn.commit()

def load_cmmc(conn, path="data/cmmc_controls_raw.json"):
    with open(path) as f:
        controls = json.load(f)
    rows = [
        ("CMMC", c["control_id"], c["title"], c["text"], c.get("start_page"))
        for c in controls
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO controls (framework, control_id, title, text, source_page) VALUES (?, ?, ?, ?, ?)",
        rows
    )
    conn.commit()
    print(f"Loaded {len(rows)} CMMC controls")

def load_pcidss(conn, path="data/pcidss_requirements_raw.json"):
    with open(path) as f:
        requirements = json.load(f)
    rows = [
        ("PCI-DSS", r["requirement_id"], None, r["text"], r.get("page"))
        for r in requirements
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO controls (framework, control_id, title, text, source_page) VALUES (?, ?, ?, ?, ?)",
        rows
    )
    conn.commit()
    print(f"Loaded {len(rows)} PCI-DSS requirements")

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    build_schema(conn)
    load_cmmc(conn)
    load_pcidss(conn)

    # Quick sanity check
    cur = conn.execute("SELECT framework, COUNT(*) FROM controls GROUP BY framework")
    print("\nControl counts by framework:")
    for framework, count in cur.fetchall():
        print(f"  {framework}: {count}")

    conn.close()
    print(f"\nDatabase saved to {DB_PATH}")
