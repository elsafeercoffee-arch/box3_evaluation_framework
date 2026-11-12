from src.judge import check_length_bias, check_position_bias, judge_response

SAMPLE_CASE = {
    "id": "d03",
    "question": "ما هي المدة القصوى لفترة الاختبار للعامل؟",
    "expected_ref": "المادة 2",
    "expected_answer": "لا يجوز أن تزيد فترة الاختبار عن ثلاثة أشهر.",
    "keywords": ["ثلاثة", "اشهر", "الاختبار"],
    "is_answerable": True,
}


def test_judge_perfect_and_wrong_scores():
    good = judge_response(SAMPLE_CASE, "فترة الاختبار لا تزيد عن ثلاثة أشهر. (المرجع: المادة 2)", provider="mock")
    assert good["score_correctness"] == 2
    assert good["score_groundedness"] == 2
    bad = judge_response(SAMPLE_CASE, "يمكن العمل بدون أي حدود زمنية.", provider="mock")
    assert bad["score_correctness"] == 0


def test_judge_refusal_on_out_of_scope():
    oos = {"id": "o01", "question": "ما عقوبة المرور؟", "expected_ref": "", "expected_answer": "", "keywords": [], "is_answerable": False}
    ok = judge_response(oos, "لا توجد معلومة كافية في المستندات.", provider="mock")
    assert ok["score_correctness"] == 2 and ok["score_groundedness"] == 2
    hallucinated = judge_response(oos, "الغرامة 1000 جنيه وفقاً للمادة 1.", provider="mock")
    assert hallucinated["score_correctness"] == 0


def test_length_and_position_bias():
    concise = "فترة الاختبار لا تزيد عن ثلاثة أشهر. (المرجع: المادة 2)"
    padded = concise + (" كلام عام إضافي مكرر لتطويل الإجابة." * 6)
    lb = check_length_bias(SAMPLE_CASE, concise, padded)
    assert lb["length_bias_free"] is True
    pb = check_position_bias(SAMPLE_CASE, concise, "إجابة خاطئة تماماً.")
    assert pb["position_consistent"] is True
