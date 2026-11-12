from src.human_align import compute_human_alignment


def test_human_judge_alignment_threshold():
    res = compute_human_alignment()
    assert res["samples"] == 20
    assert res["exact_correctness_pct"] >= 85.0
    assert res["exact_groundedness_pct"] >= 85.0
    assert res["kappa_correctness"] >= 0.70
