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
    Score each paper with hard exclusions for topic drift.
    """
    title = str(paper.get("title") or "").lower()
    abstract = str(paper.get("abstract") or "").lower()
    title_abs = title + " " + abstract
    
    # --- Hard Exclusions ---
    exclusion_reasons = []
    
    # 1. Medical Imaging / Pathology
    med_kws = ["brain tumor", "brats", "pathology", "clinical", "cancer", "medical", "mri", "ct scan", "histopathology", "arterial stiffness", "coronavirus", "medicine", "nanomedicine", "neuroimaging", "alzheimer"]
    if any(kw in title_abs for kw in med_kws):
        if not any(kw in title for kw in ["fake", "deepfake", "forgery", "aigc"]):
            exclusion_reasons.append("medical_only")
        
    # 2. Chemistry / Materials
    chem_kws = ["luminescent", "metal-organic", "chemistry", "material science", "nanoparticle", "molecular", "mass spectrometry", "spectrometry"]
    if any(kw in title_abs for kw in chem_kws):
        exclusion_reasons.append("chemistry_materials")
        
    # 3. Generic Object Detection / Benchmarks (unless AIGC/Forgery mentioned in TITLE)
    bench_kws = ["pascal", "voc challenge", "coco dataset", "imagenet", "object detection benchmark", "visual genome", "voc (voc) challenge"]
    if any(kw in title for kw in bench_kws) or ( "voc" in title and "challenge" in title):
        aigc_core = ["fake", "forgery", "manipulation", "deepfake", "synthetic", "generated", "aigc", "forensics"]
        if not any(kw in title for kw in aigc_core):
            exclusion_reasons.append("object_detection_only")
        
    # 4. Generic Explainability (unless AIGC/Forgery mentioned in TITLE)
    exp_kws = ["grad-cam", "lrp", "explainable ai", "xai", "visual explanations", "pixel-wise explanations"]
    if any(kw in title for kw in exp_kws):
        if not any(kw in title for kw in ["fake", "forgery", "manipulation", "deepfake"]):
            exclusion_reasons.append("explainability_only")
        
    # 5. General CV / Non-Image (unless AIGC/Forgery mentioned)
    gen_kws = [
        "wireless", "6g", "image processing", "computer vision survey", 
        "haze removal", "visual tracking", "image data augmentation",
        "temperature", "climate", "ocean", "satellite", "remote sensing",
        "communication network", "internet of things", "iot", "sensor network",
        "spectrometry", "spectroscopy", "natural products"
    ]
    if any(kw in title_abs for kw in gen_kws):
        if not any(kw in title for kw in ["fake", "forgery", "deepfake", "synthetic", "aigc"]):
            exclusion_reasons.append("generic_cv_only")
        
    if exclusion_reasons:
        return 0.0, ", ".join(exclusion_reasons)

    # --- Normal Scoring ---
    # 1. Citation score
    citations = paper.get("citation_count", 0)
    citation_score = min(citations / 1000.0, 1.0)
    
    # 2. Topical relevance
    # Essential image focus
    has_image_focus = any(kw in title_abs for kw in ["image", "face", "facial", "visual", "pixel", "frame", "vision"])
    if not has_image_focus:
        return 0.0, "no_image_focus"
    
    # Exclude video-only if explicitly stated and no mention of image
    if "video" in title_abs and "image" not in title_abs:
        return 0.001, "video_only_risk"
        
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
        topical_relevance = 0.1
    else:
        specific_keywords = ["deepfake", "aigc", "diffusion", "stable diffusion", "midjourney"]
        if any(kw in title_abs for kw in specific_keywords):
            topical_relevance = 1.0
        else:
            topical_relevance = 0.8
    
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
    
    if topical_relevance < 0.2:
        final_score *= 0.1

    return final_score, ""

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

    # Scoring
    scored_results = df.apply(lambda row: score_paper(row), axis=1)
    df['score'] = [r[0] for r in scored_results]
    df['exclusion_reason'] = [r[1] for r in scored_results]
    
    df['paper_role_guess'] = df.apply(guess_paper_role, axis=1)
    df['risk_flags'] = df['exclusion_reason']
    
    # Add inferred tags
    df[['modality_scope', 'topic_family', 'era']] = df.apply(lambda row: pd.Series(infer_tags(row)), axis=1)
    
    # must_keep_reason logic
    def get_must_keep_reason(row):
        title = str(row['title']).lower()
        reason = row['exclusion_reason']
        if reason == "":
            return ""
            
        if "object_detection_only" in reason:
            return "foundational_dataset_used_by_many_corpus_papers"
        if "explainability_only" in reason:
            return "foundational_method_for_localization_or_explainability"
        if "generic_cv_only" in reason:
            if "survey" in title or "review" in title:
                return "foundational_survey_providing_context"
            return "foundational_method_for_image_analysis"
        if "medical_only" in reason:
            return "foundational_method_for_imaging_benchmarking"
        if "chemistry_materials" in reason:
            return "foundational_method_for_material_analysis"
        if "no_image_focus" in reason:
            return "foundational_generic_machine_learning_method"
        if "video_only_risk" in reason:
            return "foundational_method_for_temporal_analysis"
            
        return "general_foundational_method"

    df['must_keep_reason'] = df.apply(get_must_keep_reason, axis=1)

    # Replacement Protocol - Prioritized Sorting
    # 1. No exclusion reason (Strong/Weak)
    # 2. Least offensive drift
    def get_sort_priority(row):
        reason = row['exclusion_reason']
        if reason == "":
            return 0
        if reason == "no_image_focus":
            return 1
        if "generic_cv_only" in reason:
            return 2
        if "explainability_only" in reason:
            return 3
        if "object_detection_only" in reason:
            return 4
        # Medical/Chemistry at the very bottom
        return 5

    df['sort_priority'] = df.apply(get_sort_priority, axis=1)
    
    # Sort by priority ascending, then score descending
    df = df.sort_values(by=['sort_priority', 'score'], ascending=[True, False])
    
    # Final 100
    manifest_100 = df.head(100).copy()
    
    # Identify replacement candidates (for candidates pool)
    df['replacement_candidate'] = df['exclusion_reason'] != ""
    manifest_100['replacement_candidate'] = manifest_100['exclusion_reason'] != ""

    # Final outputs
    df.head(200).to_csv("corpus/manifest_candidates.csv", index=False)
    manifest_100.to_csv("corpus/manifest_100.csv", index=False)
    print(f"Saved manifests. Final 100 has {len(manifest_100)} rows.")

if __name__ == "__main__":
    main()
