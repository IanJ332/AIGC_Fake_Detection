import json
import re
import pandas as pd
import argparse
from pathlib import Path

def normalize_value(val_str):
    if not val_str:
        return None
    val_str = val_str.lower().replace(",", "")
    
    # Handle multipliers
    multiplier = 1.0
    if "b" in val_str or "billion" in val_str:
        multiplier = 1e9
    elif "m" in val_str or "million" in val_str:
        multiplier = 1e6
    elif "k" in val_str or "thousand" in val_str:
        multiplier = 1e3
        
    # Extract numeric part
    nums = re.findall(r"(\d+\.?\d*)", val_str)
    if nums:
        try:
            return float(nums[0]) * multiplier
        except ValueError:
            return None
    return None

def extract_numeric_claims(data_dir):
    data_dir = Path(data_dir)
    sections_path = data_dir / "sections" / "sections.jsonl"
    tables_path = data_dir / "tables" / "table_candidates.jsonl"
    output_path = data_dir / "extracted" / "numeric_claims.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    claims = []
    claim_id_counter = 1
    
    # Regex patterns
    patterns = {
        "parameter_count": [
            r"(\d+\.?\d*\s*[m|b|million|billion]?)\s*parameters",
            r"#params[:\s]*(\d+\.?\d*\s*[m|b|million|billion]?)",
            r"params[:\s]*(\d+\.?\d*\s*[m|b|million|billion]?)",
            r"(\d+\.?\d*[m|b])\s*params",
        ],
        "model_size": [
            r"(\d+\.?\d*\s*[m|b|million|billion]?)\s*model",
            r"size of\s*(\d+\.?\d*\s*[m|b|million|billion]?)",
        ],
        "dataset_size": [
            r"(\d+[\d,.]*\s*[m|b|million|billion]?)\s*images",
            r"(\d+[\d,.]*\s*[m|b|million|billion]?)\s*samples",
            r"dataset consists of\s*(\d+[\d,.]*\s*[m|b|million|billion]?)",
            r"training set contains\s*(\d+[\d,.]*\s*[m|b|million|billion]?)",
            r"million-scale",
        ],
        "sota_claim": [
            r"state-of-the-art",
            r"sota",
            r"outperforms previous",
            r"best performance",
            r"achieves",
        ],
        "augmentation_flag": [
            r"data augmentation",
            r"without augmentation",
            r"no augmentation",
            r"flip", r"crop", r"color jitter", r"randaugment", r"mixup", r"cutmix"
        ],
        "architecture_type": [
            r"transformer", r"vit", r"clip", r"swin", r"resnet", r"cnn", r"mllm", r"vlm"
        ]
    }
    
    def process_text(text, paper_id, source_type):
        nonlocal claim_id_counter
        text_lower = text.lower()
        
        for claim_type, regex_list in patterns.items():
            for pattern in regex_list:
                matches = re.finditer(pattern, text_lower)
                for match in matches:
                    raw_text = match.group(0)
                    value_numeric = None
                    unit = None
                    normalized_value = None
                    
                    if claim_type in ["parameter_count", "model_size", "dataset_size"]:
                        try:
                            val_str = match.group(1) if match.groups() else match.group(0)
                            normalized_value = normalize_value(val_str)
                            value_numeric = normalized_value # simplified
                        except:
                            pass
                    
                    # Heuristic for architecture
                    arch = None
                    for a in ["transformer", "vit", "clip", "swin", "resnet", "cnn", "mllm", "vlm"]:
                        if a in text_lower:
                            arch = a.upper()
                            break
                            
                    claims.append({
                        "claim_id": f"C{claim_id_counter:05d}",
                        "paper_id": paper_id,
                        "claim_type": claim_type,
                        "entity": arch,
                        "value_numeric": value_numeric,
                        "unit": None,
                        "normalized_value": normalized_value,
                        "benchmark": None,
                        "metric": None,
                        "condition": source_type,
                        "evidence_anchor": source_type,
                        "raw_text": raw_text,
                        "confidence": 0.8
                    })
                    claim_id_counter += 1

    # Process sections
    if sections_path.exists():
        print(f"Processing sections from {sections_path}...")
        with open(sections_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                if not line.strip(): continue
                row = json.loads(line)
                process_text(row.get("text", ""), row.get("paper_id"), f"section:{row.get('section_type')}")

    # Process tables
    if tables_path.exists():
        print(f"Processing tables from {tables_path}...")
        with open(tables_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                if not line.strip(): continue
                row = json.loads(line)
                table_text = row.get("caption", "") + " " + str(row.get("data", ""))
                process_text(table_text, row.get("paper_id"), "table")

    df = pd.DataFrame(claims)
    if not df.empty:
        df.to_csv(output_path, index=False)
        print(f"Extracted {len(df)} numeric claims to {output_path}")
    else:
        # Create empty dataframe with columns if no claims found
        columns = ["claim_id", "paper_id", "claim_type", "entity", "value_numeric", "unit", "normalized_value", "benchmark", "metric", "condition", "evidence_anchor", "raw_text", "confidence"]
        pd.DataFrame(columns=columns).to_csv(output_path, index=False)
        print(f"No numeric claims found. Created empty file at {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    args = parser.parse_args()
    extract_numeric_claims(args.data_dir)
