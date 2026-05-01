#!/bin/bash

echo "Starting Day 3 Document Parsing..."

# 1. Parse PDFs
python -m src.parse.parse_pdfs --registry corpus/document_registry.csv

# 2. Segment Sections
python -m src.parse.segment_sections --parsed-dir corpus/parsed

# 3. Extract Table Candidates
python -m src.parse.extract_table_candidates --sections corpus/sections/sections.jsonl

# 4. Validate Parse
python -m src.parse.validate_parse

echo "Day 3 process complete. Check docs/day3_parse_report.md"
