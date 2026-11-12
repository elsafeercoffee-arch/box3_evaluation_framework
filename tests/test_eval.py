import pytest
import sqlite3
from pathlib import Path

def test_database_connection():
    db_path = Path("data/eval_database.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eval_runs (
            id TEXT PRIMARY KEY,
            model_name TEXT,
            score REAL
        )
    """)
    conn.commit()
    conn.close()
    assert True
