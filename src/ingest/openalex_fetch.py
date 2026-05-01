import argparse
import yaml
import requests
import time
import os
from src.utils.io import write_jsonl
from src.utils.cost_tracker import cost_tracker

def fetch_openalex_works(query, max_results=100):
    """Fetches works from OpenAlex API based on a search query."""
    base_url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "per_page": min(max_results, 100),
        "sort": "cited_by_count:desc"
    }
    
    results = []
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        cost_tracker.log_cost("OpenAlex", "works", 1, 0.0, f"Query: {query}")
    except Exception as e:
        print(f"Error fetching from OpenAlex for query '{query}': {e}")
    
    return results

def normalize_openalex_work(work, query_source):
    """Normalizes an OpenAlex work object into the required schema."""
    authors = [a.get("author", {}).get("display_name") for a in work.get("authorships", [])]
    concepts = [c.get("display_name") for c in work.get("concepts", [])]
    
    # Extract PDF URL if available
    pdf_url = None
    best_oa = work.get("best_oa_location")
    if best_oa and best_oa.get("pdf_url"):
        pdf_url = best_oa.get("pdf_url")

    return {
        "openalex_id": work.get("id"),
        "doi": work.get("doi"),
        "title": work.get("title"),
        "authors": authors,
        "year": work.get("publication_year"),
        "venue": work.get("host_venue", {}).get("display_name") if work.get("host_venue") else None,
        "citation_count": work.get("cited_by_count", 0),
        "source_url": work.get("primary_location", {}).get("landing_page_url"),
        "pdf_url": pdf_url,
        "landing_page_url": work.get("primary_location", {}).get("landing_page_url"),
        "abstract": None, # OpenAlex abstract is inverted index, needs processing or SS backfill
        "referenced_works": work.get("referenced_works", []),
        "concepts": concepts,
        "query_source": query_source
    }

def main():
    parser = argparse.ArgumentParser(description="Fetch candidate papers from OpenAlex.")
    parser.add_argument("--config", default="configs/corpus_query.yaml", help="Path to config file")
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    seed_queries = config.get("seed_queries", [])
    max_per_query = config.get("fetch_settings", {}).get("openalex_max_results_per_query", 50)
    
    all_raw_candidates = []
    seen_ids = set()

    for query in seed_queries:
        print(f"Fetching candidates for: {query}")
        works = fetch_openalex_works(query, max_results=max_per_query)
        for work in works:
            if work["id"] not in seen_ids:
                normalized = normalize_openalex_work(work, query)
                all_raw_candidates.append(normalized)
                seen_ids.add(work["id"])
        time.sleep(1) # Polite rate limiting

    output_path = "corpus/raw_metadata/openalex_raw.jsonl"
    write_jsonl(all_raw_candidates, output_path)
    print(f"Fetched {len(all_raw_candidates)} unique candidates. Saved to {output_path}")

if __name__ == "__main__":
    main()
