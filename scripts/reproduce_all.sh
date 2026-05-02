#!/bin/bash
# scripts/reproduce_all.sh
# -------------------------
# Reproduction script for AIGC Fake Detection Research QA Engine.
#
# This script reruns evaluation on an existing data bundle by default.
# It does NOT regenerate PDFs or extracted data unless --rebuild is specified.
#
# Usage:
#   bash scripts/reproduce_all.sh [OPTIONS] [DATA_DIR]
#
# Options:
#   --eval-only   (default) Only run the 40-question evaluation against existing data.
#   --rebuild     Download accessible PDFs, run extraction, build DuckDB, then evaluate.
#   --help        Show this message.
#
# DATA_DIR: path to the data bundle directory (default: ./Data)
#
# Reproducibility modes:
#   eval-only   → requires pre-built Data/extracted/ and Data/index/
#   rebuild     → requires internet access; will download PDFs it can access;
#                 documents 403-blocked papers as known failures.

set -e

MODE="eval-only"
DATA_DIR=""
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"

for arg in "$@"; do
    case $arg in
        --eval-only) MODE="eval-only" ;;
        --rebuild)   MODE="rebuild" ;;
        --help)
            sed -n '/^#/p' "$0" | sed 's/^# *//'
            exit 0
            ;;
        *) DATA_DIR="$arg" ;;
    esac
done

DATA_DIR="${DATA_DIR:-./Data}"
echo "=== AIGC Research QA Engine — Reproduce ($MODE) ==="
echo "Data directory: $DATA_DIR"
echo ""

# ── 1. Install dependencies ────────────────────────────────────────────────
echo "[1/5] Installing dependencies..."
pip install -r requirements.txt -q

# ── 2. Rebuild mode: download PDFs and re-extract ─────────────────────────
if [ "$MODE" = "rebuild" ]; then
    echo "[2/5] Downloading accessible corpus PDFs..."
    python scripts/download_corpus.py \
        --manifest corpus/manifest.csv \
        --out-dir "$DATA_DIR/pdfs" \
        --report "$DATA_DIR/download_report.json"

    echo "[3/5] Parsing PDFs and extracting sections..."
    python src/parse/parse_pdfs.py --data-dir "$DATA_DIR"
    python src/parse/segment_sections.py --data-dir "$DATA_DIR"

    echo "[4/5] Running entity and result extraction..."
    python src/extract/extract_entities.py --data-dir "$DATA_DIR"
    python src/extract/extract_results.py --data-dir "$DATA_DIR"
    python src/extract/build_paper_summaries.py --data-dir "$DATA_DIR"
    python src/extract/build_duckdb.py --data-dir "$DATA_DIR"
else
    echo "[2-4/5] Skipping extraction (eval-only mode)."
    echo "  → Verifying required data files..."

    MISSING=0
    for f in \
        "$DATA_DIR/extracted/entities.csv" \
        "$DATA_DIR/extracted/result_tuples.csv" \
        "$DATA_DIR/index/research_corpus.duckdb"; do
        if [ ! -f "$f" ]; then
            echo "  [MISSING] $f"
            MISSING=1
        else
            echo "  [OK]      $f"
        fi
    done

    if [ "$MISSING" = "1" ]; then
        echo ""
        echo "ERROR: Required data files are missing."
        echo "Run with --rebuild to download and regenerate them, or"
        echo "ensure the Data/ bundle is present at: $DATA_DIR"
        exit 1
    fi
fi

# ── 5. Run evaluation ──────────────────────────────────────────────────────
echo "[5/5] Running 40-question evaluation suite..."
mkdir -p "$DATA_DIR/reports/day6_eval"

python eval/run_eval.py \
    --data-dir "$DATA_DIR" \
    --questions eval/questions_40.jsonl \
    --output-dir "$DATA_DIR/reports/day6_eval"

echo ""
echo "=== Reproduction complete ==="
echo "See $DATA_DIR/reports/day6_eval/ for the evaluation report."
