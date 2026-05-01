import argparse
import yaml
import requests
import time
import os
from src.utils.io import write_jsonl
from src.utils.cost_tracker import cost_tracker

def fetch_openalex_works(query, max_results=200, search_mode="search"):
    """Fetches works from OpenAlex API based on a search query and mode."""
    base_url = "https://api.openalex.org/works"
    
    # We always sort by cited_by_count:desc as requested
    params = {
        "per_page": 100,
        "sort": "cited_by_count:desc"
    }
    
    # Modes implementation
    if search_mode == "search":
        params["search"] = query
    elif search_mode == "title_abs":
        params["filter"] = f"title_and_abstract.search:{query}"
    elif search_mode == "pdf_oa":
        # high-quality pass with PDF required
        params["filter"] = f"title_and_abstract.search:{query},has_content.pdf:true"
    
    results = []
    try:
        page = 1
        while len(results) < max_results:
            params["page"] = page
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            page_results = data.get("results", [])
            if not page_results:
                break
            results.extend(page_results)
            if len(page_results) < params["per_page"]:
                break
            page += 1
            time.sleep(0.2)
            
        cost_tracker.log_cost("OpenAlex", "works", page, 0.0, f"Query: {query} ({search_mode})")
    except Exception as e:
        print(f"Error fetching from OpenAlex for query '{query}' [{search_mode}]: {e}")
    
    return results[:max_results]

def normalize_openalex_work(work, metadata):
    """Normalizes an OpenAlex work object into the required schema."""
    authors = [a.get("author", {}).get("display_name") for a in work.get("authorships", [])]
    concepts = [c.get("display_name") for c in work.get("concepts", [])]
    
    pdf_url = None
    best_oa = work.get("best_oa_location")
    if best_oa and best_oa.get("pdf_url"):
        pdf_url = best_oa.get("pdf_url")

    venue_name = None
    if work.get("primary_location") and work.get("primary_location").get("source"):
        venue_name = work.get("primary_location").get("source").get("display_name")

    # Reconstruct abstract from inverted index
    abstract = None
    inverted_index = work.get("abstract_inverted_index")
    if inverted_index:
        try:
            # abstract_inverted_index is a dict {word: [pos1, pos2, ...]}
            # We want to reconstruct the list of words
            word_list = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_list.append((pos, word))
            word_list.sort()
            abstract = " ".join([w[1] for w in word_list])
        except Exception:
            abstract = None

    norm = {
        "openalex_id": work.get("id"),
        "doi": work.get("doi"),
        "title": work.get("title"),
        "authors": authors,
        "year": work.get("publication_year"),
        "venue": venue_name,
        "citation_count": work.get("cited_by_count", 0),
        "source_url": work.get("primary_location", {}).get("landing_page_url") if work.get("primary_location") else None,
        "pdf_url": pdf_url,
        "landing_page_url": work.get("primary_location", {}).get("landing_page_url") if work.get("primary_location") else None,
        "abstract": abstract,
        "referenced_works": work.get("referenced_works", []),
        "concepts": concepts,
    }
    norm.update(metadata)
    return norm

def main():
    parser = argparse.ArgumentParser(description="Fetch candidate papers from OpenAlex.")
    parser.add_argument("--config", default="configs/corpus_query.yaml", help="Path to config file")
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Config file {args.config} not found.")
        return

    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    query_groups = config.get("query_groups", {})
    settings = config.get("settings", {})
    max_per_query = settings.get("openalex_max_results_per_query", 200)
    
    all_raw_candidates = []
    seen_ids = set()

    search_modes = ["search", "title_abs", "pdf_oa"]

    for group_name, queries in query_groups.items():
        print(f"\nProcessing Group: {group_name}")
        for query in queries:
            for mode in search_modes:
                print(f"  Fetching: {query} [{mode}]")
                works = fetch_openalex_works(query, max_results=max_per_query, search_mode=mode)
                for rank, work in enumerate(works, 1):
                    work_id = work["id"]
                    metadata = {
                        "query_group": group_name,
                        "query_text": query,
                        "search_mode": mode,
                        "openalex_rank": rank
                    }
                    if work_id not in seen_ids:
                        normalized = normalize_openalex_work(work, metadata)
                        all_raw_candidates.append(normalized)
                        seen_ids.add(work_id)
                time.sleep(0.5)

    output_path = "corpus/raw_metadata/openalex_raw.jsonl"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    write_jsonl(all_raw_candidates, output_path)
    print(f"\nFetched {len(all_raw_candidates)} unique candidates. Saved to {output_path}")

if __name__ == "__main__":
    main()
