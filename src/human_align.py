import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from src.judge import judge_response


def cohen_kappa(y_true: List[int], y_pred: List[int], labels: Tuple = (0, 1, 2)) -> float:
    n = len(y_true)
    if n == 0:
        return 0.0
    po = sum(1 for a, b in zip(y_true, y_pred) if a == b) / n
    pe = sum((y_true.count(k) / n) * (y_pred.count(k) / n) for k in labels)
    if pe >= 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1.0 - pe)


def compute_human_alignment(
    golden_path: str = "data/golden_eval.jsonl",
    human_path: str = "data/human_annotations.jsonl",
    provider: Optional[str] = "mock",
) -> Dict[str, Any]:
    cases = {}
    with open(golden_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                cases[row["id"]] = row

    samples = []
    with open(human_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    hc_list, jc_list, hg_list, jg_list = [], [], [], []
    exact_corr, exact_ground, within_one = 0, 0, 0
    details = []

    for s in samples:
        case = cases[s["q_id"]]
        res = judge_response(case, s["model_answer"], provider=provider)
        hc, hg = int(s["human_correctness"]), int(s["human_groundedness"])
        jc, jg = int(res["score_correctness"]), int(res["score_groundedness"])
        hc_list.append(hc)
        jc_list.append(jc)
        hg_list.append(hg)
        jg_list.append(jg)
        if hc == jc:
            exact_corr += 1
        if hg == jg:
            exact_ground += 1
        if abs(hc - jc) <= 1 and abs(hg - jg) <= 1:
            within_one += 1
        details.append({"q_id": s["q_id"], "human": (hc, hg), "judge": (jc, jg)})

    n = len(samples) or 1
    return {
        "samples": len(samples),
        "exact_correctness_pct": round((exact_corr / n) * 100.0, 2),
        "exact_groundedness_pct": round((exact_ground / n) * 100.0, 2),
        "within_one_pct": round((within_one / n) * 100.0, 2),
        "kappa_correctness": round(cohen_kappa(hc_list, jc_list), 4),
        "kappa_groundedness": round(cohen_kappa(hg_list, jg_list), 4),
        "details": details,
    }


if __name__ == "__main__":
    res = compute_human_alignment()
    print({k: v for k, v in res.items() if k != "details"})
