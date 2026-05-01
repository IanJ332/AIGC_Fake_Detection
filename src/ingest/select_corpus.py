import argparse
import pandas as pd
import json
import os
import re
import yaml
from src.utils.io import read_jsonl

def normalize_title(title):
    if not title or not isinstance(title, str):
        return ""
    # Remove non-alphanumeric and lowercase
    return re.sub(r'[^a-z0-9]', '', title.lower())

def score_paper(paper, known_seeds=None):
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
    chem_kws = ["luminescent", "metal-organic", "chemistry", "material science", "nanoparticle", "molecular", "mass spectrometry", "spectrometry", "spectroscopy", "natural products"]
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
        "communication network", "internet of things", "iot", "sensor network"
    ]
    if any(kw in title_abs for kw in gen_kws):
        if not any(kw in title for kw in ["fake", "forgery", "deepfake", "synthetic", "aigc"]):
            exclusion_reasons.append("generic_cv_only")
        
    if exclusion_reasons:
        # Check if it's a known seed. Known seeds can bypass hard exclusions if they are canonical.
        if known_seeds:
            norm_title = normalize_title(title)
            if any(normalize_title(seed) in norm_title for seed in known_seeds):
                pass # Continue to normal scoring for known seeds
            else:
                return 0.0, ", ".join(exclusion_reasons)
        else:
            return 0.0, ", ".join(exclusion_reasons)

    # --- Normal Scoring ---
    # 1. Citation score
    citations = paper.get("citation_count", 0)
    try:
        citations = float(citations) if citations else 0.0
    except:
        citations = 0.0
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
        specific_keywords = ["deepfake", "aigc", "diffusion", "stable diffusion", "midjourney", "fake image detection"]
        if any(kw in title_abs for kw in specific_keywords):
            topical_relevance = 1.0
        else:
            topical_relevance = 0.8
    
    # 3. Open access
    pdf_url = paper.get("pdf_url")
    oa_score = 1.0 if pdf_url and isinstance(pdf_url, str) else 0.0
    
    # 4. Benchmark/Dataset
    benchmark_keywords = ["benchmark", "dataset", "competition", "challenge", "evaluation", "database", "artifact", "synthbuster"]
    benchmark_matches = sum(1 for kw in benchmark_keywords if kw in title_abs)
    benchmark_score = 1.0 if benchmark_matches > 0 else 0.0
    
    # 5. Recency bonus
    year = paper.get("year", 0)
    try:
        year = int(year) if year else 0
    except:
        year = 0
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
    
    # 6. Known Seed Match Bonus
    if known_seeds:
        norm_title = normalize_title(title)
        if any(normalize_title(seed) in norm_title for seed in known_seeds):
            final_score += 5.0 # Major boost for known seeds

    if topical_relevance < 0.2 and not (known_seeds and any(normalize_title(seed) in normalize_title(title) for seed in known_seeds)):
        final_score *= 0.1

    return final_score, ""

def infer_tags(paper):
    title = str(paper.get("title") or "").lower()
    abstract = str(paper.get("abstract") or "").lower()
    title_abs = title + " " + abstract
    
    modality = "unknown"
    if "image" in title_abs or "pixel" in title_abs:
        modality = "image"
        if "face" in title_abs or "facial" in title_abs:
            modality = "face_image"
    elif "video" in title_abs:
        modality = "video"
        
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
            
    return modality, family

def guess_paper_role(paper):
    title = str(paper.get("title") or "").lower()
    abstract = str(paper.get("abstract") or "").lower()
    title_abs = title + " " + abstract
    if "survey" in title_abs or "review" in title_abs:
        return "survey"
    if "dataset" in title_abs or "benchmark" in title_abs:
        return "dataset/benchmark"
    return "method"

