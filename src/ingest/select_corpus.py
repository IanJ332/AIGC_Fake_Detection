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
    score = 0.35 * normalized citation_count 
          + 0.35 * topical_relevance
          + 0.15 * pdf_or_oa_available
          + 0.10 * benchmark_or_dataset_relevance
          + 0.05 * recency_bonus
    """
    # 1. Citation score (log normalized or capped)
    citations = paper.get("citation_count", 0)
    # Simple normalization: cap at 1000 citations and divide by 1000
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
        "artificial", "adversarial", "neural", "fake", "synthesized", "manipulated",
        "generative", "synthesis", "face swap", "attribute editing"
    ]
    detection_keywords = [
        "detection", "forensics", "localization", "identification", "fake", 
        "authenticity", "verifying", "classifier", "attribution", "recognition",
        "forgery", "analysis", "discriminating", "detecting"
    ]
    
    has_aigc = any(kw in title_abs for kw in aigc_keywords)
    has_detection = any(kw in title_abs for kw in detection_keywords)
    
    if not (has_aigc and has_detection):
        topical_relevance = 0.1 # Weak match
    else:
        # Extra points for very specific AIGC terms
        specific_keywords = ["deepfake", "aigc", "diffusion", "stable diffusion", "midjourney"]
        if any(kw in title_abs for kw in specific_keywords):
            topical_relevance = 1.0
        else:
            topical_relevance = 0.8 # Good but general
    
    # 3. Open access
    oa_score = 1.0 if paper.get("pdf_url") else 0.0
    
    # 4. Benchmark/Dataset
    benchmark_keywords = ["benchmark", "dataset", "competition", "challenge", "evaluation", "database"]
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
        0.35 * citation_score +
        0.35 * topical_relevance +
        0.15 * oa_score +
        0.10 * benchmark_score +
        0.05 * recency_bonus
    )
    
    # If it's a very weak topical match, penalize heavily
    if topical_relevance < 0.2:
        final_score *= 0.1

    return final_score

def infer_tags(paper):
    title_abs = ((paper.get("title") or "") + " " + (paper.get("abstract") or "")).lower()
    
    # Modality Scope
    modality = "unknown"
    if "image" in title_abs or "pixel" in title_abs:
        modality = "image"
        if "face" in title_abs or "facial" in title_abs:
            modality = "face_image"
    elif "video" in title_abs:
        modality = "video"
    elif "audio" in title_abs or "speech" in title_abs or "voice" in title_abs:
        modality = "audio"
    elif "text" in title_abs:
        modality = "text"
        
    # Topic Family
    family = "unknown"
    if "deepfake" in title_abs or "face manipulation" in title_abs or "face swap" in title_abs:
        family = "face_forgery_detection"
    elif "gan" in title_abs or "diffusion" in title_abs or "synthetic" in title_abs or "aigc" in title_abs:
        family = "ai_generated_image_detection"
    elif "forgery" in title_abs and ("localization" in title_abs or "segmentation" in title_abs or "pixel" in title_abs):
        family = "image_forgery_localization"
    elif "benchmark" in title_abs or "dataset" in title_abs or "database" in title_abs:
        family = "benchmark_dataset"
    elif "survey" in title_abs or "review" in title_abs:
        family = "survey"
    elif "forensics" in title_abs:
        family = "general_forensics"
        
    # Era
    year = paper.get("year", 0)
    era = "unknown"
    if year > 0:
        if "diffusion" in title_abs or "stable diffusion" in title_abs or year >= 2023:
            era = "diffusion_era"
        elif year >= 2022:
            era = "foundation_model_era"
        elif "gan" in title_abs or (year >= 2014 and year < 2022):
            era = "gan_era"
        else:
            era = "pre_gan"
            
    return modality, family, era

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
    
    # Add inferred tags
    df[['modality_scope', 'topic_family', 'era']] = df.apply(lambda row: pd.Series(infer_tags(row)), axis=1)
    
    # Replacement Protocol
    # Identify weak matches or excluded modalities
    exclude_terms = ["video", "audio", "speech", "voice", "text detection", "watermark"]
    def is_weak(row):
        title_abs = (str(row['title']) + " " + str(row.get('abstract', ''))).lower()
        if any(term in title_abs for term in exclude_terms) and "image" not in title_abs:
            return True
        if row['score'] < 0.1: # Threshold for penalized weak matches
            return True
        return False

    df['replacement_candidate'] = df.apply(is_weak, axis=1)
    df['must_keep'] = ~df['replacement_candidate']
    
    # Sort by score descending
    df = df.sort_values(by='score', ascending=False)
    
    # Initial top 100
    manifest_100 = df.head(100).copy()
    
    # Check if replacements needed
    weak_count = manifest_100['replacement_candidate'].sum()
    print(f"Initial top 100 has {weak_count} weak matches.")
    
    if weak_count > 0:
        print(f"Applying replacement protocol for {weak_count} papers...")
        strong_candidates = df[100:][~df[100:]['replacement_candidate']].head(weak_count)
        
        # Identify indices to replace
        replace_indices = manifest_100[manifest_100['replacement_candidate']].index
        
        if not strong_candidates.empty:
            num_to_replace = min(len(replace_indices), len(strong_candidates))
            for i in range(num_to_replace):
                idx_to_remove = replace_indices[i]
                # Replace with top strong candidate
                manifest_100.loc[idx_to_remove] = strong_candidates.iloc[i]
            print(f"Replaced {num_to_replace} papers.")

    # Final outputs
    df.head(200).to_csv("corpus/manifest_candidates.csv", index=False)
    manifest_100.to_csv("corpus/manifest_100.csv", index=False)
    print(f"Saved manifests. Final 100 has {len(manifest_100)} rows.")

if __name__ == "__main__":
    main()
