import sqlite3
from src.regression import compare_and_check_regression


def test_eval_db_schema_and_regression_pass(tmp_path):
    db = str(tmp_path / "test_eval.db")
    res = compare_and_check_regression(db_path=db, write_report=False)
    assert res["passed"] is True
    assert res["baseline"]["total_cases"] == 72
    assert res["candidate"]["total_cases"] == 72
    conn = sqlite3.connect(db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(eval_runs)").fetchall()}
    conn.close()
    assert {"id", "model_name", "prompt_version", "q_id", "answer", "latency_ms", "score_correctness", "score_groundedness", "agreement_score", "ts"}.issubset(cols)


def test_regression_fails_on_degraded_candidate(tmp_path):
    db = str(tmp_path / "test_fail.db")
    res = compare_and_check_regression(
        candidate_model="degraded-v0",
        candidate_prompt="degraded_v0",
        max_drop_pct=3.0,
        db_path=db,
        write_report=False,
    )
    assert res["passed"] is False
    assert res["drop_pct"] > 3.0
