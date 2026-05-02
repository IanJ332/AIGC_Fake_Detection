import pandas as pd
from pathlib import Path
import os

def expand_corpus():
    # Paths
    repo_root = Path(os.getcwd())
    candidates_path = repo_root / "corpus" / "manifest_candidates.csv"
    current_manifest_path = repo_root / "corpus" / "manifest_100.csv"
    registry_path = repo_root / "Data" / "registry" / "document_registry.csv"
    
    output_candidates_v2 = repo_root / "corpus" / "manifest_candidates_v2.csv"
    output_executable_100 = repo_root / "corpus" / "manifest_executable_100.csv"
    output_replacements = repo_root / "corpus" / "manifest_replacements_v2.csv"
    output_report = repo_root / "docs" / "day9_corpus_expansion_report.md"

    # Load data
    print(f"Loading {candidates_path}...")
    df_candidates = pd.read_csv(candidates_path)
    
    print(f"Loading {current_manifest_path}...")
    df_current = pd.read_csv(current_manifest_path)
    
    print(f"Loading {registry_path}...")
    df_registry = pd.read_csv(registry_path)

    # 1. Identify successful papers from current Data bundle
    successful_ids = df_registry[df_registry['pdf_downloaded'] == True]['openalex_id'].tolist()
    failed_ids = df_registry[df_registry['pdf_downloaded'] == False]['openalex_id'].tolist()
    
    print(f"Current success: {len(successful_ids)}, Current failure: {len(failed_ids)}")

    # 2. Filter candidates for replacements
    # - Not already in successful set
    # - Has pdf_url
    # - Topic relevant (already mostly filtered in manifest_candidates, but we'll re-verify)
    # - Rank by citation_count and year
    
    # Exclude those that are already in the registry (even if failed, we want new ones if possible)
    # Actually, we should exclude the successful ones for sure.
    # For the failed ones, we check if they are in the candidates list and if we can find better ones.
    
    registry_openalex_ids = df_registry['openalex_id'].tolist()
    
    # Candidates that were NOT in the original 100
    df_fresh_candidates = df_candidates[~df_candidates['openalex_id'].isin(registry_openalex_ids)].copy()
    
    # Must have a PDF URL
    df_fresh_candidates = df_fresh_candidates[df_fresh_candidates['pdf_url'].notna()]
    
    # Policy filtering: Exclude medical/audio if possible
    # (Checking abstract/concepts)
    def is_valid_topic(row):
        text = str(row['title']) + " " + str(row['abstract'])
        text = text.lower()
        if "medical" in text or "audio" in text or "speech" in text:
            # Check if it's actually about AIGC detection in that domain
            if "image" not in text and "face" not in text:
                return False
        return True

    df_fresh_candidates['is_valid'] = df_fresh_candidates.apply(is_valid_topic, axis=1)
    df_fresh_candidates = df_fresh_candidates[df_fresh_candidates['is_valid'] == True]

    # Rank by citation count (desc) and year (desc)
    df_fresh_candidates = df_fresh_candidates.sort_values(by=['citation_count', 'year'], ascending=False)

    print(f"Fresh valid candidates found: {len(df_fresh_candidates)}")

    # 3. Build the new 100
    # Keep the successful ones
    df_successful = df_candidates[df_candidates['openalex_id'].isin(successful_ids)].copy()
    
    num_to_replace = 100 - len(df_successful)
    print(f"Need to pick {num_to_replace} new papers.")

    df_replacements = df_fresh_candidates.head(num_to_replace).copy()
    
    df_final_100 = pd.concat([df_successful, df_replacements], ignore_index=True)
    
    # Ensure exactly 100
    df_final_100 = df_final_100.head(100)

    # 4. Save outputs
    print(f"Saving {output_executable_100}...")
    df_final_100.to_csv(output_executable_100, index=False)
    
    print(f"Saving {output_replacements}...")
    df_replacements.to_csv(output_replacements, index=False)
    
    # Candidates v2 (for future reference)
    df_candidates.to_csv(output_candidates_v2, index=False)

    # 5. Generate report
    report_content = f"""# Day 9 Corpus Expansion Report

## Overview
- **Original Executable Papers**: {len(successful_ids)}
- **Failed/Inaccessible Papers Replaced**: {len(failed_ids)}
- **New Executable Target**: 100

## Replacement Strategy
We identified {len(df_fresh_candidates)} potential candidates from the expanded pool that have accessible PDF URLs.
We selected the top {num_to_replace} candidates based on:
1. Direct PDF accessibility (arXiv, OpenAccess CVF).
2. Citation count.
3. Topical relevance to AIGC detection.

## Selected Replacements
| Title | Year | Citations | Source |
| :--- | :--- | :--- | :--- |
"""
    for _, row in df_replacements.iterrows():
        report_content += f"| {row['title']} | {row['year']} | {row['citation_count']} | {row['pdf_url']} |\n"

    report_content += "\n## Failed Papers (Original Manifest)\n"
    df_failed = df_candidates[df_candidates['openalex_id'].isin(failed_ids)]
    for _, row in df_failed.iterrows():
        report_content += f"- {row['title']} ({row['year']}) - [OpenAlex]({row['openalex_id']})\n"

    with open(output_report, "w", encoding="utf-8") as f:
        f.write(report_content)

    print("Corpus expansion complete.")

if __name__ == "__main__":
    expand_corpus()
