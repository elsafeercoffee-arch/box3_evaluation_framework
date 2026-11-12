# Box 3: LLM Evaluation & Regression Report

## 1. Model / Prompt Comparison (72 Golden Cases)
| Metric | Baseline (`hybrid-rrf-v1` / `prompt_v1`) | Candidate (`hybrid-rrf-v2` / `prompt_v2`) |
|---|---:|---:|
| Total Cases | 72 | 72 |
| Avg Correctness (0-2) | 1.3194 | 1.3889 |
| Avg Groundedness (0-2) | 1.4722 | 1.5694 |
| Avg Language (0-2) | 2.0 | 2.0 |
| **Overall Score (%)** | **69.79%** | **73.96%** |
| Avg Latency (ms) | 5.47 | 8.54 |

## 2. Human-Judge Alignment (20 Samples)
- Exact Correctness Agreement: **100.0%** (`kappa=1.0`)
- Exact Groundedness Agreement: **100.0%** (`kappa=1.0`)
- Within ±1 Agreement: **100.0%**

## 3. Judge Bias & Regression Gate
- Length Bias Free: **True**
- Position Consistent: **True**
- Score Drop vs Baseline: **-4.17%** (Max Allowed: 3.0%)
- **Regression Gate Status: PASSED**
