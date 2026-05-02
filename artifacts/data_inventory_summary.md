# Data Inventory Summary

This document summarizes the local Data environment used for development and evaluation. To maintain a lightweight repository, the full `Data/` directory (including PDFs, DuckDB, and large JSONL files) is excluded from version control and is stored in a private Google Drive backup.

## Local Data Stats (Summary)
- **Total Local Data Size**: ~330.99 MB
- **Source PDFs**: 72 (in `Data/pdfs`)
- **Parsed JSON Documents**: 72 (in `Data/parsed`)
- **Total Entities Extracted**: 15,338
- **Total Result Tuples Extracted**: 771
- **Papers with Extracted Entities**: 72
- **Papers with Extracted Results**: 58
- **Database Backend**: DuckDB (locally stored at `Data/index/research_corpus.duckdb`)

## Evidence Artifacts (GitHub)
The following lightweight evidence is included in this repository under the `artifacts/` directory:
- **reports/**: Day 5 extraction logs and Day 6 evaluation summaries.
- **manifests/**: The 100-paper manifest and cross-referenced document registries.
- **samples/**: Representative CSV samples of the extraction output (first 100-200 rows) for structural audit.

Full extraction and evaluation can be re-run using the provided notebooks and scripts, provided the source `Data/` directory is present in the environment.
