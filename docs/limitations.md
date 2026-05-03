# Project Limitations and Scope

This document outlines the known constraints and design boundaries of the Analytical QA Engine.

## Data and Coverage

- **PDF Access Restrictions**: The final corpus achieves 117 successfully parsed papers. While the system successfully backfills paywalled documents with Open Access candidates, total scale is ultimately bounded by the availability of high-quality OA papers.
- **Citation Graph**: The system implements citation graph features via OpenAlex metadata mapping, but complex internal self-citations depend on extracted string matching.
- **Paper Identification**: Candidate papers use dynamic ID generation (Cxxx) to avoid overlapping with seed IDs (Pxxx), requiring accurate metadata normalization downstream.

## Analytical Depth

- **Heuristic Extractions**: Result tuples and entity occurrences are extracted via rule-based heuristics. They represent "candidate claims" rather than manually verified ground truth.
- **Noisy Evidence**: The evidence extraction logic may occasionally include noisy snippets (e.g., table fragments or multi-column layout artifacts) due to the nature of automated PDF-to-Markdown conversion.
- **Deduplication**: Entity deduplication is string-based. Semantic aliases (e.g., "ResNet50" vs. "ResNet-50") may be counted as distinct entities unless mapped in a normalization layer.

## Design Philosophy

- **No Fine-Tuning**: By design, no models were fine-tuned for this task. The system relies on deterministic logic to ensure maximum auditability.
- **No Image Detection**: This repository is focused on **Research Comprehension** (analyzing papers about AIGC detection). It does not contain code for training image classifiers or performing inference on image files.
- **Operator-Based**: The QA system is operator-constrained. Questions that fall outside the defined tiers (Single-Doc, Aggregation, Contradiction, etc.) will be correctly routed to "Unknown" rather than hallucinated.
