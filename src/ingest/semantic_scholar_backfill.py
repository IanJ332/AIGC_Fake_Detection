import argparse
import requests
import time
import os
from src.utils.io import read_jsonl, write_jsonl
from src.utils.cost_tracker import cost_tracker

def fetch_ss_metadata(identifier):
    """Fetches metadata from Semantic Scholar API using DOI or title."""
    # identifier could be DOI or "title:..."
    base_url = f"https://api.semanticscholar.org/graph/v1/paper/{identifier}"
    params = {
        "fields": "title,abstract,citationCount,influentialCitationCount,externalIds,openAccessPdf,authors,year,venue"
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        cost_tracker.log_cost("SemanticScholar", "paper_lookup", 1, 0.0, f"ID: {identifier}")
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            print(f"SS API Error {response.status_code} for {identifier}")
            return None
    except Exception as e:
        print(f"Error fetching from Semantic Scholar for {identifier}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Backfill missing metadata using Semantic Scholar.")
    parser.add_argument("--input", default="corpus/raw_metadata/openalex_raw.jsonl", help="Path to input JSONL")
    args = parser.parse_args()

    candidates = read_jsonl(args.input)
    backfilled_data = []
    
    print(f"Starting backfill for {len(candidates)} candidates...")
    
    for i, paper in enumerate(candidates):
        # We backfill if abstract is missing or if we want to enrich citations
        identifier = None
        if paper.get("doi"):
            identifier = paper["doi"]
        elif paper.get("title"):
            identifier = f"title:{paper['title']}"
        
        if identifier:
            print(f"[{i+1}/{len(candidates)}] Backfilling: {paper.get('title')[:50]}...")
            ss_data = fetch_ss_metadata(identifier)
            
            if ss_data:
                # Fill missing abstract
                if not paper.get("abstract") and ss_data.get("abstract"):
                    paper["abstract"] = ss_data["abstract"]
                
                # Enrichment
                paper["influential_citation_count"] = ss_data.get("influentialCitationCount", 0)
                
                if ss_data.get("openAccessPdf") and not paper.get("pdf_url"):
                    paper["pdf_url"] = ss_data["openAccessPdf"].get("url")
                
                # External IDs
                if ss_data.get("externalIds"):
                    paper["external_ids"] = ss_data["externalIds"]

                # Only update citation count if OpenAlex was 0 or missing
                if (not paper.get("citation_count") or paper["citation_count"] == 0) and ss_data.get("citationCount"):
                    paper["citation_count"] = ss_data["citationCount"]
            
            time.sleep(1) # SS API rate limit for free tier is ~1 request/second
        
        backfilled_data.append(paper)
        
        # Limit backfill in Day 1 to avoid long runs if there are too many candidates
        if i >= 100: 
            print("Reached Day 1 backfill limit (100 papers). Skipping rest.")
            backfilled_data.extend(candidates[i+1:])
            break

    output_path = "corpus/raw_metadata/semantic_scholar_backfill.jsonl"
    write_jsonl(backfilled_data, output_path)
    print(f"Backfill complete. Saved to {output_path}")

if __name__ == "__main__":
    main()
