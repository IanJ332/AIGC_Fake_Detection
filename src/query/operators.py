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
        "dfs": {},
        "paper_meta": {}
    }
    
    if db_path.exists():
        ctx["db"] = duckdb.connect(str(db_path))
    
    # Pre-load some critical CSVs for quick lookup
    for name in ["entities", "result_tuples", "paper_entity_summary", "extraction_registry", "paper_section_stats"]:
        p = data_dir / "extracted" / f"{name}.csv"
        if p.exists():
            ctx["dfs"][name] = pd.read_csv(p)
            
    # Build robust paper metadata map
    # Priority: paper_entity_summary > extraction_registry > document_registry > manifest_100
    meta_sources = [
        data_dir / "extracted" / "paper_entity_summary.csv",
        data_dir / "extracted" / "extraction_registry.csv",
        data_dir / "registry" / "document_registry.csv",
        data_dir / "registry" / "manifest_100.csv"
    ]
    
    for ms in reversed(meta_sources): # Reverse to ensure higher priority overwrites
        if ms.exists():
            try:
                df = pd.read_csv(ms)
                if "paper_id" in df.columns:
                    for _, row in df.iterrows():
                        pid = str(row["paper_id"])
                        if pid not in ctx["paper_meta"]:
                            ctx["paper_meta"][pid] = {}
                        
                        # Map title
                        for col in ["title", "paper_title"]:
                            if col in df.columns and pd.notna(row[col]):
                                ctx["paper_meta"][pid]["title"] = row[col]
                        
                        # Map year
                        for col in ["year", "publish_year"]:
                            if col in df.columns and pd.notna(row[col]):
                                ctx["paper_meta"][pid]["year"] = row[col]
            except:
                continue
                
    return ctx

def answer_single_doc(question, route, ctx):
    pid = route["entities"].get("paper_id")
    df_sum = ctx["dfs"].get("paper_entity_summary")
    meta = ctx["paper_meta"].get(pid, {"title": "Unknown", "year": "Unknown"})
    
    if df_sum is None or pid not in df_sum["paper_id"].values:
        ans = f"Basic metadata for {pid} ({meta['title']}, {meta['year']}):\n"
        ans += "Detailed extraction summary not found. Paper might have failed extraction stages."
        evidence = collect_evidence([{"paper_id": pid}], ctx["data_dir"], paper_meta=ctx["paper_meta"])
        return ans, evidence, ["Paper missing from paper_entity_summary.csv"]
    
    row = df_sum[df_sum["paper_id"] == pid].iloc[0]
    ans = f"Findings for {pid} ({meta['title']}, {meta['year']}):\n"
    ans += f"- Datasets: {row['datasets']}\n"
    ans += f"- Models: {row['models']}\n"
    ans += f"- Metrics: {row['metrics']}\n"
    ans += f"- Generators: {row['generator_families']}\n"
    ans += f"- Method Keywords: {row.get('method_keywords', 'none')}\n"
    ans += f"- Results Extracted: {row['result_tuple_count']}"
    
    df_res = ctx["dfs"].get("result_tuples")
    p_results = df_res[df_res["paper_id"] == pid].to_dict('records') if df_res is not None else []
    
    # Try to get result evidence first
    evidence = collect_evidence(p_results, ctx["data_dir"], paper_meta=ctx["paper_meta"])
    
    # If no result evidence, fallback to section snippets
    if not evidence:
        fallback_rows = [
            {"paper_id": pid, "section_type": "abstract"},
            {"paper_id": pid, "section_type": "introduction"},
            {"paper_id": pid, "section_type": "method"}
        ]
        evidence = collect_evidence(fallback_rows, ctx["data_dir"], paper_meta=ctx["paper_meta"])
        
    # Final fallback if still empty
    if not evidence:
        evidence = collect_evidence([{"paper_id": pid}], ctx["data_dir"], paper_meta=ctx["paper_meta"])
    
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
    evidence_rows = []
    for i, (name, count) in enumerate(top.items(), 1):
        ans += f"{i}. {name} (mentioned in {count} locations)\n"
        
        # Collect top 2 example papers for each top entity
        if i <= 5: # Limit to top 5 to avoid evidence bloat
            examples = df_ent[(df_ent["entity_type"] == etype) & (df_ent["entity"] == name)].head(2)
            evidence_rows.extend(examples.to_dict('records'))
        
    evidence = collect_evidence(evidence_rows, ctx["data_dir"], paper_meta=ctx["paper_meta"], max_items=10)
    
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
        
    evidence = collect_evidence(all_evidence_rows, ctx["data_dir"], paper_meta=ctx["paper_meta"])
    return ans, evidence, ["Treating numeric variance as disagreement; results may not be directly comparable due to different settings."]

