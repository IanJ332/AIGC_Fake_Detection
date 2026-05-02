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
    
    # Load metadata
    meta = None
    if manifest_path.exists(): meta = pd.read_csv(manifest_path)
    elif doc_reg_path.exists(): meta = pd.read_csv(doc_reg_path)
    
    # Load parse status
    parse_status = {}
    if parse_reg_path.exists():
        df_p = pd.read_csv(parse_reg_path)
        parse_status = dict(zip(df_p["paper_id"], df_p["success"]))

    # 1. Section Stats
    print("Building section stats...")
    paper_sections = defaultdict(list)
    with open(sections_path, "r", encoding="utf-8") as f:
        for line in f:
            sect = json.loads(line)
            paper_sections[sect["paper_id"]].append(sect)
            
    section_rows = []
    for pid, sects in tqdm(paper_sections.items()):
        types = [s["section_type"] for s in sects]
        section_rows.append({
            "paper_id": pid,
            "title": df_entities[df_entities["paper_id"] == pid]["paper_title"].iloc[0] if not df_entities[df_entities["paper_id"] == pid].empty else "Unknown",
            "year": df_entities[df_entities["paper_id"] == pid]["year"].iloc[0] if not df_entities[df_entities["paper_id"] == pid].empty else "Unknown",
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
    unique_pids = set(df_sect_stats["paper_id"]).union(set(df_entities["paper_id"]))
    
    for pid in tqdm(unique_pids):
        p_entities = df_entities[df_entities["paper_id"] == pid]
        p_results = df_results[df_results["paper_id"] == pid]
        
        def get_unique_entities(etype):
            return ", ".join(sorted(p_entities[p_entities["entity_type"] == etype]["entity"].unique()))

        entity_summary_rows.append({
            "paper_id": pid,
            "title": p_entities["paper_title"].iloc[0] if not p_entities.empty else "Unknown",
            "year": p_entities["year"].iloc[0] if not p_entities.empty else "Unknown",
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
    if meta is not None:
        for pid in meta["paper_id"]:
            registry_rows.append({
                "paper_id": pid,
                "title": titles.get(pid, "Unknown") if 'titles' in locals() else "Unknown",
                "parsed_available": parse_status.get(pid, False),
                "sections_count": len(paper_sections.get(pid, [])),
                "entity_count": len(df_entities[df_entities["paper_id"] == pid]),
                "result_tuple_count": len(df_results[df_results["paper_id"] == pid]),
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
