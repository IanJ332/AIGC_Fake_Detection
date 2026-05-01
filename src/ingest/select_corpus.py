import argparse
import pandas as pd
import json
import os
import re
from src.utils.io import read_jsonl

def normalize_title(title):
    if not title:
        return ""
    return re.sub(r'[^a-z0-9]', '', title.lower())

def score_paper(paper):
    """
    Score each paper:
    score = 0.45 * normalized citation_count 
          + 0.25 * topical_relevance
          + 0.15 * open_access_pdf_available
          + 0.10 * benchmark_or_dataset_relevance
          + 0.05 * recency_bonus
    """
    # 1. Citation score (log normalized or capped)
    citations = paper.get("citation_count", 0)
    # Simple normalization for Day 1: cap at 1000 citations and divide by 1000
    citation_score = min(citations / 1000.0, 1.0)
    
    # 2. Topical relevance (keyword matching)
    title_abs = (paper.get("title") or "") + " " + (paper.get("abstract") or "")
    title_abs = title_abs.lower()
    
    # Check if 'image' or related is present
    has_image_focus = any(kw in title_abs for kw in ["image", "face", "facial", "visual", "pixel", "frame", "vision"])
    if not has_image_focus:
        return 0.0 
    
    # Exclude video-only if explicitly stated and no mention of image
    if "video" in title_abs and "image" not in title_abs:
        return 0.001 # Very low but not zero
        
    aigc_keywords = [
        "aigc", "deepfake", "gan", "diffusion", "synthetic", "forgery", 
        "stable diffusion", "midjourney", "dalle", "generated", "manipulation",
        "artificial", "adversarial", "neural"
    ]
    detection_keywords = ["detection", "forensics", "localization", "identification", "fake", "authenticity", "verifying"]
    
    has_aigc = any(kw in title_abs for kw in aigc_keywords)
    has_detection = any(kw in title_abs for kw in detection_keywords)
    
    if not (has_aigc and has_detection):
        topical_relevance = 0.1 # Weak match
    else:
        topical_relevance = 1.0 # Strong match
    
    # 3. Open access
    oa_score = 1.0 if paper.get("pdf_url") else 0.0
    
    # 4. Benchmark/Dataset
    benchmark_keywords = ["benchmark", "dataset", "competition", "challenge", "evaluation"]
    benchmark_matches = sum(1 for kw in benchmark_keywords if kw in title_abs)
    benchmark_score = 1.0 if benchmark_matches > 0 else 0.0
    
    # 5. Recency bonus
    year = paper.get("year", 0)
    recency_bonus = 0.0
    if year >= 2023:
        recency_bonus = 1.0
    elif year >= 2021:
        recency_bonus = 0.5
        
    final_score = (
        0.45 * citation_score +
        0.25 * topical_relevance +
        0.15 * oa_score +
        0.10 * benchmark_score +
        0.05 * recency_bonus
    )
    
    # If it's a very weak topical match, penalize heavily
    if topical_relevance < 0.5:
        final_score *= 0.1

    return final_score

def guess_paper_role(paper):
    title_abs = ((paper.get("title") or "") + " " + (paper.get("abstract") or "")).lower()
    if "survey" in title_abs or "review" in title_abs:
        return "survey"
    if "dataset" in title_abs or "benchmark" in title_abs:
        return "dataset/benchmark"
    if "challenge" in title_abs or "competition" in title_abs:
        return "challenge"
    return "method"

def check_risk_flags(paper):
    title_abs = ((paper.get("title") or "") + " " + (paper.get("abstract") or "")).lower()
    flags = []
    if "video" in title_abs and "image" not in title_abs:
        flags.append("video_only")
    if not paper.get("pdf_url"):
        flags.append("missing_pdf")
    # Add more as needed
    return ", ".join(flags)

def main():
    parser = argparse.ArgumentParser(description="Select top papers for the corpus.")
    parser.add_argument("--input", default="corpus/raw_metadata/semantic_scholar_backfill.jsonl", help="Path to input JSONL")
    args = parser.parse_args()

    candidates = read_jsonl(args.input)
    if not candidates:
        print("No candidates found. Trying raw OpenAlex data...")
        candidates = read_jsonl("corpus/raw_metadata/openalex_raw.jsonl")
    
    if not candidates:
        print("Error: No data to process.")
        return

    # Deduplicate
    df = pd.DataFrame(candidates)
    print(f"Initial candidates: {len(df)}")
    
    # Fill missing DOIs with None for consistent deduplication
    df['doi'] = df['doi'].fillna('')
    
    # Deduplicate by DOI first (excluding empty)
    doi_mask = df['doi'] != ''
    df_with_doi = df[doi_mask].drop_duplicates(subset=['doi'])
    df_without_doi = df[~doi_mask]
    
    df = pd.concat([df_with_doi, df_without_doi])
    
    # Deduplicate by normalized title
    df['norm_title'] = df['title'].apply(normalize_title)
    df = df.drop_duplicates(subset=['norm_title'])
    print(f"After deduplication: {len(df)}")

    # Score
    df['score'] = df.apply(score_paper, axis=1)
    df['paper_role_guess'] = df.apply(guess_paper_role, axis=1)
    df['risk_flags'] = df.apply(check_risk_flags, axis=1)
    
    # Sort
    df = df.sort_values(by='score', ascending=False)
    
    # Output top 200 candidates
    manifest_candidates = df.head(200)
    manifest_candidates.to_csv("corpus/manifest_candidates.csv", index=False)
    print(f"Saved top 200 candidates to corpus/manifest_candidates.csv")
    
    # Output top 100 selection
    manifest_100 = df.head(100)
    manifest_100.to_csv("corpus/manifest_100.csv", index=False)
    print(f"Saved top 100 selection to corpus/manifest_100.csv")

if __name__ == "__main__":
    main()
