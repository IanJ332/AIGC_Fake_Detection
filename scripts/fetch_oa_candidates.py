import argparse
import requests
import pandas as pd
import time
import os
import re

QUERIES = [
    ("synthetic media forensics", "multimedia_forensics"),
    ("image forgery detection", "image_forgery_detection"),
    ("image manipulation detection", "image_manipulation_detection"),
    ("copy-move forgery detection", "image_forgery_detection"),
    ("image splicing detection", "image_forgery_detection"),
    ("face forgery detection", "image_forgery_detection"),
    ("deepfake detection visual forensics", "deepfake_visual_forensics"),
    ("deepfake image detection", "deepfake_visual_forensics"),
    ("deepfake video detection forensics", "deepfake_visual_forensics"),
    ("AI-generated image detection", "generated_image_detection"),
    ("synthetic image detection", "generated_image_detection"),
    ("GAN generated image detection", "generated_image_detection"),
    ("diffusion generated image detection", "generated_image_detection"),
    ("fake image detection", "generated_image_detection"),
    ("multimedia forensics generated media", "multimedia_forensics"),
    ("image inpainting forgery detection", "image_forgery_detection"),
    ("generated image attribution", "generated_image_detection"),
    ("survey visual synthetic media forensics", "benchmark_or_survey"),
    ("benchmark visual synthetic media forensics", "benchmark_or_survey")
]

PAYWALLED_DOMAINS = ["ieee.org", "acm.org", "springer.com", "sciencedirect.com", "wiley.com"]

def get_best_pdf_url(work):
    best_url = None
    
    # Check open access URL first
    if work.get("open_access", {}).get("is_oa") and work.get("open_access", {}).get("oa_url"):
        oa_url = work["open_access"]["oa_url"]
        if any(d in oa_url for d in PAYWALLED_DOMAINS):
            pass
        else:
            best_url = oa_url
            
    # Check locations
    for loc in work.get("locations", []):
        url = loc.get("pdf_url")
        if url and not any(d in url for d in PAYWALLED_DOMAINS):
            if best_url is None or "arxiv.org" in url or "thecvf.com" in url:
                best_url = url
                
    # If still none, and the primary location has a pdf_url, take it as long as it's not paywalled
    if best_url is None:
        url = work.get("primary_location", {}).get("pdf_url")
        if url and not any(d in url for d in PAYWALLED_DOMAINS):
            best_url = url

    return best_url

def fetch_candidates(max_results=500):
    candidates = []
    seen_ids = set()
    
    for query, scope_family in QUERIES:
        if len(candidates) >= max_results:
            break
            
        print(f"Querying: {query}")
        url = f"https://api.openalex.org/works?search={requests.utils.quote(query)}&per-page=50&filter=has_pdf_url:true"
        
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code != 200:
                continue
                
            data = resp.json()
            for work in data.get("results", []):
                work_id = work.get("id", "").split("/")[-1]
                if not work_id:
                    work_id = f"OA{len(candidates)+1:04d}"
                    
                if work_id in seen_ids:
                    continue
                    
                pdf_url = get_best_pdf_url(work)
                if not pdf_url:
                    continue
                    
                # Abstract
                abstract_inverted = work.get("abstract_inverted_index", {})
                abstract = ""
                if abstract_inverted:
                    word_index = []
                    for word, positions in abstract_inverted.items():
                        for pos in positions:
                            word_index.append((pos, word))
                    word_index.sort()
                    abstract = " ".join([w for _, w in word_index])
                
                # Authors
                authors = ", ".join([a.get("author", {}).get("display_name", "") for a in work.get("authorships", [])])
                
                # Refs
                refs = ",".join([r.split("/")[-1] for r in work.get("referenced_works", [])])
                
                # Venue
                venue = work.get("primary_location", {}).get("source", {})
                venue_name = venue.get("display_name", "") if venue else ""
                
                candidates.append({
                    "paper_id": f"C{len(candidates)+1:04d}",
                    "id": work_id,
                    "title": work.get("title", ""),
                    "authors": authors,
                    "year": work.get("publication_year", ""),
                    "venue": venue_name,
                    "citation_count": work.get("cited_by_count", 0),
                    "source_url": work.get("id", ""),
                    "pdf_url": pdf_url,
                    "abstract": abstract,
                    "referenced_works": refs,
                    "scope_family": scope_family
                })
                seen_ids.add(work_id)
                
                if len(candidates) >= max_results:
                    break
                    
        except Exception as e:
            print(f"Error fetching {query}: {e}")
            
        time.sleep(1) # Polite delay
        
    return candidates

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--max-results", type=int, default=500, help="Maximum candidates to fetch")
    args = parser.parse_args()
    
    candidates = fetch_candidates(args.max_results)
    print(f"Fetched {len(candidates)} candidates.")
    
    df = pd.DataFrame(candidates)
    if len(df) > 0:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        df.to_csv(args.out, index=False)
        print(f"Saved to {args.out}")
    else:
        print("No candidates found.")

if __name__ == "__main__":
    main()
