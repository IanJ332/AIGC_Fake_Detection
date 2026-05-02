#!/bin/bash
# Reproduction script for AIGC Fake Detection Research QA Engine
# This script reruns evaluation on an existing data bundle. 
# It does not regenerate PDFs or extracted data unless explicitly modified.

set -e

echo "Starting reproduction pipeline..."

# 1. Install Dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# 2. Setup Data Directory
# Expected structure in /content/drive/MyDrive/AIGC/Data or local ./Data
DATA_DIR=${1:-"./Data"}
echo "Using data directory: $DATA_DIR"

if [ ! -d "$DATA_DIR" ]; then
    echo "Error: Data directory $DATA_DIR not found."
    echo "Please ensure Google Drive is mounted and data exists."
    exit 1
fi

# 3. Run Day 5 Extraction Pipeline (Simulation)
# In a real environment, this would call:
# python src/extract/extract_entities.py --data-dir $DATA_DIR
# python src/extract/extract_results.py --data-dir $DATA_DIR
echo "Skipping extraction pipeline execution to protect existing data..."
echo "Verify Data/extracted/*.csv exists."

# 4. Run Day 6 Evaluation
echo "Running 40-question evaluation suite..."
python eval/run_eval.py --data-dir "$DATA_DIR" --questions eval/questions_40.jsonl

echo "Reproduction complete. See eval/results/day6_eval_summary.md for report."
