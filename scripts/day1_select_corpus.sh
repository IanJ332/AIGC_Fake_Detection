#!/bin/bash

echo "Starting Day 1 Corpus Selection and Audit..."

# 1. Run selection script
python -m src.ingest.select_corpus --input corpus/raw_metadata/openalex_raw.jsonl

# 2. Run audit
python -m src.ingest.audit_corpus

echo "Corpus selection and audit complete."
echo "Check docs/day1_corpus_audit.md and corpus/manifest_100.csv"
