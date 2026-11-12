import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_db_path(db_path: Optional[str] = None) -> Path:
    path = Path(db_path or os.getenv("EVAL_DB_PATH", "data/eval.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path(db_path)))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS eval_runs (
                id TEXT PRIMARY KEY,
                model_name TEXT NOT NULL,
                prompt_version TEXT NOT NULL,
                q_id TEXT NOT NULL,
                answer TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                score_correctness INT NOT NULL,
                score_groundedness INT NOT NULL,
                score_language INT NOT NULL DEFAULT 2,
                agreement_score REAL,
                ts DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_eval_mp ON eval_runs(model_name, prompt_version)")
        conn.commit()


def clear_run(model_name: str, prompt_version: str, db_path: Optional[str] = None) -> None:
    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM eval_runs WHERE model_name=? AND prompt_version=?", (model_name, prompt_version))
        conn.commit()


def insert_eval_run(rec: Dict[str, Any], db_path: Optional[str] = None) -> None:
    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO eval_runs
            (id, model_name, prompt_version, q_id, answer, latency_ms,
             score_correctness, score_groundedness, score_language, agreement_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rec["id"], rec["model_name"], rec["prompt_version"], rec["q_id"],
             rec["answer"], float(rec["latency_ms"]), int(rec["score_correctness"]),
             int(rec["score_groundedness"]), int(rec.get("score_language", 2)),
             rec.get("agreement_score")),
        )
        conn.commit()


def get_run_summary(model_name: str, prompt_version: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS n, AVG(score_correctness) AS c,
               AVG(score_groundedness) AS g, AVG(score_language) AS l,
               AVG(latency_ms) AS lat, AVG(agreement_score) AS agr
               FROM eval_runs WHERE model_name=? AND prompt_version=?""",
            (model_name, prompt_version),
        ).fetchone()
    n = int(row["n"] or 0)
    c, g, l = float(row["c"] or 0.0), float(row["g"] or 0.0), float(row["l"] or 0.0)
    pct = ((c + g) / 4.0) * 100.0 if n > 0 else 0.0
    return {
        "model_name": model_name, "prompt_version": prompt_version, "total_cases": n,
        "avg_correctness": round(c, 4), "avg_groundedness": round(g, 4),
        "avg_language": round(l, 4), "overall_score_pct": round(pct, 2),
        "avg_latency_ms": round(float(row["lat"] or 0.0), 2),
        "avg_agreement": round(float(row["agr"]), 4) if row["agr"] is not None else None,
    }


def list_runs(limit: int = 20, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT model_name, prompt_version, COUNT(*) AS cases,
               ROUND(AVG(score_correctness), 3) AS avg_correctness,
               ROUND(AVG(score_groundedness), 3) AS avg_groundedness,
               ROUND(AVG(latency_ms), 2) AS avg_latency_ms,
               MAX(ts) AS last_ts
               FROM eval_runs GROUP BY model_name, prompt_version
               ORDER BY last_ts DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
