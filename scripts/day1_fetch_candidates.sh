#!/bin/bash

echo "Starting Day 1 Fetch Candidates..."

# 1. Fetch from OpenAlex
python -m src.ingest.openalex_fetch --config configs/corpus_query.yaml

# 2. Backfill with Semantic Scholar
python -m src.ingest.semantic_scholar_backfill --input corpus/raw_metadata/openalex_raw.jsonl

echo "Fetch and backfill complete."
