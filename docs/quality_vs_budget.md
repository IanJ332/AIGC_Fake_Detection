# Quality vs Budget

## Summary

This document reports actual measured performance at three local budget levels plus two planned higher-budget tiers.

---

## Measured Local Ablations (All $0, No Paid APIs)

All three levels were executed on the same 40-question evaluation set (`eval/questions_40.jsonl`) against the full extracted corpus (`Data/extracted/`).

| Level | Mode | Routing Accuracy | Op Success | Evidence Coverage | Avg Latency | Spend |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | `router_only` — Return tier label only | 92.5% | 100% | 0% | <1 ms | $0.00 |
| 1 | `operator_no_evidence` — Run operator, suppress evidence | 92.5% | 100% | 0% | 25 ms | $0.00 |
| 2 | `operator_with_evidence` — Full pipeline (current system) | 92.5% | 100% | 100% | 24 ms | $0.00 |

> [!IMPORTANT]
> These numbers are real, measured results produced by `eval/run_budget_eval.py`. Raw per-question results are in `artifacts/reports/budget_eval_results.csv`. See `artifacts/reports/budget_eval_summary.md` for the auto-generated table.

**Key finding**: The operator pipeline adds evidence coverage (0% → 100%) with essentially no latency cost over the operator-only mode. The routing accuracy ceiling at 92.5% reflects 3 questions that require disambiguation between similar tiers (temporal vs. quantitative for year-specific count questions).

---

## Planned Higher-Budget Tiers (Not Yet Run)

These two tiers would require paid API spend and have not been executed. They are documented here as the natural extension of the ablation curve.

| Level | Mode | Expected Routing | Expected Evidence | Expected Spend | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 3 | Embedding reranking (`sentence-transformers/all-MiniLM-L6-v2`, local free model) | ~92–95% | Higher quality snippets | $0.00 (local GPU/CPU) | **Planned** |
| 4 | LLM synthesis (e.g., GPT-4o-mini answer synthesis over retrieved snippets) | ~95%+ | Synthesised prose answers | ~$0.01–$0.05/question | **Planned** |

> [!NOTE]
> Level 3 can be run locally at $0 cost using the optional `sentence-transformers` dependency documented in `requirements.txt`. It is not enabled by default to avoid the ~400MB model download requirement.

---

## Interpretation

The measured curve demonstrates:

1. **Router alone** is sufficient for tier classification (92.5%).
2. **Operator execution** provides structured, defensible answers at effectively zero marginal cost.  
3. **Evidence attachment** (Level 2) is the primary value-add: every answer includes a traceable data source (CSV file, evidence snippet, or section text).
4. Paid-API tiers would primarily improve answer fluency and synthesis quality, not routing or coverage — an acceptable trade-off for a zero-cost deployment.

---

## Cost per Question

| Tier | Spend per question |
| :--- | :--- |
| Levels 0–2 (current) | $0.00 |
| Level 3 (local embeddings) | $0.00 |
| Level 4 (LLM, planned) | ~$0.01–$0.05 |

Total project spend to date: **$0.00** (OpenAlex API is free; no paid models used).
