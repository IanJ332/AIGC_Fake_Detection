# Quality vs. Budget Analysis

This document explores the performance trade-offs of the current deterministic system versus potential higher-budget LLM-integrated architectures.

## Current Performance (Measured)

The following metrics were recorded during the Day 6 evaluation of the 40-question gold set:

- **Corpus Size**: 72 papers (extracted).
- **Routing Accuracy**: 92.5% (37/40).
- **Operator Execution Success**: 100% (40/40).
- **Unknown Tier Count**: 0.
- **Answers with Limitations**: 100% (40/40) - providing explicit constraints for every answer.
- **Answers with Evidence**: ~52.5% (21/40) - strictly verifiable snippets.

## Budget Tiers & Planned Ablations

### Level 1: $0 Rule-Only (Current)
- **Architecture**: DuckDB + Pandas + Heuristic Regex.
- **Pros**: Zero cost, zero hallucination, extremely fast, 100% auditable.
- **Cons**: Limited semantic understanding; fails on complex multi-doc reasoning that requires cross-referencing un-indexed text.

### Level 2: $5 Embedding Reranking (Planned Ablation)
- **Proposed Enhancement**: Generate 1536-d embeddings for all sections using `text-embedding-3-small`.
- **Expected Benefit**: Improve evidence coverage from 52% to >80% by replacing keyword-based snippet matching with semantic similarity.
- **Estimated Cost**: <$1.00 for 100 papers; remaining budget for high-volume QA sessions.

### Level 3: $20 LLM Selective Synthesis (Planned Ablation)
- **Proposed Enhancement**: Route complex "Multihop" or conflicting queries to GPT-4o-mini with retrieved context.
- **Expected Benefit**: Improve synthesis quality for complex multihop questions and reduce unsupported-answer risk when paired with retrieved evidence.
- **Estimated Cost**: ~$0.01 per query; $20 supports thousands of high-fidelity analytical sessions.

## Conclusion

The current $0 implementation provides a robust foundation for high-fidelity research comprehension. While semantic nuances are sacrificed for determinism, the system remains a highly reliable "Numbers-First" auditor for the AIGC detection corpus.
