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
echo "[3/6] Building paper summaries..."
python -m src.extract.build_paper_summaries --data-dir "$DATA_DIR"

# 4. Extract Numeric Claims
echo "[4/6] Extracting numeric claims..."
python -m src.extract.extract_numeric_claims --data-dir "$DATA_DIR"

# 5. Build DuckDB Index
echo "[5/6] Building DuckDB index..."
python -m src.extract.build_duckdb --data-dir "$DATA_DIR"

# 6. Validate Extraction
echo "[6/6] Validating extraction..."
python -m src.extract.validate_extraction --data-dir "$DATA_DIR"

echo "Pipeline complete."
