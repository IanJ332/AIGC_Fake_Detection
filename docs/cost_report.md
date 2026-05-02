# Project Cost Report: Analytical QA Engine

This document summarizes the financial expenditures and resource utilization for the building and execution of the AIGC Fake Detection research comprehension system.

## Financial Summary

| Category | Cost (USD) | Notes |
| :--- | :--- | :--- |
| **Model API (LLM)** | $0.00 | Purely deterministic rule-based operators (DuckDB/Pandas). |
| **Embedding API** | $0.00 | No vector search or embeddings used in the core engine. |
| **Data Acquisition** | $0.00 | OpenAlex/Semantic Scholar free tier APIs used via `pyalex` and `scholarly`. |
| **PDF Processing** | $0.00 | Local `Marker` / `pdfplumber` execution. |
| **Compute (Colab)** | $0.00 | Standard free tier Google Colab instances used. |
| **Total Spend** | **$0.00** | |

## Operational Metrics

- **Cost per Question**: $0.00 (Local/Free CPU execution).
- **Latency per Question**: ~1.5s - 4.0s (mostly DuckDB IO).
- **Storage Requirement**: ~1.2GB for 100 PDFs and associated parsed JSON/indices.

## Infrastructure Notes

- **403 PDF Failures**: Approximately 28% of target PDFs returned 403 Forbidden errors during direct publisher requests. These were handled by free fallbacks (e.g., searching for open access versions via OpenAlex), resulting in a 72-paper final corpus.
- **Compute**: All extraction and QA logic is designed for consumer-grade CPU environments, requiring no GPU acceleration.
