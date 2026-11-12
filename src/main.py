from fastapi import Depends, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from src.db import list_runs
from src.judge import judge_response
from src.regression import compare_and_check_regression
from src.security import is_prompt_injection, mask_pii, verify_api_key

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Box 3 Evaluation & Regression API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class EvalRequest(BaseModel):
    class Config:
        extra = "forbid"
    id: str = Field(default="api_q", min_length=1, max_length=40)
    question: str = Field(..., min_length=3, max_length=500)
    answer: str = Field(..., min_length=1, max_length=2000)
    expected_ref: str = Field(default="", max_length=50)
    expected_answer: str = Field(default="", max_length=1000)
    keywords: list = Field(default_factory=list)
    is_answerable: bool = True


class RegressionRequest(BaseModel):
    class Config:
        extra = "forbid"
    baseline_prompt: str = Field(default="prompt_v1", min_length=2, max_length=40)
    candidate_prompt: str = Field(default="prompt_v2", min_length=2, max_length=40)
    max_drop_pct: float = Field(default=3.0, ge=0.0, le=50.0)


@app.get("/health")
def health():
    return {"status": "ok", "service": "box3_evaluation_framework"}


@app.post("/evaluate")
@limiter.limit("20/minute")
def evaluate_endpoint(request: Request, body: EvalRequest, _: str = Depends(verify_api_key)):
    q_clean = mask_pii(body.question)
    a_clean = mask_pii(body.answer)
    if is_prompt_injection(q_clean) or is_prompt_injection(a_clean):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt injection detected and blocked")
    return judge_response(
        {"id": body.id, "question": q_clean, "expected_ref": body.expected_ref,
         "expected_answer": body.expected_answer, "keywords": body.keywords, "is_answerable": body.is_answerable},
        a_clean,
    )


@app.post("/regression")
@limiter.limit("20/minute")
def regression_endpoint(request: Request, body: RegressionRequest, _: str = Depends(verify_api_key)):
    return compare_and_check_regression(
        baseline_prompt=body.baseline_prompt,
        candidate_prompt=body.candidate_prompt,
        max_drop_pct=body.max_drop_pct,
        write_report=False,
    )


@app.get("/report")
@limiter.limit("20/minute")
def report_endpoint(request: Request, _: str = Depends(verify_api_key)):
    return {"runs": list_runs()}
