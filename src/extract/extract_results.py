import pandas as pd
import json
import re
import argparse
from pathlib import Path
from tqdm import tqdm

# Minimal dictionaries for tagging results
DATASETS = [
    "GenImage", "Synthbuster", "ForenSynths", "CIFAKE", "FaceForensics++", 
    "Celeb-DF", "ImageNet", "COCO", "LAION", "DiffusionDB", "MS-COCO", 
    "ArtiFact", "AIGIBench", "WildFake", "DeepFakeDetection", "UniversalFakeDetect"
]
METRICS = [
    "accuracy", "acc", "AUC", "AP", "F1", "EER", "precision", "recall", "ROC-AUC", "AUROC"
]

def get_first(row, keys, default=""):
    for k in keys:
        if k in row and row[k] not in [None, ""]:
            return row[k]
    return default

def extract_results(data_dir):
    data_dir = Path(data_dir)
    tables_path = data_dir / "tables" / "table_candidates.jsonl"
    manifest_path = data_dir / "registry" / "manifest_100.csv"
    doc_reg_path = data_dir / "registry" / "document_registry.csv"
    
    if not tables_path.exists():
        print(f"Error: {tables_path} not found.")
        return

    # Metadata
    meta = None
    if manifest_path.exists(): meta = pd.read_csv(manifest_path)
    elif doc_reg_path.exists(): meta = pd.read_csv(doc_reg_path)
    
    titles = {}
    years = {}
    if meta is not None:
        if "paper_id" in meta.columns:
            if "title" in meta.columns:
                titles = dict(zip(meta["paper_id"], meta["title"]))
            if "year" in meta.columns: years = dict(zip(meta["paper_id"], meta["year"]))
            elif "publish_year" in meta.columns: years = dict(zip(meta["paper_id"], meta["publish_year"]))

    results = []
    result_id_counter = 1
    
    # Result-like keywords for low-confidence extraction
    RESULT_KEYWORDS = ["accuracy", "auc", "f1", "ap", "benchmark", "robust", "jpeg", "compression", "eer"]

    print(f"Extracting results from {tables_path}...")
    with open(tables_path, "r", encoding="utf-8") as f:
        for line in tqdm(f):
            row = json.loads(line)
            paper_id = get_first(row, ["paper_id"], "unknown")
            text = get_first(row, ["text", "raw_text", "candidate_text", "content", "line"], "")
            evidence_anchor = get_first(row, ["evidence_anchor", "section_id", "candidate_id"], f"{paper_id}:table_candidate")
            
            if not text:
                continue
            
            dataset_guess = next((d for d in DATASETS if re.search(r"\b" + re.escape(d) + r"\b", text, re.IGNORECASE)), "unknown")
            metric_guess = next((m for m in METRICS if re.search(r"\b" + re.escape(m) + r"\b", text, re.IGNORECASE)), "unknown")
            
            # Numeric values: 95.3, 95.3%, 0.953
            vals = re.findall(r"\b(\d{1,3}\.\d{1,2}%?|0\.\d{3,4})\b", text)
            
            cond_patterns = {
                "clean": r"clean|orig", "JPEG": r"jpeg|jpg", "blur": r"blur", 
                "compression": r"compress", "cross-generator": r"cross|transfer", 
                "unseen": r"unseen", "robust": r"robust"
            }
            cond_guess = next((c for c, p in cond_patterns.items() if re.search(p, text, re.IGNORECASE)), "unknown")
            
            has_result_keyword = any(k in text.lower() for k in RESULT_KEYWORDS)

            if vals and (dataset_guess != "unknown" or metric_guess != "unknown" or has_result_keyword):
                for v in vals:
                    # Normalize numeric value
                    v_num = v.replace("%", "")
                    try:
                        v_float = float(v_num)
                    except:
                        v_float = None
                    
                    # Confidence scoring
                    if dataset_guess != "unknown" and metric_guess != "unknown": 
                        conf = "high"
                    elif dataset_guess != "unknown" or metric_guess != "unknown": 
                        conf = "medium"
                    else:
                        conf = "low"
                    
                    results.append({
                        "result_id": f"R{result_id_counter:05d}",
                        "paper_id": paper_id,
                        "paper_title": titles.get(paper_id, "Unknown"),
                        "year": years.get(paper_id, "Unknown"),
                        "dataset_guess": dataset_guess,
                        "metric_guess": metric_guess,
                        "value_guess": v,
                        "value_numeric": v_float,
                        "value_scale_guess": "percentage" if "%" in v else "decimal",
                        "condition_guess": cond_guess,
                        "model_guess": "unknown",
                        "evidence_anchor": evidence_anchor,
                        "raw_text": text.strip(),
                        "confidence": conf
                    })
                    result_id_counter += 1

    columns = [
        "result_id", "paper_id", "paper_title", "year",
        "dataset_guess", "metric_guess", "value_guess",
        "value_numeric", "value_scale_guess",
        "condition_guess", "model_guess",
        "evidence_anchor", "raw_text", "confidence"
    ]
    df = pd.DataFrame(results, columns=columns)
    out_dir = data_dir / "extracted"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    out_path = out_dir / "result_tuples.csv"
    df.to_csv(out_path, index=False)
    print(f"Extracted {len(df)} result tuples to {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="/content/drive/MyDrive/AIGC/Data")
    args = parser.parse_args()
    extract_results(args.data_dir)
