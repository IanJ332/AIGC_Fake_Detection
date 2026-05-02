import re

def classify_question(question: str) -> dict:
    q = question.lower().strip()
    
    # 1. Single-doc: Detect P### pattern (Highest priority)
    pid_match = re.search(r"\b(p\d{3})\b", q)
    if pid_match:
        return {
            "tier": "single_doc",
            "intent": "paper_lookup",
            "entities": {"paper_id": pid_match.group(1).upper()},
            "confidence": 0.95
        }

    # 2. Contradiction: conflict, disagree, contradict, vs, comparison
    if any(k in q for k in ["conflict", "disagree", "contradict", "discrepancy", "sota claim", "disagreement", "variation in", "inconsistency", "compare"]) or ("different" in q and "result" in q):
        return {
            "tier": "contradiction",
            "intent": "result_variance",
            "entities": {},
            "confidence": 0.8
        }

    # 3. Temporal: over time, evolved, history, trend, timeline, 202x, when
    if any(k in q for k in ["over time", "evolved", "chronologically", "timeline", "trend", "year", "history", "when", "evolution"]) or re.search(r"\b20\d{2}\b", q):
        return {
            "tier": "temporal",
            "intent": "trend_analysis",
            "entities": {},
            "confidence": 0.85
        }

    # 4. Citation Graph: cited by, references, builds on, based on, etc.
    if any(k in q for k in [
        "cited by", "cites", "cite ", "cite?", " cite", " cited", "citation", 
        "references", "reference", "referenced", "build on", "builds on", "built on",
        "based on", "follow-up", "influential", "pioneering", "citation graph", "influenced by"
    ]):
        return {
            "tier": "citation_graph",
            "intent": "relationship_lookup",
            "entities": {},
            "confidence": 0.85
        }

    # 5. Quantitative: how many, sum, median, average, count, total
    if any(k in q for k in ["how many", "sum", "median", "average", "avg", "total", "count", "percentage", "yield", "mean"]):
        return {
            "tier": "quantitative",
            "intent": "numerical_summary",
            "entities": {},
            "confidence": 0.8
        }

    # 6. Negation: lack, missing, absent, without, "do not"
    if any(k in q for k in ["lack", "missing", "absent", "without", "no ", "don't ", "do not", "never", "not mention"]):
        return {
            "tier": "negation",
            "intent": "gap_analysis",
            "entities": {},
            "confidence": 0.75
        }

    # 7. Multihop: complex filtering (AND logic)
    if " and " in q or " also " in q or " using " in q or "find papers" in q or "impact of" in q:
        return {
            "tier": "multihop",
            "intent": "complex_filter",
            "entities": {},
            "confidence": 0.6
        }

    # 8. Aggregation: list, top, most common, every, etc. (Low priority fallback)
    if any(k in q for k in ["most common", "top", "list every", "which metric", "which dataset", "popular", "frequently", "summary of all", "which papers", "what papers", "distribution of"]):
        return {
            "tier": "aggregation",
            "intent": "corpus_stats",
            "entities": {},
            "confidence": 0.8
        }

    return {
        "tier": "unknown",
        "intent": "general_query",
        "entities": {},
        "confidence": 0.4
    }
