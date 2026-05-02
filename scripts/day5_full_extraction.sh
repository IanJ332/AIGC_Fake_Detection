#!/bin/bash

# Day 5 Full Extraction Pipeline Orchestrator
set -euo pipefail
set -x

DATA_DIR=${1:-"/content/drive/MyDrive/AIGC/Data"}

echo "Starting Day 5 Full Extraction Pipeline..."
echo "Data Directory: $DATA_DIR"

# 1. Extract Entities
echo "[1/5] Extracting entities..."
python -m src.extract.extract_entities --data-dir "$DATA_DIR"

# 2. Extract Result Tuples
echo "[2/5] Extracting result tuples..."
python -m src.extract.extract_results --data-dir "$DATA_DIR"

# 3. Build Paper Summaries
echo "[3/5] Building paper summaries..."
python -m src.extract.build_paper_summaries --data-dir "$DATA_DIR"

# 4. Build DuckDB Index
echo "[4/5] Building DuckDB index..."
python -m src.extract.build_duckdb --data-dir "$DATA_DIR"

# 5. Validate Extraction
echo "[5/5] Validating extraction..."
python -m src.extract.validate_extraction --data-dir "$DATA_DIR"

echo "Pipeline complete."
