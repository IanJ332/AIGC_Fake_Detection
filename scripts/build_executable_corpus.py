import argparse
import pandas as pd
import json
import os
import subprocess
import glob
from pathlib import Path
import time
import re

def normalize_columns(df):
    if "id" in df.columns and "paper_id" not in df.columns:
        df["paper_id"] = df["id"]
    for col in ["title", "year", "citation_count", "source_url", "pdf_url", "abstract", "referenced_works"]:
        if col not in df.columns:
            df[col] = ""
    return df

def check_relevance(title, abstract):
    text = str(title).lower() + " " + str(abstract).lower()
    
    include_kws = ["ai-generated image", "synthetic image", "fake image", "aigc", "generative", "diffusion", "gan", "image forensics", "deepfake image", "generated image detection"]
    exclude_kws = ["medical-only", "audio-only", "speech-only", "text-only"]
    
    if any(ex in text for ex in exclude_kws):
        # We allow video-only if image/deepfake detection related, but let's keep it simple
        if "video-only" in text and not any(kw in text for kw in ["image", "deepfake detection"]):
            return False
        return False
        
    return any(inc in text for inc in include_kws)

def get_parsed_json_count(data_dir):
    return len(list(Path(data_dir).joinpath("parsed").glob("*.json")))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-manifest", required=True)
    parser.add_argument("--candidate-pool", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--target-parsed", type=int, default=100)
    parser.add_argument("--max-candidates", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--delay", type=float, default=1.5)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "registry").mkdir(parents=True, exist_ok=True)
    (data_dir / "download_logs").mkdir(parents=True, exist_ok=True)
    (data_dir / "probes").mkdir(parents=True, exist_ok=True)

    if not os.path.exists(args.seed_manifest):
        print(f"Error: seed manifest not found {args.seed_manifest}")
        return

    seed_df = pd.read_csv(args.seed_manifest)
    seed_df = normalize_columns(seed_df)

    candidates_df = pd.DataFrame()
    if os.path.exists(args.candidate_pool):
        candidates_df = pd.read_csv(args.candidate_pool)
        candidates_df = normalize_columns(candidates_df)
    
    # Deduplicate
    all_df = pd.concat([seed_df, candidates_df], ignore_index=True)
    all_df['title_norm'] = all_df['title'].astype(str).str.lower().str.strip()
    
    # Filter relevance for candidates
    all_df['relevant'] = all_df.apply(lambda x: check_relevance(x['title'], x['abstract']), axis=1)
    
    # Sort: Seed rows first (they are implicitly relevant), then candidates by pdf_url existence, citation count, year
    all_df['is_seed'] = all_df.index < len(seed_df)
    all_df['has_pdf'] = all_df['pdf_url'].astype(str).str.len() > 5
    
    all_df['citation_count'] = pd.to_numeric(all_df['citation_count'], errors='coerce').fillna(0)
    all_df['year'] = pd.to_numeric(all_df['year'], errors='coerce').fillna(0)
    
    # Seed gets priority, then relevant candidates with PDFs, sorted by citation
    all_df = all_df.sort_values(by=['is_seed', 'relevant', 'has_pdf', 'citation_count', 'year'], ascending=[False, False, False, False, False])
    all_df = all_df.drop_duplicates(subset=['title_norm'], keep='first')
    
    # We only want to process up to target_parsed + buffer
    # The pool is all_df. We take batches from it.
    
    pool = all_df.to_dict('records')
    active_manifest = []
    
    attempts = 0
    batch_num = 0
    
    while attempts < args.max_candidates and get_parsed_json_count(data_dir) < args.target_parsed and pool:
        batch_num += 1
        print(f"\n--- Batch {batch_num} ---")
        
        # Take batch
        batch = pool[:args.batch_size]
        pool = pool[args.batch_size:]
        attempts += len(batch)
        
        active_manifest.extend(batch)
        active_df = pd.DataFrame(active_manifest)
        active_manifest_path = data_dir / "registry" / "active_manifest.csv"
        active_df.to_csv(active_manifest_path, index=False)
        
        print(f"Downloading batch of {len(batch)} papers (total active: {len(active_manifest)})...")
        subprocess.run([
            "python", "scripts/download_corpus.py",
            "--manifest", str(active_manifest_path),
            "--data-dir", str(data_dir),
            "--delay", str(args.delay)
        ], check=True)
        
        print("Parsing PDFs...")
        subprocess.run(["python", "-m", "src.parse.parse_pdfs", "--data-dir", str(data_dir)], check=True)
        print("Segmenting Sections...")
        subprocess.run(["python", "-m", "src.parse.segment_sections", "--data-dir", str(data_dir)], check=True)
        print("Extracting Table Candidates...")
        subprocess.run([
            "python", "-m", "src.parse.extract_table_candidates",
            "--sections", f"{data_dir}/sections/sections.jsonl",
            "--out", f"{data_dir}/tables/table_candidates.jsonl"
        ], check=True)
        
        parsed = get_parsed_json_count(data_dir)
        print(f"Parsed JSONs: {parsed}/{args.target_parsed}")
        
    parsed = get_parsed_json_count(data_dir)
    status = "EXECUTABLE_CORPUS_BLOCKED"
    if parsed >= args.target_parsed:
        status = "EXECUTABLE_CORPUS_READY"
    elif parsed >= 95:
        status = "EXECUTABLE_CORPUS_CAUTION_NEAR_TARGET"
    elif parsed >= 70:
        status = "EXECUTABLE_CORPUS_CAUTION_LOW"
        
    print(f"\nFinal Status: {status} ({parsed} parsed)")
    
    # Save final tracking files
    pd.DataFrame(active_manifest).to_csv(data_dir / "registry" / "executable_manifest.csv", index=False)
    
    status_data = {
        "target": args.target_parsed,
        "parsed": parsed,
        "attempts": attempts,
        "status": status
    }
    with open(data_dir / "probes" / "executable_corpus_status.json", "w") as f:
        json.dump(status_data, f, indent=2)
        
    with open(data_dir / "download_logs" / "backfill_report.md", "w") as f:
        f.write("# Backfill Report\n\n")
        f.write(f"- Status: {status}\n")
        f.write(f"- Target: {args.target_parsed}\n")
        f.write(f"- Parsed: {parsed}\n")
        f.write(f"- Attempts: {attempts}\n")

if __name__ == "__main__":
    main()
