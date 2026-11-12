# Box 3: LLM Evaluation & Regression Framework

Automated evaluation, bias-auditing, and regression-gating framework for Arabic Hybrid RAG systems, built under low-resource constraints (**Samsung Galaxy S8+ | 4GB RAM | Termux | $0 cloud cost**).

## Architecture

    [72 Golden Cases (direct / complex / trap / out_of_scope)]
                                |
                                v
               [Box 1 Arabic RAG (SQLite FTS5 RO)]
                 (prompt_v1 vs prompt_v2 vs degraded)
                                |
                                v
             [LLM-as-a-Judge + Deterministic Fallback]
              |-- Rubric (0-2): Correctness, Groundedness, Language
              |-- Bias Checks: Length Bias & Position Consistency
              |-- Human Alignment: 20 Expert Samples (Kappa)
                                |
                                v
              [SQLite: eval_runs] --> [Regression Gate (>3% drop => FAIL)]

## Real Benchmark Metrics (72 Golden Cases)
| Metric | Baseline (`prompt_v1`) | Candidate (`prompt_v2`) |
|---|---:|---:|
| Overall Score | 69.79% | **73.96%** (+4.17%) |
| Human-Judge Agreement (n=20) | 100.0% (`kappa=1.0`) | 100.0% (`kappa=1.0`) |
| Length Bias Free | Yes | Yes |
| Position Consistent | Yes | Yes |
| Regression Gate (Max Drop 3%) | Baseline | **PASSED** |

## Failure Analysis & Trade-offs
- **Low-Resource Trade-off:** Running a >1B local LLM on 4GB RAM is infeasible; therefore, evaluation pairs an optional free REST judge (`JUDGE_PROVIDER=gemini`) with a calibrated deterministic offline judge (`mock`) for zero-cost CI.
- **Observed Gap (~26%):** Complex paraphrased queries with unseen Arabic synonyms under-match FTS5 without dense neural reranking; `prompt_v2` resolves prefix attachment (`ال/لل/وال/بال`) and number-word variants (+4.17%).

## Quickstart & Security

    python -m src.regression
    python -m src.regression --candidate-prompt degraded_v0
    pytest -v
    uvicorn src.main:app --host 127.0.0.1 --port 8000

- API enforces `X-API-Key` (`401`), Pydantic `extra="forbid"` (`422`), PII masking, and Prompt Injection blocking (`400`).