def main():
    parser = argparse.ArgumentParser(description="Select top papers for the corpus.")
    parser.add_argument("--input", default="corpus/raw_metadata/openalex_raw.jsonl", help="Path to input JSONL")
    parser.add_argument("--seeds", default="configs/known_seed_papers.yaml", help="Path to known seeds config")
    args = parser.parse_args()

    candidates = read_jsonl(args.input)
    if not candidates:
        print("Error: No data to process.")
        return

    known_seeds = []
    if os.path.exists(args.seeds):
        with open(args.seeds, 'r') as f:
            known_seeds = yaml.safe_load(f).get("known_papers", [])

    df = pd.DataFrame(candidates)
    print(f"Initial candidates: {len(df)}")
    
    df['doi'] = df['doi'].fillna('')
    doi_mask = df['doi'] != ''
    df_with_doi = df[doi_mask].drop_duplicates(subset=['doi'])
    df_without_doi = df[~doi_mask]
    df = pd.concat([df_with_doi, df_without_doi])
    
    df['norm_title'] = df['title'].apply(normalize_title)
    df = df.drop_duplicates(subset=['norm_title'])
    print(f"After deduplication: {len(df)}")

    # Scoring
    scored_results = df.apply(lambda row: score_paper(row, known_seeds), axis=1)
    df['score'] = [r[0] for r in scored_results]
    df['exclusion_reason'] = [r[1] for r in scored_results]
    
    df['paper_role_guess'] = df.apply(guess_paper_role, axis=1)
    df['risk_flags'] = df['exclusion_reason']
    df[['modality_scope', 'topic_family']] = df.apply(lambda row: pd.Series(infer_tags(row)), axis=1)
    
    # must_keep_reason
    def get_must_keep_reason(row):
        title = str(row['title']).lower()
        norm_title = normalize_title(title)
        if any(normalize_title(seed) in norm_title for seed in known_seeds):
            return "explicit_known_seed_paper"
        return ""

    df['must_keep_reason'] = df.apply(get_must_keep_reason, axis=1)

    # Sorting
    def get_sort_priority(row):
        if row['must_keep_reason'] == "explicit_known_seed_paper": return 0
        reason = row['exclusion_reason']
        if reason == "": return 1
        return 2

    df['sort_priority'] = df.apply(get_sort_priority, axis=1)
    df = df.sort_values(by=['sort_priority', 'score'], ascending=[True, False])
    
    # Diversity Caps
    selected = []
    face_count = 0
    forgery_count = 0
    survey_count = 0
    
    for _, row in df.iterrows():
        if len(selected) >= 100:
            break
            
        if row['exclusion_reason'] != "" and row['must_keep_reason'] == "":
            continue
            
        title_l = str(row['title']).lower()
        modality = row['modality_scope']
        family = row['topic_family']
        role = row['paper_role_guess']
        
        is_face = (modality == "face_image" or "face" in title_l)
        is_forgery = (family == "image_forgery_localization" or "forgery" in title_l)
        is_survey = (role == "survey")
        
        if is_face and face_count >= 15 and row['must_keep_reason'] == "": continue
        if is_forgery and forgery_count >= 10 and row['must_keep_reason'] == "": continue
        if is_survey and survey_count >= 10 and row['must_keep_reason'] == "": continue
            
        selected.append(row)
        if is_face: face_count += 1
        if is_forgery: forgery_count += 1
        if is_survey: survey_count += 1
        
    manifest_100 = pd.DataFrame(selected)
    
    if len(manifest_100) < 100:
        remaining = df[~df.index.isin(manifest_100.index)].head(100 - len(manifest_100))
        manifest_100 = pd.concat([manifest_100, remaining])

    manifest_100['replacement_candidate'] = manifest_100['exclusion_reason'] != ""

    df.head(500).to_csv("corpus/manifest_candidates.csv", index=False)
    manifest_100.to_csv("corpus/manifest_100.csv", index=False)
    print(f"Saved manifests. Final 100 has {len(manifest_100)} rows.")
    print(f"Stats: Face={face_count}, Forgery={forgery_count}, Survey={survey_count}")

if __name__ == "__main__":
    main()