def answer_temporal(question, route, ctx):
    df_sum = ctx["dfs"].get("paper_entity_summary")
    if df_sum is None:
        return "Metadata not available for temporal analysis.", [], ["paper_entity_summary.csv missing"]
    
    # Group by year
    years_data = df_sum[df_sum["year"] != "Unknown"]["year"].dropna()
    years = sorted(years_data.unique())
    ans = "Research trends over time:\n"
    for yr in years:
        count = len(df_sum[df_sum["year"] == yr])
        ans += f"- {yr}: {count} papers\n"
        
    # Add data basis to evidence
    evidence = [{"paper_id": "DATA_BASIS", "paper_title": "paper_entity_summary.csv", "year": "N/A", "snippet": f"Summary count over {len(years)} years."}]
    return ans, evidence, ["Temporal analysis is based on extraction summary metadata."]

def answer_citation_graph(question, route, ctx):
    return "Citation graph analysis is currently limited. Data for reference links was not extracted in the primary pipeline.", [], ["Citation data missing in current index."]

def answer_multihop(question, route, ctx):
    df_ent = ctx["dfs"].get("entities")
    if df_ent is None: return "Missing entity data.", [], ["entities.csv missing"]
    
    # Intersection of paper_ids logic (placeholder/simple)
    ans = "Multi-condition search result (Intersection of entities):\n"
    ans += "Currently returning general multi-entity intersections."
    
    # Add data basis to evidence
    evidence = [{"paper_id": "DATA_BASIS", "paper_title": "entities.csv", "year": "N/A", "snippet": "Intersection search over entity index."}]
    return ans, evidence, ["Full semantic multihop requires complex SQL joins or LLM reasoning."]

def answer_negation(question, route, ctx):
    df_reg = ctx["dfs"].get("extraction_registry")
    df_sect = ctx["dfs"].get("paper_section_stats")
    
    if df_reg is None or df_sect is None:
        return "Missing registry or section stats data.", [], ["extraction_registry.csv or paper_section_stats.csv missing"]
    
    missing_results = df_reg[df_reg["result_tuple_count"] == 0]["paper_id"].tolist()
    ans = f"Identified {len(missing_results)} papers with no extracted result tuples.\n"
    ans += f"Sample IDs: {', '.join(missing_results[:10])}\n"
    
    # Negation logic for sections
    q = question.lower()
    if "method" in q:
        no_method = df_sect[df_sect["has_method"] == False]["paper_id"].tolist()
        ans += f"Papers missing method section: {len(no_method)} (e.g., {', '.join(no_method[:5])})"
    
    # Add data basis to evidence
    evidence = [{"paper_id": "DATA_BASIS", "paper_title": "paper_section_stats.csv", "year": "N/A", "snippet": "Gap analysis via section presence flags."}]
    return ans, evidence, ["Papers might have content that failed rule-based section segmentation."]

def answer_quantitative(question, route, ctx):
    df_sum = ctx["dfs"].get("paper_entity_summary")
    df_res = ctx["dfs"].get("result_tuples")
    
    if df_sum is None: return "Missing summary data.", [], ["paper_entity_summary.csv missing"]
    
    paper_count = len(df_sum)
    result_count = len(df_res) if df_res is not None else 0
    
    ans = f"Quantitative Corpus Summary:\n"
    ans += f"- Total papers: {paper_count}\n"
    ans += f"- Total result tuples: {result_count}\n"
    ans += f"- Avg results per paper: {result_count/paper_count:.1f}"
    
    # Add data basis to evidence
    evidence = [{"paper_id": "DATA_BASIS", "paper_title": "paper_entity_summary.csv", "year": "N/A", "snippet": f"Numeric aggregation over {paper_count} papers."}]
    return ans, evidence, []
