import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from src.db import get_run_summary
from src.human_align import compute_human_alignment
from src.judge import check_length_bias, check_position_bias
from src.runner import evaluate_config, load_golden


def write_eval_report(res: Dict[str, Any], out_path: str = "docs/eval_report.md") -> None:
    b, c, al = res["baseline"], res["candidate"], res["alignment"]
    status = "PASSED" if res["passed"] else "FAILED"
    md = f"""# Box 3: LLM Evaluation & Regression Report

## 1. Model / Prompt Comparison (72 Golden Cases)
| Metric | Baseline (`{b['model_name']}` / `{b['prompt_version']}`) | Candidate (`{c['model_name']}` / `{c['prompt_version']}`) |
|---|---:|---:|
| Total Cases | {b['total_cases']} | {c['total_cases']} |
| Avg Correctness (0-2) | {b['avg_correctness']} | {c['avg_correctness']} |
| Avg Groundedness (0-2) | {b['avg_groundedness']} | {c['avg_groundedness']} |
| Avg Language (0-2) | {b['avg_language']} | {c['avg_language']} |
| **Overall Score (%)** | **{b['overall_score_pct']}%** | **{c['overall_score_pct']}%** |
| Avg Latency (ms) | {b['avg_latency_ms']} | {c['avg_latency_ms']} |

## 2. Human-Judge Alignment (20 Samples)
- Exact Correctness Agreement: **{al['exact_correctness_pct']}%** (`kappa={al['kappa_correctness']}`)
- Exact Groundedness Agreement: **{al['exact_groundedness_pct']}%** (`kappa={al['kappa_groundedness']}`)
- Within ±1 Agreement: **{al['within_one_pct']}%**

## 3. Judge Bias & Regression Gate
- Length Bias Free: **{res['length_bias_free']}**
- Position Consistent: **{res['position_consistent']}**
- Score Drop vs Baseline: **{res['drop_pct']}%** (Max Allowed: {res['max_drop_pct']}%)
- **Regression Gate Status: {status}**
"""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(md, encoding="utf-8")


def compare_and_check_regression(
    baseline_model: str = "hybrid-rrf-v1",
    baseline_prompt: str = "prompt_v1",
    candidate_model: str = "hybrid-rrf-v2",
    candidate_prompt: str = "prompt_v2",
    max_drop_pct: Optional[float] = None,
    db_path: Optional[str] = None,
    run_eval: bool = True,
    write_report: bool = True,
) -> Dict[str, Any]:
    limit = float(max_drop_pct if max_drop_pct is not None else os.getenv("REGRESSION_MAX_DROP_PCT", "3.0"))
    if run_eval:
        base = evaluate_config(baseline_model, baseline_prompt, db_path=db_path)
        cand = evaluate_config(candidate_model, candidate_prompt, db_path=db_path)
    else:
        base = get_run_summary(baseline_model, baseline_prompt, db_path=db_path)
        cand = get_run_summary(candidate_model, candidate_prompt, db_path=db_path)

    drop_pct = round(base["overall_score_pct"] - cand["overall_score_pct"], 2)
    align = compute_human_alignment()
    sample = load_golden()[0]
    lb = check_length_bias(sample, f"{sample['expected_answer']} (المرجع: {sample['expected_ref']})", f"{sample['expected_answer']} (المرجع: {sample['expected_ref']}) " + ("تفاصيل إضافية عامة. " * 6))
    pb = check_position_bias(sample, f"{sample['expected_answer']} (المرجع: {sample['expected_ref']})", "إجابة غير دقيقة.")

    res = {
        "passed": drop_pct <= limit and cand["total_cases"] > 0,
        "drop_pct": drop_pct,
        "max_drop_pct": limit,
        "baseline": base,
        "candidate": cand,
        "alignment": {k: v for k, v in align.items() if k != "details"},
        "length_bias_free": lb["length_bias_free"],
        "position_consistent": pb["position_consistent"],
    }
    if write_report:
        write_eval_report(res)
    return res


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--candidate-prompt", default="prompt_v2")
    p.add_argument("--candidate-model", default="hybrid-rrf-v2")
    args = p.parse_args()
    out = compare_and_check_regression(candidate_model=args.candidate_model, candidate_prompt=args.candidate_prompt)
    print(f"Baseline: {out['baseline']['overall_score_pct']}% | Candidate: {out['candidate']['overall_score_pct']}% | Drop: {out['drop_pct']}% | Passed: {out['passed']}")
    sys.exit(0 if out["passed"] else 1)
