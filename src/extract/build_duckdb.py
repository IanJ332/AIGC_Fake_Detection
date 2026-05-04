import pandas as pd
import argparse
from pathlib import Path
import json

def build_duckdb(data_dir):
    try:
        import duckdb
    except ImportError:
        print("DuckDB not installed. Run 'pip install duckdb'.")
        return

    data_dir = Path(data_dir)
    extracted_dir = data_dir / "extracted"
    index_dir = data_dir / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    
    db_path = index_dir / "research_corpus.duckdb"
    print(f"Building DuckDB index at {db_path}...")
    
    con = duckdb.connect(str(db_path))
    
    # Tables to import
    tables = {
        "entities": extracted_dir / "entities.csv",
        "result_tuples": extracted_dir / "result_tuples.csv",
        "paper_section_stats": extracted_dir / "paper_section_stats.csv",
        "paper_entity_summary": extracted_dir / "paper_entity_summary.csv",
        "extraction_registry": extracted_dir / "extraction_registry.csv",
        "numeric_claims": extracted_dir / "numeric_claims.csv"
    }
    
    # Registry and Manifest
    registry_path = data_dir / "registry" / "document_registry.csv"
    manifest_path = data_dir / "registry" / "manifest_100.csv"
    if registry_path.exists(): tables["papers"] = registry_path
    elif manifest_path.exists(): tables["papers"] = manifest_path

    for table_name, csv_path in tables.items():
        if csv_path.exists():
            print(f"  Importing {table_name}...")
            # Drop if exists
            con.execute(f"DROP TABLE IF EXISTS {table_name}")
            # Import from CSV
            con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto('{csv_path}')")
        else:
            print(f"  Skipping {table_name} (File not found)")

    # Special handling for JSONL sections if needed for complex SQL
    sections_jsonl = data_dir / "sections" / "sections.jsonl"
    if sections_jsonl.exists():
        print("  Importing sections (JSONL)...")
        con.execute("DROP TABLE IF EXISTS sections")
        con.execute(f"CREATE TABLE sections AS SELECT * FROM read_json_auto('{sections_jsonl}')")

    con.close()
    print("DuckDB indexing complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="/content/drive/MyDrive/AIGC/Data")
    args = parser.parse_args()
    build_duckdb(args.data_dir)
