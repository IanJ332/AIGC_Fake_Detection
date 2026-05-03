import argparse
import pandas as pd
import json
import os
import subprocess
import glob
from pathlib import Path
import time
import re

def normalize_columns(df, prefix="P"):
    df = df.copy()

    if "paper_id" not in df.columns:
        df["paper_id"] = ""

    if "id" in df.columns:
        missing = df["paper_id"].isna() | (df["paper_id"].astype(str).str.strip() == "") | (df["paper_id"].astype(str).str.lower() == "nan")
        df.loc[missing, "paper_id"] = df.loc[missing, "id"].astype(str)

    missing = df["paper_id"].isna() | (df["paper_id"].astype(str).str.strip() == "") | (df["paper_id"].astype(str).str.lower() == "nan")
    df.loc[missing, "paper_id"] = [f"{prefix}{i+1:03d}" for i in range(missing.sum())]

    df["paper_id"] = df["paper_id"].astype(str).str.replace(r"[^A-Za-z0-9_-]+", "_", regex=True)

    for col in ["title", "year", "citation_count", "source_url", "pdf_url", "abstract", "referenced_works"]:
        if col not in df.columns:
            df[col] = ""

    return df

def check_relevance(title, abstract):
    text = str(title).lower() + " " + str(abstract).lower()
    
    include_kws = ["synthetic media", "multimedia forensics", "image forgery", "image manipulation", "copy-move", "splicing", "inpainting", "face forgery", "deepfake", "fake face", "manipulated image", "forged image", "visual misinformation", "generated image", "synthetic image", "ai-generated image", "gan", "diffusion", "aigc", "attribution"]
    exclude_kws = ["audio only", "speech only", "text only", "medical diagnosis", "malnutrition", "disease", "lesion", "tumor", "segmentation only", "object detection only"]
    
    if any(ex in text for ex in exclude_kws):
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
    seed_df = normalize_columns(seed_df, prefix="P")

    candidate_pool_used = ""
    candidates_rows = 0
    
    candidates_df = pd.DataFrame()
    if os.path.exists(args.candidate_pool):
        candidates_df = pd.read_csv(args.candidate_pool)
        candidates_df = normalize_columns(candidates_df, prefix="C")
        candidate_pool_used = args.candidate_pool
        candidates_rows = len(candidates_df)
        if "scope_family" not in candidates_df.columns:
            candidates_df["scope_family"] = "unknown"
    
    if "scope_family" not in seed_df.columns:
        seed_df["scope_family"] = "seed"
    
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
    
    # Handle duplicated paper_ids
    if all_df["paper_id"].duplicated().any():
        dup_mask = all_df["paper_id"].duplicated(keep='first')
        all_df.loc[dup_mask, "paper_id"] = [f"D{i+1:04d}" for i in range(dup_mask.sum())]
    
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
        
        assert active_df["paper_id"].notna().all()
        assert not active_df["paper_id"].astype(str).str.lower().eq("nan").any()
        nan_count = active_df["paper_id"].isna().sum() + active_df["paper_id"].astype(str).str.lower().eq("nan").sum()
        dup_count = active_df["paper_id"].duplicated().sum()
        print(f"Candidate paper_id null count: {nan_count}")
        print(f"Candidate paper_id duplicate count: {dup_count}")
        
        active_manifest_path = data_dir / "registry" / "active_manifest.csv"
        active_manifest_path.parent.mkdir(parents=True, exist_ok=True)
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
    reg_file = data_dir / "registry" / "executable_manifest.csv"
    reg_file.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(active_manifest).to_csv(reg_file, index=False)
    
    # Get scope family distribution
    final_df = pd.DataFrame(active_manifest)
    scope_dist = {}
    if "scope_family" in final_df.columns:
        scope_dist = final_df["scope_family"].value_counts().to_dict()
    pdf_count = len(list(data_dir.joinpath("pdfs").glob("*.pdf")))
        
    status_data = {
        "target": args.target_parsed,
        "parsed_json_count": parsed,
        "actual_pdf_count": pdf_count,
        "attempts": attempts,
        "candidate_pool_used": candidate_pool_used,
        "candidate_pool_rows": candidates_rows,
        "scope_family_distribution": scope_dist,
        "nan_paper_id_count": int(final_df["paper_id"].isna().sum() + final_df["paper_id"].astype(str).str.lower().eq("nan").sum()),
        "duplicate_paper_id_count": int(final_df["paper_id"].duplicated().sum()),
        "final_status": status
    }
    with open(data_dir / "probes" / "executable_corpus_status.json", "w") as f:
        json.dump(status_data, f, indent=2)
        
    with open(data_dir / "download_logs" / "backfill_report.md", "w") as f:
        f.write("# Backfill Report\n\n")
        f.write(f"- **Final Status**: {status}\n")
        f.write(f"- **Candidate Pool Used**: {candidate_pool_used}\n")
        f.write(f"- **Candidate Pool Rows**: {candidates_rows}\n")
        f.write(f"- **Target Parsed**: {args.target_parsed}\n")
        f.write(f"- **Actual PDF Count**: {pdf_count}\n")
        f.write(f"- **Parsed JSON Count**: {parsed}\n")
        f.write(f"- **Attempts**: {attempts}\n\n")
        f.write("## Scope Family Distribution\n")
        for k, v in scope_dist.items():
            f.write(f"- {k}: {v}\n")

if __name__ == "__main__":
    main()
