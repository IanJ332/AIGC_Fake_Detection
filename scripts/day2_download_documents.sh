#!/bin/bash

echo "Starting Day 2 Document Acquisition..."

# 1. Download documents
python -m src.acquire.download_documents --manifest corpus/manifest_100.csv

# 2. Validate documents
python -m src.acquire.validate_documents --registry corpus/document_registry.csv

echo "Day 2 process complete. Check docs/day2_status.md"
