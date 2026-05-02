#!/bin/bash
set -euo pipefail
set -x

DATA_DIR=${1:-"/content/drive/MyDrive/AIGC/Data"}

echo "Running sample QA queries..."
python -m src.query.cli --data-dir "$DATA_DIR" --question "What are the top 10 datasets mentioned across the corpus?"
python -m src.query.cli --data-dir "$DATA_DIR" --question "What does paper P001 propose?"
python -m src.query.cli --data-dir "$DATA_DIR" --question "Are there conflicting results for FaceForensics++?"

echo "Running full 40-question evaluation..."
python eval/run_eval.py --data-dir "$DATA_DIR" --questions eval/questions_40.jsonl

echo "Day 6 QA Engine check complete."
