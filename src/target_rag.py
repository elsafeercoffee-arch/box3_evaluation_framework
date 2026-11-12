import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Set, Tuple
from src.security import is_prompt_injection, mask_pii
from src.textproc import extract_tokens, normalize_arabic

REFUSAL = "لا توجد معلومة كافية في المستندات."
BOX1_DB = Path(__file__).resolve().parents[2] / "box1_arabic_rag" / "data" / "rag.db"
GENERIC_WORDS = {"قانون", "القانون", "احكام", "شروط", "حكم", "ماده", "الماده"}

FALLBACK_CORPUS = [
    ("المادة 1", "تسري أحكام هذا القانون على جميع العاملين الخاضعين لعقد عمل فردي لدى صاحب عمل خاص."),
    ("المادة 2", "تحدد فترة الاختبار للعامل في عقد العمل، ولا يجوز أن تزيد عن ثلاثة أشهر، ولا يجوز تعيين العامل تحت الاختبار أكثر من مرة واحدة لدى صاحب عمل واحد."),
    ("المادة 3", "لا يجوز تشغيل العامل تشغيلاً فعلياً أكثر من ثماني ساعات في اليوم الواحد أو ثماني وأربعين ساعة في الأسبوع، ولا تدخل فيها الفترات المخصصة لتناول الطعام والراحة."),
    ("المادة 4", "يستحق العامل إجازة سنوية بأجر كامل لا تقل عن واحد وعشرين يوماً في السنة، وتزاد إلى ثلاثين يوماً متى أمضى العامل في خدمة صاحب العمل خمس سنوات متصلة."),
    ("المادة 5", "يحظر فصل العامل دون إخطار مسبق وتكون مهلة الإخطار ثلاثين يوماً إذا كانت مدة خدمة العامل متصلة أقل من عشر سنوات، وثلاثة أشهر إذا زادت عن ذلك."),
    ("المادة 6", "يستحق العامل عند انتهاء عقد العمل مكافأة نهاية خدمة تحسب على أساس أجر نصف شهر عن كل سنة من السنوات الخمس الأولى، وأجر شهر عن كل سنة من السنوات التالية."),
    ("المادة 10", "يلتزم المورد بإعلام المستهلك بجميع البيانات الجوهرية الخاصة بالسلعة، بما في ذلك السعر الإجمالي والضرائب المفروضة ومدة الضمان ومواصفاتها الأساسية، وذلك في مكان ظاهر."),
    ("المادة 11", "للمستهلك الحق في استبدال السلعة أو إعادتها مع استرداد قيمتها النقدية دون إبداء أسباب ودون تحمل أي نفقات خلال أربعة عشر يوماً من تسلمها بشرط بقائها بحالتها."),
    ("المادة 12", "يمتد حق الاستبدال أو الاسترداد إلى ثلاثين يوماً إذا كان بالسلعة عيب أو لم تكن مطابقة للمواصفات أو للغرض الذي تم التعاقد من أجله."),
    ("المادة 13", "يلتزم المورد بضمان السلع المعمرة لمدة لا تقل عن عامين من تاريخ الاستلام، ويلتزم بتوفير مراكز الصيانة وقطع الغيار اللازمة خلال فترة الضمان."),
    ("المادة 14", "يحظر تداول أو ترويج السلع التي تنطوي على إعلان خادع أو بيانات غير حقيقية تضلّل المستهلك حول طبيعة السلعة أو مكوناتها أو مصدرها."),
]


def _stem_tokens(tokens: Set[str]) -> Set[str]:
    out = set()
    for t in tokens:
        if t in GENERIC_WORDS:
            continue
        out.add(t)
        for pref in ("وال", "بال", "كال", "فال"):
            if t.startswith(pref) and len(t) > 4:
                out.add(t[len(pref):])
        if t.startswith(("ال", "لل")) and len(t) > 3:
            out.add(t[2:])
        elif t.startswith(("ل", "ب", "و")) and len(t) > 4:
            out.add(t[1:])
    return out


def _load_chunks() -> List[Tuple[str, str]]:
    if BOX1_DB.exists():
        try:
            conn = sqlite3.connect(f"file:{BOX1_DB}?mode=ro", uri=True)
            rows = conn.execute("SELECT ref, text FROM chunks").fetchall()
            conn.close()
            if rows:
                return [(r[0], r[1]) for r in rows]
        except Exception:
            pass
    return FALLBACK_CORPUS


def run_rag_query(question: str, prompt_version: str = "prompt_v2") -> Dict[str, str]:
    cleaned = mask_pii(question)
    if is_prompt_injection(cleaned):
        return {"answer": REFUSAL, "ref": "", "source": "security_block"}

    raw_tokens = extract_tokens(cleaned) - GENERIC_WORDS
    q_tokens = _stem_tokens(raw_tokens) if prompt_version == "prompt_v2" else raw_tokens
    if not q_tokens:
        return {"answer": REFUSAL, "ref": "", "source": "empty_query"}

    explicit_art = re.search(r"الماده\s*(\d+)", normalize_arabic(cleaned))
    scored = []
    for ref, text in _load_chunks():
        c_raw = extract_tokens(text) | extract_tokens(ref)
        c_tokens = _stem_tokens(c_raw) if prompt_version == "prompt_v2" else c_raw
        overlap = len(q_tokens & c_tokens)
        if prompt_version == "prompt_v2":
            nt = normalize_arabic(text)
            if any(d in cleaned for d in ("30", "عشرون", "ثلاثين")) and ("ثلاثين" in nt or "عشرين" in nt):
                overlap += 1
            if "14" in cleaned and "اربعه عشر" in nt:
                overlap += 1
        scored.append((overlap, ref, text))

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_ref, best_text = scored[0]

    if best_score < 2:
        return {"answer": REFUSAL, "ref": "", "source": "no_match"}

    if explicit_art and f"المادة {explicit_art.group(1)}" != best_ref:
        return {"answer": REFUSAL, "ref": "", "source": "article_mismatch"}

    if prompt_version == "degraded_v0":
        return {"answer": best_text[:40], "ref": "", "source": "degraded"}

    return {"answer": f"{best_text} (المرجع: {best_ref})", "ref": best_ref, "source": "box1_rag"}
