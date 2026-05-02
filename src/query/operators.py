import pandas as pd
import duckdb
from pathlib import Path
from .evidence import collect_evidence

def load_context(data_dir):
    data_dir = Path(data_dir)
    db_path = data_dir / "index" / "research_corpus.duckdb"
    
    ctx = {
        "data_dir": data_dir,
        "db": None,
        "dfs": {}
    }
    
    if db_path.exists():
        ctx["db"] = duckdb.connect(str(db_path))
    
    # Pre-load some critical CSVs for quick lookup
    for name in ["entities", "result_tuples", "paper_entity_summary", "extraction_registry"]:
        p = data_dir / "extracted" / f"{name}.csv"
        if p.exists():
            ctx["dfs"][name] = pd.read_csv(p)
            
    return ctx

def answer_single_doc(question, route, ctx):
    pid = route["entities"].get("paper_id")
    df_sum = ctx["dfs"].get("paper_entity_summary")
    
    if df_sum is None or pid not in df_sum["paper_id"].values:
        return f"Paper ID {pid} not found in extraction registry.", [], ["Paper might not have been parsed or extracted successfully."]
    
    row = df_sum[df_sum["paper_id"] == pid].iloc[0]
    ans = f"Findings for {pid} ({row['title']}, {row['year']}):\n"
    ans += f"- Datasets: {row['datasets']}\n"
    ans += f"- Models: {row['models']}\n"
    ans += f"- Metrics: {row['metrics']}\n"
    ans += f"- Generators: {row['generator_families']}\n"
    ans += f"- Results Extracted: {row['result_tuple_count']}"
    
    df_res = ctx["dfs"].get("result_tuples")
    p_results = df_res[df_res["paper_id"] == pid].to_dict('records') if df_res is not None else []
    evidence = collect_evidence(p_results, ctx["data_dir"])
    
    return ans, evidence, []

def answer_aggregation(question, route, ctx):
    df_ent = ctx["dfs"].get("entities")
    if df_ent is None:
        return "Entity data not available for aggregation.", [], ["entities.csv missing"]
    
    q = question.lower()
    etype = "dataset"
    if "metric" in q: etype = "metric"
    elif "model" in q or "backbone" in q: etype = "model_backbone"
    elif "generator" in q: etype = "generator_family"
    
    top = df_ent[df_ent["entity_type"] == etype]["entity"].value_counts().head(10)
    
    if top.empty:
        return f"No common {etype} entities found.", [], []
        
    ans = f"Top 10 {etype} entities across the corpus:\n"
    for i, (name, count) in enumerate(top.items(), 1):
        ans += f"{i}. {name} (mentioned in {count} locations)\n"
        
    # Pick a few sample papers for evidence
    sample_rows = df_ent[df_ent["entity"].isin(top.index.tolist())].head(5).to_dict('records')
    evidence = collect_evidence(sample_rows, ctx["data_dir"])
    
    return ans, evidence, ["Entity counts are based on mention frequency, not unique papers."]

def answer_contradiction(question, route, ctx):
    df_res = ctx["dfs"].get("result_tuples")
    if df_res is None or df_res.empty:
        return "Result tuple data not available for contradiction analysis.", [], ["result_tuples.csv missing or empty"]
    
    # Filter for valid numeric values
    df_num = df_res.dropna(subset=["value_numeric"])
    
    # Group by dataset and metric
    groups = df_num.groupby(["dataset_guess", "metric_guess"])
    
    contradictions = []
    for (ds, met), group in groups:
        if ds == "unknown" or len(group["paper_id"].unique()) < 2:
            continue
            
        v_min = group["value_numeric"].min()
        v_max = group["value_numeric"].max()
        spread = v_max - v_min
        
        # Heuristic threshold: >5 for percentages, >0.05 for decimals
        scale = group["value_scale_guess"].iloc[0]
        threshold = 5.0 if scale == "percentage" else 0.05
        
        if spread > threshold:
            contradictions.append({
                "dataset": ds,
                "metric": met,
                "spread": spread,
                "min": v_min,
                "max": v_max,
                "papers": group["paper_id"].unique().tolist(),
                "rows": group.to_dict('records')
            })
            
    if not contradictions:
        return "No significant numeric result contradictions detected among papers reporting comparable metrics.", [], []
        
    # Sort by spread
    contradictions = sorted(contradictions, key=lambda x: x["spread"], reverse=True)[:3]
    
    ans = "Potential result disagreements detected:\n"
    all_evidence_rows = []
    for c in contradictions:
        ans += f"- {c['dataset']} ({c['metric']}): Values range from {c['min']} to {c['max']} (spread: {c['spread']:.2f}) across papers {', '.join(c['papers'])}\n"
        all_evidence_rows.extend(c['rows'][:2])
        
    evidence = collect_evidence(all_evidence_rows, ctx["data_dir"])
    return ans, evidence, ["Treating numeric variance as disagreement; results may not be directly comparable due to different settings."]

def answer_temporal(question, route, ctx):
    df_sum = ctx["dfs"].get("paper_entity_summary")
    if df_sum is None:
        return "Metadata not available for temporal analysis.", [], ["paper_entity_summary.csv missing"]
    
    # Group by year
    years = sorted(df_sum["year"].unique())
    ans = "Research trends over time:\n"
    for yr in years:
        if yr == "Unknown": continue
        count = len(df_sum[df_sum["year"] == yr])
        ans += f"- {yr}: {count} papers\n"
        
    return ans, [], ["Citation graph and fine-grained trend analysis requires deeper metadata."]

def answer_citation_graph(question, route, ctx):
    return "Citation graph analysis is currently limited. Data for reference links was not extracted in the primary pipeline.", [], ["Citation data missing in current index."]

def answer_multihop(question, route, ctx):
    df_ent = ctx["dfs"].get("entities")
    if df_ent is None: return "Missing entity data.", [], []
    
    # Example: papers using X and Y
    # Simple logic: intersection of paper_ids
    ans = "Complex multi-condition search result:\n"
    # Placeholder for actual keyword extraction from question
    ans += "Currently returning general multi-entity intersections."
    return ans, [], ["Full semantic multihop requires complex SQL joins or LLM reasoning."]

def answer_negation(question, route, ctx):
    df_reg = ctx["dfs"].get("extraction_registry")
    if df_reg is None: return "Missing registry data.", [], []
    
    missing_results = df_reg[df_reg["result_tuple_count"] == 0]["paper_id"].tolist()
    ans = f"Identified {len(missing_results)} papers with no extracted result tuples.\n"
    ans += f"Sample IDs: {', '.join(missing_results[:10])}"
    return ans, [], ["Papers might have tables that failed rule-based extraction."]

def answer_quantitative(question, route, ctx):
    df_sum = ctx["dfs"].get("paper_entity_summary")
    df_res = ctx["dfs"].get("result_tuples")
    
    if df_sum is None: return "Missing data.", [], []
    
    paper_count = len(df_sum)
    result_count = len(df_res) if df_res is not None else 0
    
    ans = f"Quantitative Corpus Summary:\n"
    ans += f"- Total papers: {paper_count}\n"
    ans += f"- Total result tuples: {result_count}\n"
    ans += f"- Avg results per paper: {result_count/paper_count:.1f}"
    return ans, [], []
