import os
import json
import re
import argparse

METRIC_KWS = ["accuracy", "acc", "auc", "ap", "f1", "eer", "precision", "recall", "roc", "robust", "psnr", "ssim"]
DATASET_KWS = ["GenImage", "Synthbuster", "ForenSynths", "CIFAKE", "FaceForensics", "Celeb-DF", "ImageNet", "COCO", "LAION"]
TABLE_CAPTION_REGEX = r"^\s*(Table|Tab\.|Table\s*[0-9]+|Table\s*[I|V|X]+)\b"

def is_numeric_dense(text):
    if not text: return False
    # Count digits and numeric-like characters (dots, commas, percent, plus/minus)
    numeric_chars = sum(c.isdigit() or c in ".,%±" for c in text)
    ratio = numeric_chars / len(text)
    # Tables usually have many numbers and whitespace separators
    if ratio > 0.2 and (len(text.split()) > 3):
        return True
    return False

def main():
    parser = argparse.ArgumentParser(description="Extract table candidates from sections.")
    parser.add_argument("--sections", default="corpus/sections/sections.jsonl", help="Path to sections JSONL")
    parser.add_argument("--out", default="corpus/tables/table_candidates.jsonl", help="Path to output table_candidates JSONL")
    args = parser.parse_args()
    
    output_path = args.out
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if not os.path.exists(args.sections):
        print(f"Error: {args.sections} not found.")
        return

    print(f"Extracting table candidates from {args.sections}...")
    candidates = []
    
    with open(args.sections, "r", encoding="utf-8") as f:
        for line in f:
            try:
                sec = json.loads(line)
                paper_id = sec["paper_id"]
                text = sec["text"]
                lines = text.split("\n")
                
                for l in lines:
                    l_stripped = l.strip()
                    if len(l_stripped) < 10: continue # Skip very short lines
                    
                    reason = None
                    # 1. Table Captions
                    if re.search(TABLE_CAPTION_REGEX, l_stripped, re.IGNORECASE):
                        reason = "table_caption"
                    # 2. Numeric Density
                    elif is_numeric_dense(l_stripped):
                        reason = "numeric_density"
                    # 3. Metric Keywords with some numbers
                    elif any(kw.lower() in l_stripped.lower() for kw in METRIC_KWS):
                        if sum(c.isdigit() for c in l_stripped) >= 2:
                            reason = "metric_keywords"
                    # 4. Dataset Keywords with some numbers
                    elif any(kw.lower() in l_stripped.lower() for kw in DATASET_KWS):
                        if sum(c.isdigit() for c in l_stripped) >= 2:
                            reason = "dataset_keywords"
                    
                    if reason:
                        candidates.append({
                            "paper_id": paper_id,
                            "page_num": sec["page_start"], 
                            "candidate_id": f"{paper_id}_C{len(candidates)+1}",
                            "text": l_stripped,
                            "reason": reason
                        })
            except Exception as e:
                continue
                    
    with open(output_path, "w", encoding="utf-8") as out_f:
        for c in candidates:
            out_f.write(json.dumps(c, ensure_ascii=False) + "\n")
            
    print(f"Extraction complete. Found {len(candidates)} candidates.")

if __name__ == "__main__":
    main()
