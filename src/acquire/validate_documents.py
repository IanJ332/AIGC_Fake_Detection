import argparse
import pandas as pd
import os
import json

def main():
    parser = argparse.ArgumentParser(description="Validate downloaded documents.")
    parser.add_argument("--registry", default="corpus/document_registry.csv", help="Path to registry CSV")
    args = parser.parse_args()

    if not os.path.exists(args.registry):
        print(f"Error: Registry {args.registry} not found.")
        return

    df = pd.read_csv(args.registry)
    
    # Checks
    total_rows = len(df)
    acquired_count = sum((df["pdf_downloaded"] == True) | (df["tei_downloaded"] == True))
    zero_byte_files = []
    missing_sha256 = []
    suspicious_size = []
    
    for _, row in df.iterrows():
        if row["pdf_downloaded"] or row["tei_downloaded"]:
            paper_id = row["paper_id"]
            path = f"corpus/pdfs/{paper_id}.pdf" if row["pdf_downloaded"] else f"corpus/tei_xml/{paper_id}.tei.xml"
            
            if os.path.exists(path):
                size = os.path.getsize(path)
                if size == 0:
                    zero_byte_files.append(paper_id)
                if size < 1000: # Less than 1KB is likely not a full PDF/XML
                    suspicious_size.append(f"{paper_id} ({size} bytes)")
            
            if pd.isna(row.get("sha256")) or row.get("sha256") == "":
                missing_sha256.append(paper_id)

    # Suspicious modality
    manifest_path = "corpus/manifest_100.csv"
    suspicious_modality = []
    if os.path.exists(manifest_path):
        manifest_df = pd.read_csv(manifest_path)
        for _, row in manifest_df.iterrows():
            title = str(row.get("title", "")).lower()
            modality = str(row.get("modality_scope", "")).lower()
            if any(kw in title for kw in ["audio", "speech", "voice"]):
                suspicious_modality.append(f"{row.get('title')} (Modality: {modality})")
            if "video" in title and "image" not in title:
                suspicious_modality.append(f"{row.get('title')} (Modality: {modality})")

    # Generate Report
    report_md = f"""# Day 2 Document Acquisition Report

## Summary
- **Total Rows in Registry**: {total_rows}
- **Documents Acquired**: {acquired_count} (Goal: >= 70)
- **Status**: {"PASSED" if acquired_count >= 70 else "FAILED"}

## Integrity Checks
- **Zero-byte files**: {len(zero_byte_files)}
- **Missing SHA256**: {len(missing_sha256)}
- **Suspiciously small files (<1KB)**: {len(suspicious_size)}
{", ".join(suspicious_size) if suspicious_size else "None"}

## Suspicious Modality Papers (Potentially non-image)
{chr(10).join([f"- {m}" for m in suspicious_modality]) if suspicious_modality else "None"}

## Registry Overview (Top 20)
| Paper ID | Title | PDF | TEI | Source | Error |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
    for _, row in df.head(20).iterrows():
        report_md += f"| {row['paper_id']} | {str(row['title'])[:50]}... | {row['pdf_downloaded']} | {row['tei_downloaded']} | {row['source_used']} | {row['download_error']} |\n"

    with open("docs/day2_document_acquisition_report.md", "w", encoding="utf-8") as f:
        f.write(report_md)
        
    # Generate Day 2 Status
    pdf_count = sum(df["pdf_downloaded"] == True)
    tei_count = sum(df["tei_downloaded"] == True)
    failed_count = total_rows - acquired_count
    manual_count = sum(df["needs_manual_review"] == True)
    
    # Try to get cost from report
    report_json_path = "corpus/download_logs/download_report.json"
    estimated_spend = 0.0
    if os.path.exists(report_json_path):
        with open(report_json_path, "r") as f:
            report_data = json.load(f)
            estimated_spend = report_data.get("total_cost_usd", 0.0)

    recommendation = "PROCEED" if acquired_count >= 70 else "CAUTION"
    if acquired_count < 50:
        recommendation = "BLOCKED"

    status_md = f"""# Day 2 Status Report

## Summary
- **Number of PDF downloaded**: {pdf_count}
- **Number of TEI XML downloaded**: {tei_count}
- **Total docs acquired**: {acquired_count}
- **Failed docs**: {failed_count}
- **Manual review docs**: {manual_count}
- **Estimated spend**: ${estimated_spend:.2f}

## Recommendation
**{recommendation}**
"""
    with open("docs/day2_status.md", "w", encoding="utf-8") as f:
        f.write(status_md)

    print(f"Validation complete. Reports saved to docs/")

if __name__ == "__main__":
    main()
