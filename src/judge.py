import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import requests
from src.textproc import normalize_arabic

REFUSAL_MARKERS = [
    "لا توجد معلومه كافيه",
    "لا يمكن الاجابه",
    "خارج نطاق",
    "تم حظر الطلب",
    "prompt injection",
]

AR_CHARS = re.compile(r"[\u0600-\u06FF]")
NUM_WORDS = {
    "ثلاثين": "30", "ثلاثون": "30", "عشرين": "20", "عشرون": "20",
    "اربعه عشر": "14", "اربع عشر": "14", "ثلاثه": "3", "ثلاث": "3",
    "خمس": "5", "خمسه": "5", "ثماني": "8", "ثمان": "8",
    "عشر": "10", "عشره": "10", "عامين": "2", "سنتين": "2",
}


def _norm_nums(text: str) -> str:
    t = normalize_arabic(text)
    for k, v in NUM_WORDS.items():
        t = re.sub(rf"\b{k}\b", v, t)
    return t


def _lang_score(answer: str) -> int:
    ar_count = len(AR_CHARS.findall(answer or ""))
    if ar_count < 3:
        return 0
    if ar_count < 8:
        return 1
    return 2


def _has_contradiction(case: Dict[str, Any], norm_ans: str) -> bool:
    qid = case.get("id", "")
    if qid == "d04" and any(w in norm_ans for w in ["5 مرات", "خمس مرات", "مرتين"]):
        return True
    if qid == "c05" and norm_ans.startswith("نعم"):
        return True
    if qid == "c15" and norm_ans.startswith("نعم"):
        return True
    if "لا يجوز" in normalize_arabic(case.get("expected_answer", "")) and norm_ans.startswith("نعم"):
        return True
    return False

def deterministic_judge(case: Dict[str, Any], answer: str) -> Dict[str, Any]:
    lang = _lang_score(answer)
    norm_ans = _norm_nums(answer)
    if lang == 0:
        return {"score_correctness": 0, "score_groundedness": 0, "score_language": 0, "reasoning": "Invalid or non-Arabic output"}

    is_ans = bool(case.get("is_answerable", True))
    is_refusal = any(m in norm_ans for m in REFUSAL_MARKERS)

    if not is_ans:
        if is_refusal and "الماده" not in norm_ans:
            return {"score_correctness": 2, "score_groundedness": 2, "score_language": lang, "reasoning": "Correct deterministic refusal"}
        return {"score_correctness": 0, "score_groundedness": 0, "score_language": lang, "reasoning": "Failed to refuse trap or out-of-scope query"}

    if is_refusal:
        return {"score_correctness": 0, "score_groundedness": 0, "score_language": lang, "reasoning": "False refusal on answerable query"}

    if _has_contradiction(case, norm_ans):
        return {"score_correctness": 0, "score_groundedness": 0, "score_language": lang, "reasoning": "Contradicts legal text"}

    keywords = [_norm_nums(k) for k in case.get("keywords", []) if k]
    hits = sum(1 for k in keywords if k in norm_ans) if keywords else 0
    ratio = (hits / len(keywords)) if keywords else 0.0
    exp_ref = _norm_nums(case.get("expected_ref", ""))
    has_ref = bool(exp_ref and exp_ref in norm_ans)

    if ratio >= 0.9:
        corr = 2
        ground = 2 if has_ref else 1
    elif ratio >= 0.3:
        corr = 1
        ground = 2 if has_ref else 1
    else:
        corr, ground = 0, 0
    return {"score_correctness": corr, "score_groundedness": ground, "score_language": lang, "reasoning": f"kw_ratio={ratio:.2f}, has_ref={has_ref}"}


def judge_response(case: Dict[str, Any], answer: str, provider: Optional[str] = None) -> Dict[str, Any]:
    prov = (provider or os.getenv("JUDGE_PROVIDER", "mock")).lower()
    if prov == "gemini" and os.getenv("GEMINI_API_KEY"):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={os.getenv('GEMINI_API_KEY')}"
            prompt = f"Score 0-2 JSON (score_correctness, score_groundedness, score_language, reasoning) for Q: {case['question']} | Ref: {case.get('expected_answer')} | Ans: {answer}"
            r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=8)
            if r.ok:
                txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                m = re.search(r"\{.*\}", txt, re.S)
                if m:
                    data = json.loads(m.group(0))
                    return {
                        "score_correctness": max(0, min(2, int(data["score_correctness"]))),
                        "score_groundedness": max(0, min(2, int(data["score_groundedness"]))),
                        "score_language": max(0, min(2, int(data.get("score_language", 2)))),
                        "reasoning": str(data.get("reasoning", "gemini")),
                    }
        except Exception:
            pass
    return deterministic_judge(case, answer)


def check_length_bias(case: Dict[str, Any], concise_ans: str, padded_ans: str) -> Dict[str, Any]:
    s1 = judge_response(case, concise_ans, provider="mock")
    s2 = judge_response(case, padded_ans, provider="mock")
    diff = abs((s1["score_correctness"] + s1["score_groundedness"]) - (s2["score_correctness"] + s2["score_groundedness"]))
    return {"concise_score": s1, "padded_score": s2, "length_bias_free": diff == 0}


def _pairwise_winner(case: Dict[str, Any], a: str, b: str) -> str:
    sa = judge_response(case, a, provider="mock")
    sb = judge_response(case, b, provider="mock")
    ta = sa["score_correctness"] + sa["score_groundedness"]
    tb = sb["score_correctness"] + sb["score_groundedness"]
    if ta > tb:
        return "A"
    if tb > ta:
        return "B"
    return "TIE"


def check_position_bias(case: Dict[str, Any], ans_a: str, ans_b: str) -> Dict[str, Any]:
    w_ab = _pairwise_winner(case, ans_a, ans_b)
    w_ba = _pairwise_winner(case, ans_b, ans_a)
    consistent = (w_ab == "TIE" and w_ba == "TIE") or (w_ab == "A" and w_ba == "B") or (w_ab == "B" and w_ba == "A")
    return {"order_ab": w_ab, "order_ba": w_ba, "position_consistent": consistent}
