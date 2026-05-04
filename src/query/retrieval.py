import json
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import joblib
import os

def retrieve_sections(query, data_dir, top_k=5):
    data_dir = Path(data_dir)
    sections_path = data_dir / "sections" / "sections.jsonl"
    index_path = data_dir / "index" / "tfidf_sections.joblib"
    
    if not sections_path.exists():
        return []
    
    # Load or build index
    if index_path.exists():
        data = joblib.load(index_path)
        vectorizer = data["vectorizer"]
        tfidf_matrix = data["tfidf_matrix"]
        sections = data["sections"]
    else:
        print("Building TF-IDF index for sections...")
        sections = []
        with open(sections_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                if not line.strip(): continue
                sections.append(json.loads(line))
        
        if not sections:
            return []
            
        texts = [s.get("text", "") for s in sections]
        vectorizer = TfidfVectorizer(stop_words='english', max_features=10000)
        tfidf_matrix = vectorizer.fit_transform(texts)
        
        # Cache index
        os.makedirs(index_path.parent, exist_ok=True)
        joblib.dump({
            "vectorizer": vectorizer,
            "tfidf_matrix": tfidf_matrix,
            "sections": sections
        }, index_path)
    
    # Query
    query_vec = vectorizer.transform([query])
    similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    top_indices = similarities.argsort()[-top_k:][::-1]
    
    results = []
    for idx in top_indices:
        if similarities[idx] > 0:
            s = sections[idx]
            results.append({
                "paper_id": s["paper_id"],
                "section_type": s["section_type"],
                "text": s["text"],
                "score": float(similarities[idx])
            })
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--query", required=True)
    args = parser.parse_args()
    
    results = retrieve_sections(args.query, args.data_dir)
    for r in results:
        print(f"[{r['score']:.3f}] {r['paper_id']} - {r['section_type']}: {r['text'][:200]}...")
