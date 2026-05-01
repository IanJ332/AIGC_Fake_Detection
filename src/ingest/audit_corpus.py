import pandas as pd
import os

def audit_corpus(manifest_path="corpus/manifest_100.csv", output_path="docs/day1_corpus_audit.md"):
    if not os.path.exists(manifest_path):
        print(f"Error: {manifest_path} not found.")
        return

    df = pd.read_csv(manifest_path)
    
    # 1. Stats
    total_rows = len(df)
    dup_doi = df['doi'].duplicated().sum() if 'doi' in df.columns else 0
    df['norm_title'] = df['title'].str.lower().str.replace(r'[^a-z0-9]', '', regex=True)
    dup_title = df['norm_title'].duplicated().sum()
    
    year_dist = df['year'].value_counts().sort_index().to_dict()
    cit_min = df['citation_count'].min()
    cit_median = df['citation_count'].median()
    cit_max = df['citation_count'].max()
    
    pdf_count = df['pdf_url'].notna().sum()
    role_dist = df['paper_role_guess'].value_counts().to_dict()
    risk_dist = df['risk_flags'].value_counts().to_dict()
    
    # Topic Drift Section
    drift_categories = [
        "medical_only", "chemistry_materials", "object_detection_only", 
        "explainability_only", "generic_cv_only", "no_image_focus", "video_only_risk"
    ]
    # Ensure risk_flags is string for matching
    df['risk_flags'] = df['risk_flags'].fillna('').astype(str)
    # Check exclusion_reason/risk_flags
    drift_papers = df[df['risk_flags'].str.contains("|".join(drift_categories), na=False)]
    drift_count = len(drift_papers)
    
    # 3. Generate Markdown
    md = []
    md.append("# Day 1 Corpus Audit Report\n")
    
    md.append("## Executive Summary")
    md.append(f"- **Total Papers**: {total_rows}")
    md.append(f"- **Duplicate DOIs**: {dup_doi}")
    md.append(f"- **Duplicate Titles**: {dup_title}")
    md.append(f"- **PDF/OA Available**: {pdf_count} ({pdf_count/total_rows:.1%})")
    md.append(f"- **Citation Count**: Min: {cit_min}, Median: {cit_median}, Max: {cit_max}")
    md.append(f"- **Topic Drift Count**: {drift_count}")
    md.append("")
    
    md.append("## Topic Drift Details")
    if drift_count > 0:
        md.append("| Title | Drift Category | Must Keep Reason |")
        md.append("| :--- | :--- | :--- |")
        for _, row in drift_papers.iterrows():
            title = str(row['title'])[:80] + "..." if len(str(row['title'])) > 80 else str(row['title'])
            md.append(f"| {title} | {row['risk_flags']} | {row.get('must_keep_reason', '')} |")
    else:
        md.append("No significant topic drift detected.")
    md.append("")
    
    md.append("## Distributions")
    md.append("### Year Distribution")
    for year, count in year_dist.items():
        md.append(f"- {year}: {count}")
    md.append("")
    
    md.append("### Paper Role Distribution")
    for role, count in role_dist.items():
        md.append(f"- {role}: {count}")
    md.append("")
    
    md.append("### Risk Flags Distribution")
    for risk, count in risk_dist.items():
        md.append(f"- {risk if risk else 'None'}: {count}")
    md.append("")
    
    md.append("## Top 20 Papers by Score")
    top_20 = df.head(20)
    md.append("| Title | Year | Citations | Role | Risk Flags |")
    md.append("| :--- | :--- | :--- | :--- | :--- |")
    for _, row in top_20.iterrows():
        title = str(row['title'])[:80] + "..." if len(str(row['title'])) > 80 else str(row['title'])
        md.append(f"| {title} | {row['year']} | {row['citation_count']} | {row['paper_role_guess']} | {row['risk_flags']} |")
    md.append("")
    
    md.append("## Suspicious Papers List")
    # Exclusion terms check
    exclude_terms = ["video", "audio", "speech", "voice", "text detection", "watermark"]
    def is_suspicious(row):
        title = str(row['title']).lower()
        reasons = []
        if any(term in title for term in exclude_terms) and "image" not in title:
            reasons.append("exclusion_term_match")
        if pd.isna(row.get('citation_count')):
            reasons.append("missing_citation")
        if pd.isna(row.get('year')):
            reasons.append("missing_year")
        return ", ".join(reasons)

    df['audit_suspicious_reasons'] = df.apply(is_suspicious, axis=1)
    suspicious_df = df[df['audit_suspicious_reasons'] != ""]

    if suspicious_df.empty:
        md.append("No suspicious papers found.")
    else:
        md.append("| Title | Reasons |")
        md.append("| :--- | :--- |")
        for _, row in suspicious_df.iterrows():
            title = str(row['title'])[:80] + "..." if len(str(row['title'])) > 80 else str(row['title'])
            md.append(f"| {title} | {row['audit_suspicious_reasons']} |")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md))
    
    print(f"Audit complete. Results saved to {output_path}")
    return drift_count

if __name__ == "__main__":
    audit_corpus()
