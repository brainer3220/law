import sqlite3
import json
from typing import Any, Dict, Optional
from contextlib import contextmanager
import os

DB_PATH = os.getenv("TRANSCRIBE_DB_PATH", "./transcribe_jobs.db")

def init_db():
    """Initialize the database and create tables if they don't exist."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def create_job(job_id: str, email: str) -> None:
    """Create a new job with PENDING status."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO jobs (job_id, email, status) VALUES (?, ?, ?)",
            (job_id, email, "PENDING")
        )
        conn.commit()

def update_job_status(job_id: str, status: str) -> None:
    """Update job status."""
    with get_db() as conn:
        conn.execute(
            "UPDATE jobs SET status = ? WHERE job_id = ?",
            (status, job_id)
        )
        conn.commit()

def update_job_result(job_id: str, result: Dict[str, Any]) -> None:
    """Update job with success result."""
    with get_db() as conn:
        conn.execute(
            "UPDATE jobs SET status = ?, result = ? WHERE job_id = ?",
            ("SUCCESS", json.dumps(result), job_id)
        )
        conn.commit()

def update_job_error(job_id: str, error: str) -> None:
    """Update job with error."""
    with get_db() as conn:
        conn.execute(
            "UPDATE jobs SET status = ?, error = ? WHERE job_id = ?",
            ("FAILURE", error, job_id)
        )
        conn.commit()

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (job_id,)
        ).fetchone()
        
        if not row:
            return None
        
        job = {
            "job_id": row["job_id"],
            "email": row["email"],
            "status": row["status"],
        }
        
        if row["result"]:
            job["result"] = json.loads(row["result"])
        
        if row["error"]:
            job["error"] = row["error"]
        
        return job

# Initialize database on module import
init_db()
