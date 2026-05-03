import os
import json
import re
import argparse

# Refined Heading Patterns with better coverage
SECTION_PATTERNS = [
    ("abstract", r"^\s*(Abstract)\b"),
    ("introduction", r"^\s*([I1]\.?\s*|Section\s*1\s*)?(Introduction)\b"),
    ("related_work", r"^\s*([II2]\.?\s*|Section\s*2\s*)?(Related Work|Background|Literature Review)\b"),
    ("method", r"^\s*([III34]\.?\s*)?(Proposed\s+)?(Method|Approach|Framework|Model|Methodology)\b"),
    ("dataset", r"\b(Dataset|Data|Benchmark|Data Collection)\b"),
    ("experiment", r"\b(Experiments|Experimental Setup|Implementation|Experimental Details)\b"),
    ("results", r"\b(Results|Evaluation|Performance|Experimental Results)\b"),
    ("discussion", r"^\s*([IV678]\.?\s*)?(Discussion|Analysis|Ablation Study)\b"),
    ("limitation", r"^\s*(Limitation|Limitations)\b"),
    ("conclusion", r"^\s*(Conclusion|Concluding Remarks|Conclusions)\b"),
    ("references", r"^\s*(References|Bibliography)\b")
]

def segment_sections(data):
    sections = []
    current_section = {
        "section_type": "unknown",
        "section_heading": None,
        "page_start": 1,
        "text_blocks": []
    }
    
    # Pre-process all blocks into a flat list
    all_blocks = []
    for p in data.get("pages", []):
        for b in p.get("blocks", []):
            all_blocks.append({**b, "page_num": p["page_num"]})
            
    for b in all_blocks:
        text = b["text"].strip()
        found_heading = False
        
        # Heading heuristics: short, often numeric prefix, matched by pattern
        if len(text) < 60:
            for s_type, pattern in SECTION_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    # Close current section
                    if current_section["text_blocks"]:
                        current_section["page_end"] = current_section["text_blocks"][-1]["page_num"]
                        current_section["text"] = "\n".join([tb["text"] for tb in current_section["text_blocks"]])
                        current_section["char_count"] = len(current_section["text"])
                        sections.append(current_section)
                    
                    current_section = {
                        "section_type": s_type,
                        "section_heading": text,
                        "page_start": b["page_num"],
                        "text_blocks": [b],
                    }
                    found_heading = True
                    break
        
        if not found_heading:
            current_section["text_blocks"].append(b)
            
    # Close last section
    if current_section["text_blocks"]:
        current_section["page_end"] = current_section["text_blocks"][-1]["page_num"]
        current_section["text"] = "\n".join([tb["text"] for tb in current_section["text_blocks"]])
        current_section["char_count"] = len(current_section["text"])
        sections.append(current_section)
        
    return sections

def main():
    parser = argparse.ArgumentParser(description="Segment parsed JSON into sections.")
    parser.add_argument("--parsed-dir", default=None, help="Directory with parsed JSONs")
    parser.add_argument("--data-dir", default=None, help="Base data directory")
    args = parser.parse_args()
    
    data_dir = args.data_dir if args.data_dir else "corpus"
    parsed_dir = args.parsed_dir if args.parsed_dir else f"{data_dir}/parsed"
    output_path = f"{data_dir}/sections/sections.jsonl"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if not os.path.exists(parsed_dir):
        print(f"Error: Directory {parsed_dir} not found.")
        return

    files = [f for f in os.listdir(parsed_dir) if f.endswith(".json")]
    print(f"Segmenting {len(files)} files...")
    
    with open(output_path, "w", encoding="utf-8") as out_f:
        for filename in files:
            try:
                with open(os.path.join(parsed_dir, filename), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                paper_id = data["paper_id"]
                sections = segment_sections(data)
                
                for s in sections:
                    row = {
                        "section_id": f"{paper_id}_{s['section_type']}_{s['page_start']}",
                        "paper_id": paper_id,
                        "title": data.get("title", "Unknown"),
                        "year": data.get("year"),
                        "section_type": s["section_type"],
                        "section_heading": s["section_heading"],
                        "page_start": s["page_start"],
                        "page_end": s["page_end"],
                        "text": s["text"],
                        "char_count": s["char_count"],
                        "evidence_anchor": f"{paper_id}:p{s['page_start']}-p{s['page_end']}:{s['section_type']}"
                    }
                    out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"  Error processing {filename}: {e}")
                
    print(f"Segmentation complete. Saved to {output_path}")

if __name__ == "__main__":
    main()
