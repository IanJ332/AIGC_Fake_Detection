import pandas as pd
import json
import re
import argparse
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

# Expanded Entity Dictionaries
ENTITIES = {
    "dataset": [
        "GenImage", "Synthbuster", "ForenSynths", "CIFAKE", "FaceForensics++", 
        "Celeb-DF", "ImageNet", "COCO", "LAION", "DiffusionDB", "MS-COCO", 
        "ArtiFact", "AIGIBench", "WildFake", "DeepFakeDetection", "UniversalFakeDetect",
        "DFBench", "AI-GenBench", "FakeBench", "VCT2"
    ],
    "model_backbone": [
        "ResNet", "EfficientNet", "ViT", "CLIP", "DINO", "DINOv2", "DINOv3", 
        "CNN", "Xception", "Swin", "ConvNeXt", "SigLIP", "EVA", "MAE", "Vision Transformer",
        "VLM", "MLLM", "InstructBLIP", "BLIP", "LLaVA"
    ],
    "generator_family": [
        "GAN", "diffusion", "latent diffusion", "Stable Diffusion", "Midjourney", 
        "DALL-E", "Flux", "SDXL", "autoregressive", "StyleGAN", "BigGAN", "ProGAN"
    ],
    "metric": [
        "accuracy", "acc", "AUC", "AP", "F1", "EER", "precision", "recall", "ROC-AUC",
        "AUROC", "balanced accuracy"
    ],
    "distortion": [
        "JPEG", "blur", "resize", "compression", "WebP", "Gaussian noise", "crop", 
        "downsampling", "watermark", "perturbation"
    ],
    "method_keyword": [
        "DIRE", "FIRE", "reconstruction error", "frequency", "spectrum", "spectral", 
        "artifact", "co-occurrence", "CLIP-based", "zero-shot", "generalizable", 
        "universal detector", "attribution", "localization"
    ],
    "benchmark": [
        "GenImage", "Synthbuster", "DFBench", "AI-GenBench", "FakeBench"
    ],
    "robustness_condition": [
        "unseen generator", "cross-generator", "cross-domain", "in-the-wild", 
        "compressed", "social media", "robustness", "degradation"
    ]
}

def normalize_entity(entity):
    return entity.lower().strip()

def extract_entities(data_dir):
    data_dir = Path(data_dir)
    sections_path = data_dir / "sections" / "sections.jsonl"
    manifest_path = data_dir / "registry" / "manifest_100.csv"
    doc_reg_path = data_dir / "registry" / "document_registry.csv"
    
    if not sections_path.exists():
        print(f"Error: {sections_path} not found.")
        return

    # Load metadata for titles and years
    meta = None
    if manifest_path.exists():
        meta = pd.read_csv(manifest_path)
    elif doc_reg_path.exists():
        meta = pd.read_csv(doc_reg_path)
    
    titles = {}
    years = {}
    if meta is not None:
        if "paper_id" in meta.columns:
            titles = dict(zip(meta["paper_id"], meta["title"]))
            if "year" in meta.columns:
                years = dict(zip(meta["paper_id"], meta["year"]))
            elif "publish_year" in meta.columns:
                years = dict(zip(meta["paper_id"], meta["publish_year"]))

    results = []
    entity_id_counter = 1
    
    print(f"Extracting entities from {sections_path}...")
    with open(sections_path, "r", encoding="utf-8") as f:
        for line in tqdm(f):
            sect = json.loads(line)
            paper_id = sect["paper_id"]
            text = sect["text"]
            
            for etype, patterns in ENTITIES.items():
                for p in patterns:
                    # Match with word boundaries, case-insensitive
                    matches = re.finditer(r"\b" + re.escape(p) + r"\b", text, re.IGNORECASE)
                    for m in matches:
                        start, end = m.span()
                        # Context window
                        ctx_start = max(0, start - 100)
                        ctx_end = min(len(text), end + 100)
                        
                        results.append({
                            "entity_id": f"E{entity_id_counter:05d}",
                            "paper_id": paper_id,
                            "paper_title": titles.get(paper_id, "Unknown"),
                            "year": years.get(paper_id, "Unknown"),
                            "entity_type": etype,
                            "entity": p,
                            "normalized_entity": normalize_entity(p),
                            "section_type": sect["section_type"],
                            "section_heading": sect["section_heading"],
                            "evidence_anchor": sect["evidence_anchor"],
                            "context_snippet": text[ctx_start:ctx_end].replace("\n", " ").strip(),
                            "char_start": start,
                            "char_end": end
                        })
                        entity_id_counter += 1

    df = pd.DataFrame(results)
    out_dir = data_dir / "extracted"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    out_path = out_dir / "entities.csv"
    df.to_csv(out_path, index=False)
    print(f"Extracted {len(df)} entities to {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="/content/drive/MyDrive/AIGC/Data")
    args = parser.parse_args()
    extract_entities(args.data_dir)
