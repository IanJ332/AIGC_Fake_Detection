import os
import json
import pandas as pd
from pathlib import Path
import argparse

def get_dir_stats(dir_path):
    if not dir_path.exists():
        return {"exists": False, "file_count": 0, "total_size_mb": 0.0, "top_files": [], "extensions": []}
    
    files = []
    for f in dir_path.rglob("*"):
        if f.is_file():
            files.append(f)
            
    file_count = len(files)
    total_size_bytes = sum(f.stat().st_size for f in files)
    total_size_mb = total_size_bytes / (1024 * 1024)
    
    top_files = sorted(files, key=lambda x: x.stat().st_size, reverse=True)[:10]
    top_files_info = [{"name": f.name, "size_mb": f.stat().st_size / (1024 * 1024)} for f in top_files]
    
    extensions = list(set(f.suffix for f in files))
    
    return {
        "exists": True,
        "file_count": file_count,
        "total_size_mb": total_size_mb,
        "top_files": top_files_info,
        "extensions": extensions
    }

def audit_data(data_dir):
    data_dir = Path(data_dir)
    subfolders = [
        "checkpoints", "download_logs", "extracted", "index", 
        "parse_logs", "parsed", "pdfs", "probes", "registry", 
        "reports", "sections", "tables", "tei_xml"
    ]
    
    inventory = {}
    for folder in subfolders:
        inventory[folder] = get_dir_stats(data_dir / folder)
        
    # Critical Artifacts
    critical_artifacts = [
        "registry/manifest_100.csv",
        "registry/document_registry.csv",
        "registry/parse_registry.csv",
        "extracted/entities.csv",
        "extracted/result_tuples.csv",
        "extracted/paper_entity_summary.csv",
        "extracted/paper_section_stats.csv",
        "extracted/extraction_registry.csv",
        "index/research_corpus.duckdb",
        "sections/sections.jsonl",
        "tables/table_candidates.jsonl",
        "reports/day5_full_extraction_report.md"
    ]
    
    artifact_status = {}
    for art in critical_artifacts:
        art_path = data_dir / art
        artifact_status[art] = {
            "exists": art_path.exists(),
            "size_mb": art_path.stat().st_size / (1024 * 1024) if art_path.exists() else 0.0
        }
        
    # Data Stats
    stats = {}
    
    # CSV row counts
    csvs = ["entities.csv", "result_tuples.csv", "paper_entity_summary.csv", "paper_section_stats.csv", "extraction_registry.csv"]
    for csv in csvs:
        csv_path = data_dir / "extracted" / csv
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                stats[csv] = len(df)
                if csv == "entities.csv":
                    stats["entity_types"] = df["entity_type"].value_counts().head(20).to_dict()
                    for etype in ["dataset", "model_backbone", "metric", "generator_family"]:
                        stats[f"top_{etype}"] = df[df["entity_type"] == etype]["entity"].value_counts().head(20).to_dict()
            except Exception as e:
                stats[csv] = f"Error: {e}"
        else:
            stats[csv] = "Missing"
            
    # PDF and JSON counts
    stats["pdf_count"] = inventory["pdfs"]["file_count"]
    stats["parsed_json_count"] = inventory["parsed"]["file_count"]
    
    return {
        "inventory": inventory,
        "artifact_status": artifact_status,
        "stats": stats,
        "total_size_mb": sum(f["total_size_mb"] for f in inventory.values())
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="Data")
    args = parser.parse_args()
    
    results = audit_data(args.data_dir)
    
    # Write JSON
    with open("LOCAL_DATA_INVENTORY.json", "w") as f:
        json.dump(results, f, indent=2)
        
    # Write Markdown
    with open("LOCAL_DATA_INVENTORY.md", "w") as f:
        f.write("# Local Data Inventory Report\n\n")
        f.write(f"**Total Data Size**: {results['total_size_mb']:.2f} MB\n\n")
        
        f.write("## Folder Inventory\n\n")
        f.write("| Folder | Exists | Files | Size (MB) | Extensions |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for folder, info in results["inventory"].items():
            exts = ", ".join(info["extensions"])
            f.write(f"| {folder} | {info['exists']} | {info['file_count']} | {info['total_size_mb']:.2f} | {exts} |\n")
            
        f.write("\n## Critical Artifact Status\n\n")
        f.write("| Artifact | Exists | Size (MB) |\n")
        f.write("| :--- | :--- | :--- |\n")
        for art, info in results["artifact_status"].items():
            f.write(f"| {art} | {info['exists']} | {info['size_mb']:.2f} |\n")
            
        f.write("\n## Row-Count Statistics\n\n")
        for k, v in results["stats"].items():
            if isinstance(v, dict):
                f.write(f"\n### {k}\n\n")
                f.write("| Key | Count |\n| :--- | :--- |\n")
                for sub_k, sub_v in v.items():
                    f.write(f"| {sub_k} | {sub_v} |\n")
            else:
                f.write(f"- **{k}**: {v}\n")
                
        f.write("\n## Git Ignore / Tracking Risk\n\n")
        f.write("> [!IMPORTANT]\n")
        f.write("> Run the following commands to verify tracking risk:\n")
        f.write("```bash\n")
        f.write("git check-ignore -v Data/\n")
        f.write("git ls-files | findstr /R \"Data/ .pdf$ .duckdb$ sections.jsonl table_candidates.jsonl extracted/.*.csv\"\n")
        f.write("```\n\n")
        
        f.write("## Recommended Retention Plan\n\n")
        f.write("- **registry/**: Keep for demo (critical metadata).\n")
        f.write("- **extracted/**: Keep for full reproducibility (QA baseline).\n")
        f.write("- **index/**: Keep for demo (runtime speed).\n")
        f.write("- **pdfs/** & **parsed/**: Safe to delete after backup (large source files).\n")
        f.write("- **GitHub Policy**: NEVER commit the `Data/` directory or its contents to the remote repository.\n")

if __name__ == "__main__":
    main()
