import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "database" / "vendorflow.db"
UPLOAD_DIR = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS vendors (
            vendor_id TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            contact_name TEXT,
            email TEXT,
            pan TEXT,
            gstin TEXT,
            bank_account TEXT,
            ifsc TEXT,
            country TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS processing_runs (
            run_id TEXT PRIMARY KEY,
            vendor_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Submitted',
            started_at TEXT NOT NULL,
            completed_at TEXT,
            llm_provider TEXT,
            decision_reason TEXT,
            FOREIGN KEY(vendor_id) REFERENCES vendors(vendor_id)
        );

        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES processing_runs(run_id)
        );

        CREATE TABLE IF NOT EXISTS validation_results (
            validation_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            check_name TEXT NOT NULL,
            result TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES processing_runs(run_id)
        );

        CREATE TABLE IF NOT EXISTS execution_events (
            event_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES processing_runs(run_id)
        );
        """)

def create_vendor_submission(data, uploaded_files):
    now = datetime.now(timezone.utc).isoformat()
    vendor_id = "V-" + uuid.uuid4().hex[:10].upper()
    run_id = "RUN-" + uuid.uuid4().hex[:10].upper()
    vendor_dir = UPLOAD_DIR / run_id
    vendor_dir.mkdir(parents=True, exist_ok=True)

    saved_docs = []
    for uploaded in uploaded_files:
        suffix = Path(uploaded.name).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {suffix}")
        document_id = "DOC-" + uuid.uuid4().hex[:10].upper()
        safe_name = Path(uploaded.name).name.replace(" ", "_")
        destination = vendor_dir / f"{document_id}_{safe_name}"
        destination.write_bytes(uploaded.getvalue())
        saved_docs.append((document_id, uploaded.name, str(destination), suffix))

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO vendors (
                vendor_id, company_name, contact_name, email, pan, gstin,
                bank_account, ifsc, country, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vendor_id, data["company_name"], data["contact_name"], data["email"],
            data["pan"], data["gstin"], data["bank_account"], data["ifsc"],
            data["country"], now
        ))
        conn.execute("""
            INSERT INTO processing_runs (run_id, vendor_id, status, started_at)
            VALUES (?, ?, 'Submitted', ?)
        """, (run_id, vendor_id, now))
        for document_id, filename, path, suffix in saved_docs:
            conn.execute("""
                INSERT INTO documents (
                    document_id, run_id, original_filename, stored_path, file_type, uploaded_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (document_id, run_id, filename, path, suffix, now))
        conn.execute("""
            INSERT INTO execution_events (event_id, run_id, stage, status, details, created_at)
            VALUES (?, ?, 'Submission received', 'Completed', ?, ?)
        """, ("EVT-" + uuid.uuid4().hex[:10].upper(), run_id,
              f"Vendor intake saved; {len(saved_docs)} document(s) attached.", now))
    return run_id

def get_recent_runs(limit=100):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT r.run_id, v.vendor_id, v.company_name, r.status,
                   r.started_at, r.completed_at, r.llm_provider, r.decision_reason,
                   (SELECT COUNT(*) FROM documents d WHERE d.run_id = r.run_id) AS document_count
            FROM processing_runs r
            JOIN vendors v ON v.vendor_id = r.vendor_id
            ORDER BY r.started_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(row) for row in rows]


import uuid


def get_run_context(run_id):
    with get_connection() as conn:
        run = conn.execute("""
            SELECT r.run_id, r.vendor_id, v.company_name,
                   v.contact_name, v.email, v.pan, v.gstin,
                   v.bank_account, v.ifsc, v.country
            FROM processing_runs r
            JOIN vendors v ON v.vendor_id = r.vendor_id
            WHERE r.run_id = ?
        """, (run_id,)).fetchone()

        documents = conn.execute("""
            SELECT original_filename, stored_path, file_type
            FROM documents
            WHERE run_id = ?
        """, (run_id,)).fetchall()

    if not run:
        raise ValueError("Processing run not found")

    return dict(run), [dict(doc) for doc in documents]


def add_execution_event(run_id, stage, status, details):
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO execution_events
            (event_id, run_id, stage, status, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "EVT-" + uuid.uuid4().hex[:10].upper(),
            run_id, stage, status, details, now
        ))


def save_validation_results(run_id, results):
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        for result in results:
            conn.execute("""
                INSERT INTO validation_results
                (validation_id, run_id, check_name, result, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                "VAL-" + uuid.uuid4().hex[:10].upper(),
                run_id,
                result["check_name"],
                result["result"],
                result["details"],
                now
            ))


def update_run(run_id, status, reason, provider=None):
    completed = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute("""
            UPDATE processing_runs
            SET status = ?,
                decision_reason = ?,
                llm_provider = ?,
                completed_at = ?
            WHERE run_id = ?
        """, (status, reason, provider, completed, run_id))


def get_run_events(run_id):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT stage, status, details, created_at
            FROM execution_events
            WHERE run_id = ?
            ORDER BY created_at
        """, (run_id,)).fetchall()

    return [dict(row) for row in rows]


def get_run_validations(run_id):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT check_name, result, details, created_at
            FROM validation_results
            WHERE run_id = ?
            ORDER BY created_at
        """, (run_id,)).fetchall()

    return [dict(row) for row in rows]

