# Final Demo Questions

This document provides a set of sample questions categorized by their analytical tier, along with the CLI commands to execute them.

## 1. Single-Doc (Fact Retrieval)
**Question**: "What does paper P001 propose?"
```bash
python -m src.query.cli --data-dir ./Data --question "What does paper P001 propose?"
```

## 2. Aggregation (Corpus Trends)
**Question**: "What are the top 10 datasets mentioned across the corpus?"
```bash
python -m src.query.cli --data-dir ./Data --question "What are the top 10 datasets mentioned across the corpus?"
```

## 3. Contradiction (Result Variance)
**Question**: "Are there any conflicting results for the Accuracy metric on the CelebA dataset?"
```bash
python -m src.query.cli --data-dir ./Data --question "Are there any conflicting results for the Accuracy metric on the CelebA dataset?"
```

## 4. Temporal (Chronological Analysis)
**Question**: "How has the volume of papers changed between 2021 and 2024?"
```bash
python -m src.query.cli --data-dir ./Data --question "How has the volume of papers changed between 2021 and 2024?"
```

## 5. Quantitative (Corpus Stats)
**Question**: "What is the average number of results reported per paper?"
```bash
python -m src.query.cli --data-dir ./Data --question "What is the average number of results reported per paper?"
```

## 6. Negation (Gap Analysis)
**Question**: "Which papers do not mention any specific generator families?"
```bash
python -m src.query.cli --data-dir ./Data --question "Which papers do not mention any specific generator families?"
```

## 7. Multihop (Complex Search)
**Question**: "Find papers that use both the CLIP model and the Accuracy metric."
```bash
python -m src.query.cli --data-dir ./Data --question "Find papers that use both the CLIP model and the Accuracy metric."
```

## 8. Unknown (Out of Scope)
**Question**: "Who is the lead author of paper P001?"
```bash
# This will be routed to 'unknown' as author metadata was not a primary extraction target.
python -m src.query.cli --data-dir ./Data --question "Who is the lead author of paper P001?"
```
