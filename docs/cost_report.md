# Cost Report

## Financial Summary

| Category | Cost (USD) | Notes |
| :--- | :--- | :--- |
| **Model API (LLM)** | $0.00 | Purely deterministic rule-based operators (DuckDB/Pandas). No LLM calls. |
| **Embedding API** | $0.00 | No vector search or embeddings used. |
| **Data Acquisition** | $0.00 | OpenAlex API (free, public). |
| **PDF Processing** | $0.00 | Local pdfplumber execution. |
| **Compute** | $0.00 | Google Colab free tier + local CPU. |
| **Total Spend** | **$0.00** | |

## Cost per Question

| Metric | Value |
| :--- | :--- |
| Mean | $0.00 |
| Median | $0.00 |
| Max | $0.00 |
| Latency (avg) | ~135 ms |

All 40 evaluation questions run locally with zero API cost.

## Infrastructure Notes

- **Corpus**: 117-paper executable corpus assembled via OpenAlex API (free). OpenAlex and OA backfill use no paid APIs.
- **PDF Acquisition**: Some publisher PDFs return 403 Forbidden. The system successfully backfills these with Open Access candidates. The final executable corpus achieved 117 parsed papers.
- **Compute**: All extraction and QA logic runs on consumer-grade CPU. No GPU required.
- **Storage**: ~1.2 GB for PDFs + parsed JSON + DuckDB index.

## Quality-vs-Budget Curve

See [quality_vs_budget.md](quality_vs_budget.md) for the 3-level measured ablation.
