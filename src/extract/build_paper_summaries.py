import pandas as pd
import json
import argparse
from pathlib import Path
from tqdm import tqdm
from collections import defaultdict

def build_paper_summaries(data_dir):
    data_dir = Path(data_dir)
    extracted_dir = data_dir / "extracted"
    registry_dir = data_dir / "registry"
    sections_path = data_dir / "sections" / "sections.jsonl"
    entities_path = extracted_dir / "entities.csv"
    results_path = extracted_dir / "result_tuples.csv"
    
    manifest_path = registry_dir / "manifest_100.csv"
    doc_reg_path = registry_dir / "document_registry.csv"
    parse_reg_path = registry_dir / "parse_registry.csv"
    
    if not extracted_dir.exists():
        print(f"Error: {extracted_dir} not found.")
        return

    # Load entities and results
    df_entities = pd.read_csv(entities_path) if entities_path.exists() else pd.DataFrame()
    df_results = pd.read_csv(results_path) if results_path.exists() else pd.DataFrame()
    
    # Metadata
    meta = None
    if manifest_path.exists(): meta = pd.read_csv(manifest_path)
    elif doc_reg_path.exists(): meta = pd.read_csv(doc_reg_path)
    
    titles = {}
    years = {}
    if meta is not None:
        if "paper_id" in meta.columns:
            if "title" in meta.columns:
                titles = dict(zip(meta["paper_id"], meta["title"]))
            if "year" in meta.columns:
                years = dict(zip(meta["paper_id"], meta["year"]))
            elif "publish_year" in meta.columns:
                years = dict(zip(meta["paper_id"], meta["publish_year"]))

    # Load parse status
    parse_status = {}
    if parse_reg_path.exists():
        df_p = pd.read_csv(parse_reg_path)
        status_col = None
        for c in ["success", "parsed_success", "parse_success", "pdf_parsed", "status"]:
            if c in df_p.columns:
                status_col = c
                break

        if "paper_id" in df_p.columns and status_col:
            if status_col == "status":
                parse_status = dict(zip(df_p["paper_id"], df_p[status_col].astype(str).str.lower().isin(["success", "parsed", "complete", "true"])))
            else:
                parse_status = dict(zip(df_p["paper_id"], df_p[status_col].fillna(False).astype(bool)))
        elif "paper_id" in df_p.columns:
            parse_status = {pid: True for pid in df_p["paper_id"]}

    # 1. Section Stats
    print("Building section stats...")
    paper_sections = defaultdict(list)
    if sections_path.exists():
        with open(sections_path, "r", encoding="utf-8") as f:
            for line in f:
                sect = json.loads(line)
                paper_sections[sect["paper_id"]].append(sect)
            
    section_rows = []
    for pid, sects in tqdm(paper_sections.items()):
        types = [s["section_type"] for s in sects]
        section_rows.append({
            "paper_id": pid,
            "title": titles.get(pid, "Unknown"),
            "year": years.get(pid, "Unknown"),
            "total_sections": len(sects),
            "total_chars": sum(len(s["text"]) for s in sects),
            "has_abstract": "abstract" in types,
            "has_intro": "introduction" in types,
            "has_method": "method" in types,
            "has_experiment": "experiment" in types,
            "has_results": "results" in types,
            "has_limitations": "limitation" in types,
            "unknown_section_count": types.count("unknown")
        })
    df_sect_stats = pd.DataFrame(section_rows)
    df_sect_stats.to_csv(extracted_dir / "paper_section_stats.csv", index=False)

    # 2. Entity Summary
    print("Building entity summary...")
    entity_summary_rows = []
    unique_pids = set(df_sect_stats["paper_id"] if not df_sect_stats.empty else []).union(set(df_entities["paper_id"] if not df_entities.empty else []))
    
    for pid in tqdm(unique_pids):
        p_entities = df_entities[df_entities["paper_id"] == pid] if not df_entities.empty else pd.DataFrame()
        p_results = df_results[df_results["paper_id"] == pid] if not df_results.empty else pd.DataFrame()
        
        def get_unique_entities(etype):
            if p_entities.empty: return ""
            return ", ".join(sorted(p_entities[p_entities["entity_type"] == etype]["entity"].unique()))

        entity_summary_rows.append({
            "paper_id": pid,
            "title": titles.get(pid, "Unknown"),
            "year": years.get(pid, "Unknown"),
            "datasets": get_unique_entities("dataset"),
            "models": get_unique_entities("model_backbone"),
            "generator_families": get_unique_entities("generator_family"),
            "metrics": get_unique_entities("metric"),
            "distortions": get_unique_entities("distortion"),
            "robustness_conditions": get_unique_entities("robustness_condition"),
            "method_keywords": get_unique_entities("method_keyword"),
            "entity_count": len(p_entities),
            "result_tuple_count": len(p_results)
        })
    df_entity_summary = pd.DataFrame(entity_summary_rows)
    df_entity_summary.to_csv(extracted_dir / "paper_entity_summary.csv", index=False)

    # 3. Extraction Registry
    print("Building extraction registry...")
    registry_rows = []
    
    if meta is not None and "paper_id" in meta.columns:
        registry_pids = list(meta["paper_id"].astype(str))
    else:
        registry_pids = sorted(unique_pids)

    for pid in registry_pids:
        registry_rows.append({
            "paper_id": pid,
            "title": titles.get(pid, "Unknown"),
            "parsed_available": parse_status.get(pid, False),
            "sections_count": len(paper_sections.get(pid, [])),
            "entity_count": len(df_entities[df_entities["paper_id"] == pid]) if not df_entities.empty else 0,
            "result_tuple_count": len(df_results[df_results["paper_id"] == pid]) if not df_results.empty else 0,
            "extraction_status": "complete" if pid in unique_pids else "pending",
            "warnings": ""
        })
    df_ext_reg = pd.DataFrame(registry_rows)
    df_ext_reg.to_csv(extracted_dir / "extraction_registry.csv", index=False)

    print("Summarization complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="/content/drive/MyDrive/AIGC/Data")
    args = parser.parse_args()
    build_paper_summaries(args.data_dir)
