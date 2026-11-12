import json
import time
from typing import Any, Dict, List, Optional
from src.db import clear_run, get_run_summary, insert_eval_run
from src.human_align import compute_human_alignment
from src.judge import judge_response
from src.target_rag import run_rag_query


def load_golden(path: str = "data/golden_eval.jsonl") -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def evaluate_config(
    model_name: str,
    prompt_version: str,
    golden_path: str = "data/golden_eval.jsonl",
    db_path: Optional[str] = None,
    judge_provider: str = "mock",
) -> Dict[str, Any]:
    cases = load_golden(golden_path)
    clear_run(model_name, prompt_version, db_path=db_path)
    align = compute_human_alignment(golden_path=golden_path, provider=judge_provider)
    agr = align["exact_correctness_pct"] / 100.0

    for case in cases:
        t0 = time.perf_counter()
        out = run_rag_query(case["question"], prompt_version=prompt_version)
        lat_ms = (time.perf_counter() - t0) * 1000.0
        scores = judge_response(case, out["answer"], provider=judge_provider)
        insert_eval_run(
            {
                "id": f"{model_name}__{prompt_version}__{case['id']}",
                "model_name": model_name,
                "prompt_version": prompt_version,
                "q_id": case["id"],
                "answer": out["answer"],
                "latency_ms": lat_ms,
                "score_correctness": scores["score_correctness"],
                "score_groundedness": scores["score_groundedness"],
                "score_language": scores["score_language"],
                "agreement_score": agr,
            },
            db_path=db_path,
        )
    return get_run_summary(model_name, prompt_version, db_path=db_path)
