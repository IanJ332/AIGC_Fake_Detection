import argparse
import pandas as pd
import os
import json

def main():
    parser = argparse.ArgumentParser(description="Validate Day 3 parsing results.")
    parser.add_argument("--registry", default="corpus/parse_registry.csv", help="Path to parse registry")
    parser.add_argument("--sections", default="corpus/sections/sections.jsonl", help="Path to sections JSONL")
    parser.add_argument("--tables", default="corpus/tables/table_candidates.jsonl", help="Path to tables JSONL")
    args = parser.parse_args()

    if not os.path.exists(args.registry):
        print(f"Error: Registry {args.registry} not found.")
        return

    df = pd.read_csv(args.registry)
    
    # Load sections
    sections = []
    if os.path.exists(args.sections):
        with open(args.sections, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    sections.append(json.loads(line))
                except:
                    continue
                
    # Load tables
    tables = []
    if os.path.exists(args.tables):
        with open(args.tables, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    tables.append(json.loads(line))
                except:
                    continue

    # Metrics
    total_attempted = len(df)
    success_count = int(df["parse_success"].sum())
    failed_count = total_attempted - success_count
    needs_ocr = int(df["needs_ocr"].sum())
    avg_chars = float(df[df["parse_success"] == True]["total_chars"].mean()) if success_count > 0 else 0.0
    
    # Section metrics
    sec_counts = {}
    for s in sections:
        t = s["section_type"]
        sec_counts[t] = sec_counts.get(t, 0) + 1
        
    papers_with_abstract = len(set(s["paper_id"] for s in sections if s["section_type"] in ["abstract", "introduction"]))
    core_sections = ["method", "experiment", "results"]
    papers_with_core = len(set(s["paper_id"] for s in sections if s["section_type"] in core_sections))
    
    # Criteria check
    passed = (success_count >= 65 and avg_chars >= 10000 and len(sections) > 0 and papers_with_abstract >= 50 and papers_with_core >= 40)
    
    report_md = f"""# Day 3 Parse Report

## Summary
- **Total Attempted PDFs**: {total_attempted}
- **Successfully Parsed**: {success_count} (Goal: >= 65)
- **Failed**: {failed_count}
- **Needs OCR**: {needs_ocr}
- **Average Chars per Paper**: {avg_chars:,.2f} (Goal: >= 10,000)
- **Status**: {"PASSED" if passed else "FAILED"}

## Section Analysis
- **Total Sections Extracted**: {len(sections)}
- **Sections by Type**:
"""
    for t, c in sorted(sec_counts.items()):
        report_md += f"  - {t}: {c}\n"

    report_md += f"""
- **Papers with Abstract/Intro**: {papers_with_abstract} (Goal: >= 50)
- **Papers with Method/Exp/Results**: {papers_with_core} (Goal: >= 40)

## Table Candidates
- **Total Table Candidate Rows**: {len(tables)}

## Examples of Evidence Anchors
"""
    for s in sections[:10]:
        report_md += f"- {s['evidence_anchor']}\n"

    report_md += "\n## Suspicious Modality Papers (Carried Forward)\n"
    registry_path = "corpus/document_registry.csv"
    if os.path.exists(registry_path):
        reg_df = pd.read_csv(registry_path)
        suspicious = reg_df[reg_df["title"].str.contains("video|audio|speech|voice", case=False, na=False)]
        if not suspicious.empty:
            for _, row in suspicious.iterrows():
                report_md += f"- {row['paper_id']}: {row['title']}\n"
        else:
            report_md += "None identified.\n"
    else:
        report_md += "Registry not found.\n"

    with open("docs/day3_parse_report.md", "w", encoding="utf-8") as f:
        f.write(report_md)
        
    print(f"Validation complete. Report saved to docs/day3_parse_report.md")

if __name__ == "__main__":
    main()
