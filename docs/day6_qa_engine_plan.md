# Day 6: Analytical Synthesis and Multi-Doc QA Engine

This plan outlines the implementation of an operator-based question-answering system designed to synthesize findings across the 100-paper AIGC research corpus.

## Objectives
- Implement a rule-based query router to classify questions into 8 analytical tiers.
- Develop deterministic operators using DuckDB and pandas for reliable, traceable synthesis.
- Ensure every answer is backed by explicit evidence anchors and section snippets.
- Avoid "hallucination-by-design" by using a non-LLM, operator-centric approach.

## Analytical Tiers
1. **Single-Doc**: Detailed lookup for a specific paper (e.g., "What datasets does P003 use?").
2. **Aggregation**: Corpus-wide statistics and rankings (e.g., "What are the top 10 datasets?").
3. **Contradiction**: Identification of potential result disagreements across papers.
4. **Temporal**: Analysis of research trends over time.
5. **Citation Graph**: (Limited) analysis of paper relationships.
6. **Multihop**: Multi-condition filtering (e.g., "Papers using GenImage that also report AUC").
7. **Negation**: Identification of missing evidence or sections.
8. **Quantitative**: Numerical summaries, counts, and averages.

## Component Architecture

### 1. Router (`src/query/router.py`)
Classifies the question into one of the 8 tiers based on keywords, regex patterns, and paper ID detection.

### 2. Operators (`src/query/operators.py`)
The logic engine. Uses SQL (via DuckDB) for complex joins and aggregations, and pandas for fine-grained data manipulation.
- `answer_aggregation`: Uses `COUNT` and `GROUP BY` on `entities.csv`.
- `answer_contradiction`: Analyzes variance in `result_tuples.csv` for same dataset/metric pairs.
- `answer_temporal`: Grouping by `year` from `paper_entity_summary.csv`.

### 3. Evidence (`src/query/evidence.py`)
Retrieves text snippets and formats anchors. Maps `evidence_anchor` from `result_tuples` back to `sections.jsonl`.

### 4. Answer Builder (`src/query/answer_builder.py`)
Standardizes output into a three-part structure:
- **Answer**: The synthesized response.
- **Evidence**: List of paper IDs, titles, and snippets.
- **Limitations**: Explicit statement of what data was missing or ambiguous.

## Verification Plan
- **Manual CLI testing**: Verify that basic questions (e.g., "top datasets") return correct counts.
- **Automated Eval (`eval/run_eval.py`)**: Run 40 questions covering all tiers and audit routing accuracy and operator stability.
- **Evidence Audit**: Ensure every row in `result_tuples.csv` maps back to a valid section in `sections.jsonl`.
