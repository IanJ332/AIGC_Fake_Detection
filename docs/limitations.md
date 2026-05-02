# Project Limitations and Scope

This document outlines the known constraints and design boundaries of the Analytical QA Engine.

## Data and Coverage

- **PDF Access Restrictions**: Only 72 out of 100 target papers were successfully parsed. 28% of papers returned HTTP 403 Forbidden errors or lacked open-access fallbacks, limiting the total corpus size.
- **Citation Graph**: The system currently lacks a full citation graph. References were not extracted as a primary entity type, limiting the engine's ability to navigate cross-doc "Influenced-By" relationships.
- **Paper Identification**: Metadata synthesis (P001-P100) is based on row order in the `manifest_100.csv`. Discrepancies in the initial CSV ordering could lead to mislabeled IDs if the manifest is re-sorted.

## Analytical Depth

- **Heuristic Extractions**: Result tuples and entity occurrences are extracted via rule-based heuristics. They represent "candidate claims" rather than manually verified ground truth.
- **Noisy Evidence**: The evidence extraction logic may occasionally include noisy snippets (e.g., table fragments or multi-column layout artifacts) due to the nature of automated PDF-to-Markdown conversion.
- **Deduplication**: Entity deduplication is string-based. Semantic aliases (e.g., "ResNet50" vs. "ResNet-50") may be counted as distinct entities unless mapped in a normalization layer.

## Design Philosophy

- **No Fine-Tuning**: By design, no models were fine-tuned for this task. The system relies on deterministic logic to ensure maximum auditability.
- **No Image Detection**: This repository is focused on **Research Comprehension** (analyzing papers about AIGC detection). It does not contain code for training image classifiers or performing inference on image files.
- **Operator-Based**: The QA system is operator-constrained. Questions that fall outside the defined tiers (Single-Doc, Aggregation, Contradiction, etc.) will be correctly routed to "Unknown" rather than hallucinated.
