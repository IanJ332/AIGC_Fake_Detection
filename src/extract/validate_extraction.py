import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime

def validate_extraction(data_dir):
    data_dir = Path(data_dir)
    extracted_dir = data_dir / "extracted"
    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    entities_path = extracted_dir / "entities.csv"
    results_path = extracted_dir / "result_tuples.csv"
    summary_path = extracted_dir / "paper_entity_summary.csv"
    duckdb_path = data_dir / "index" / "research_corpus.duckdb"
    
    issues = []
    
    # 1. Existence Checks
    if not entities_path.exists(): issues.append("entities.csv missing")
    if not results_path.exists(): issues.append("result_tuples.csv missing")
    if not summary_path.exists(): issues.append("paper_entity_summary.csv missing")
    if not duckdb_path.exists(): issues.append("DuckDB index missing")
    
    if issues:
        print(f"Validation FAILED: {', '.join(issues)}")
        # return # Proceed to generate partial report if possible

    # 2. Threshold Checks
    df_entities = pd.read_csv(entities_path) if entities_path.exists() else pd.DataFrame()
    df_results = pd.read_csv(results_path) if results_path.exists() else pd.DataFrame()
    df_summary = pd.read_csv(summary_path) if summary_path.exists() else pd.DataFrame()
    
    entity_count = len(df_entities)
    result_count = len(df_results)
    papers_with_entities = df_summary[df_summary["entity_count"] > 0]["paper_id"].nunique()
    papers_with_results = df_summary[df_summary["result_tuple_count"] > 0]["paper_id"].nunique()
    
    status = "PROCEED"
    if entity_count < 1000 or result_count < 500:
        status = "CAUTION"
    if papers_with_entities < 50 or papers_with_results < 30:
        status = "CAUTION"
    if entity_count == 0:
        status = "BLOCKED"

    # 3. Top Distributions
    def get_top_20(df, col):
        if df.empty or col not in df.columns: return []
        # Entities are often comma separated in summary, but here we use entities.csv
        return df[col].value_counts().head(20).to_dict()

    # If using entities.csv for distributions
    top_datasets = get_top_20(df_entities[df_entities["entity_type"] == "dataset"], "entity")
    top_models = get_top_20(df_entities[df_entities["entity_type"] == "model_backbone"], "entity")
    top_metrics = get_top_20(df_entities[df_entities["entity_type"] == "metric"], "entity")
    top_generators = get_top_20(df_entities[df_entities["entity_type"] == "generator_family"], "entity")

    # 4. Generate Report
    report_path = reports_dir / "day5_full_extraction_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Day 5 Full Extraction Report\n\n")
        f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Summary\n")
        f.write(f"- **Extraction Status**: {status}\n")
        f.write(f"- **Total Entities Extracted**: {entity_count}\n")
        f.write(f"- **Total Result Tuples Extracted**: {result_count}\n")
        f.write(f"- **Papers with Entities**: {papers_with_entities}\n")
        f.write(f"- **Papers with Results**: {papers_with_results}\n\n")
        
        f.write("## Distributions\n")
        
        def write_dict_table(title, d):
            f.write(f"### {title}\n")
            if not d:
                f.write("No data.\n\n")
                return
            f.write("| Item | Count |\n| :--- | :--- |\n")
            for k, v in d.items():
                f.write(f"| {k} | {v} |\n")
            f.write("\n")
            
        write_dict_table("Top 20 Datasets", top_datasets)
        write_dict_table("Top 20 Models/Backbones", top_models)
        write_dict_table("Top 20 Metrics", top_metrics)
        write_dict_table("Top 20 Generator Families", top_generators)
        
        f.write("## Observations\n")
        if status == "CAUTION":
            f.write("- **WARNING**: Extraction yields are below target thresholds (1000 entities / 500 results).\n")
        elif status == "BLOCKED":
            f.write("- **ERROR**: Critical extraction failure. Zero entities found.\n")
        else:
            f.write("- Pipeline met all success criteria.\n")

    print(f"Validation report saved to {report_path}")
    print(f"Extraction Status: {status}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="/content/drive/MyDrive/AIGC/Data")
    args = parser.parse_args()
    validate_extraction(args.data_dir)
