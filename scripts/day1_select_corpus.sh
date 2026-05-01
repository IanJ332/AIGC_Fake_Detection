#!/bin/bash

echo "Starting Day 1 Corpus Selection..."

# 1. Run selection script
python -m src.ingest.select_corpus --input corpus/raw_metadata/semantic_scholar_backfill.jsonl

echo "Corpus selection complete. Check corpus/manifest_100.csv"
