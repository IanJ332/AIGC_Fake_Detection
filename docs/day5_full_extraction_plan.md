# Day 5: Full Extraction Pipeline Plan

## Goal
Implement a production-grade extraction pipeline that converts raw parsed sections and table candidates into structured research entities and result tuples. This data will form the core of the Research Comprehension System, enabling complex queries across the 100-paper corpus.

## Pipeline Architecture
The pipeline consists of five stages, executed sequentially:

1. **Entity Extraction (`extract_entities.py`)**:
   - Scans all sections for mentions of datasets, models, generators, metrics, and distortions using expanded rule-based dictionaries.
   - Generates a granular `entities.csv` with evidence anchors and context snippets.

2. **Result Extraction (`extract_results.py`)**:
   - Processes table candidates to identify performance metrics and their corresponding numeric values.
   - Maps values to conditions (e.g., robustness, cross-generator) and assigns confidence scores.

3. **Paper Summarization (`build_paper_summaries.py`)**:
   - Aggregates extraction results to create per-paper views.
   - Generates coverage statistics for sections and entity counts.

4. **Database Indexing (`build_duckdb.py`)**:
   - Ingests all CSV/JSONL files into a unified DuckDB database (`research_corpus.duckdb`) for high-performance analytical queries.

5. **Validation & Reporting (`validate_extraction.py`)**:
   - Audit the extraction yield against defined thresholds (>1000 entities, >500 results).
   - Produces `day5_full_extraction_report.md` with top-k distributions and pipeline health status.

## Data Schema
### Entities
- `paper_id`, `entity_type`, `entity`, `section_type`, `evidence_anchor`, `context_snippet`

### Result Tuples
- `paper_id`, `dataset_guess`, `metric_guess`, `value_numeric`, `condition_guess`, `evidence_anchor`

### DuckDB Tables
- `papers`, `sections`, `entities`, `result_tuples`, `paper_entity_summary`

## Operational Constraints
- **Compute**: CPU-only, Python 3.10+.
- **Storage**: Persistent outputs written to Google Drive (`Data/extracted/`, `Data/index/`).
- **Dependencies**: `pandas`, `tqdm`, `duckdb`.

## Success Criteria
- [ ] Pipeline runs end-to-end on 72+ parsed papers.
- [ ] >1000 entities extracted.
- [ ] >500 result tuples extracted.
- [ ] DuckDB index successfully created and queryable.
- [ ] Final report status is `PROCEED`.
