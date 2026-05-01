import argparse
import pandas as pd
import requests
import os
import time
import json
import hashlib
from src.utils.cost_tracker import cost_tracker

# Constants
USER_AGENT = "AIGC-Fake-Detection-Research/1.0 (mailto:ian@example.com)"
MAX_RETRIES = 3
TIMEOUT = 30
# OpenAlex Content API estimated tracking cost
OPENALEX_CONTENT_API_UNIT_COST = 0.01 

def get_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def download_file(url, output_path, dry_run=False, api_key=None):
    if dry_run:
        print(f"    [DRY-RUN] Would download {url}")
        return True, None
    
    headers = {"User-Agent": USER_AGENT}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=TIMEOUT, stream=True)
            if response.status_code == 200:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True, None
            elif response.status_code == 404:
                return False, "404 Not Found"
            else:
                print(f"    Attempt {attempt+1} failed: {response.status_code}")
                time.sleep(1)
        except Exception as e:
            print(f"    Attempt {attempt+1} error: {e}")
            time.sleep(1)
    return False, f"Failed after {MAX_RETRIES} attempts"

def extract_id(openalex_url):
    if not openalex_url or not isinstance(openalex_url, str):
        return None
    return openalex_url.split("/")[-1]

def main():
    parser = argparse.ArgumentParser(description="Download PDFs and TEI XML for the corpus.")
    parser.add_argument("--manifest", default="corpus/manifest_100.csv", help="Path to manifest CSV")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without downloading")
    parser.add_argument("--force", action="store_true", help="Force download even if files exist")
    args = parser.parse_args()

    if not os.path.exists(args.manifest):
        print(f"Error: Manifest {args.manifest} not found.")
        return

    df = pd.read_csv(args.manifest)
    registry = []
    
    api_key = os.environ.get("OPENALEX_API_KEY")
    
    total_cost = 0.0
    
    print(f"Starting acquisition for {len(df)} papers...")
    
    for idx, row in df.iterrows():
        paper_id = f"P{idx+1:03d}"
        title_str = str(row.get('title', 'Unknown Title'))
        # Sanitize for console printing to avoid UnicodeEncodeError on some Windows terminals
        safe_title = title_str.encode('ascii', 'replace').decode('ascii')
        print(f"[{idx+1}/100] {paper_id}: {safe_title[:60]}...")
        
        pdf_path = f"corpus/pdfs/{paper_id}.pdf"
        tei_path = f"corpus/tei_xml/{paper_id}.tei.xml"
        
        status = {
            "paper_id": paper_id,
            "openalex_id": row.get("openalex_id"),
            "doi": row.get("doi"),
            "title": row.get("title"),
            "pdf_downloaded": False,
            "tei_downloaded": False,
            "source_used": None,
            "license": row.get("license") if pd.notna(row.get("license")) else "unknown",
            "download_error": None,
            "file_size_bytes": 0,
            "sha256": None,
            "needs_manual_review": False
        }

        # 1. Try manifest pdf_url
        pdf_url = row.get("pdf_url")
        if pdf_url and isinstance(pdf_url, str) and (not os.path.exists(pdf_path) or args.force):
            print(f"  Trying manifest PDF: {pdf_url}")
            success, error = download_file(pdf_url, pdf_path, args.dry_run)
            if success:
                status["pdf_downloaded"] = True
                status["source_used"] = "manifest_pdf_url"
                if not args.dry_run:
                    status["file_size_bytes"] = os.path.getsize(pdf_path)
                    status["sha256"] = get_sha256(pdf_path)
            else:
                status["download_error"] = f"Manifest PDF error: {error}"

        # 2. Try OpenAlex Content API (if key exists)
        work_id = extract_id(row.get("openalex_id"))
        if api_key and work_id and not status["pdf_downloaded"]:
            # Try TEI first
            tei_url = f"https://content.openalex.org/works/{work_id}.grobid-xml"
            if not os.path.exists(tei_path) or args.force:
                print(f"  Trying OpenAlex Content TEI: {tei_url}")
                success, error = download_file(tei_url, tei_path, args.dry_run, api_key=api_key)
                if success:
                    status["tei_downloaded"] = True
                    status["source_used"] = "openalex_content_tei"
                    total_cost += OPENALEX_CONTENT_API_UNIT_COST
                    cost_tracker.log_cost("OpenAlex", "content_tei", 1, OPENALEX_CONTENT_API_UNIT_COST, f"ID: {work_id}")
            
            # Try PDF if TEI failed or not available
            if not status["tei_downloaded"] and (not os.path.exists(pdf_path) or args.force):
                oa_pdf_url = f"https://content.openalex.org/works/{work_id}.pdf"
                print(f"  Trying OpenAlex Content PDF: {oa_pdf_url}")
                success, error = download_file(oa_pdf_url, pdf_path, args.dry_run, api_key=api_key)
                if success:
                    status["pdf_downloaded"] = True
                    status["source_used"] = "openalex_content_pdf"
                    total_cost += OPENALEX_CONTENT_API_UNIT_COST
                    cost_tracker.log_cost("OpenAlex", "content_pdf", 1, OPENALEX_CONTENT_API_UNIT_COST, f"ID: {work_id}")
                    if not args.dry_run:
                        status["file_size_bytes"] = os.path.getsize(pdf_path)
                        status["sha256"] = get_sha256(pdf_path)

        if not status["pdf_downloaded"] and not status["tei_downloaded"]:
            status["needs_manual_review"] = True
            if not status["download_error"]:
                status["download_error"] = "No accessible documents found"

        registry.append(status)
        
        if total_cost >= 2.0:
            print("Budget limit reached ($2). Stopping.")
            break
            
        time.sleep(0.5) # Polite delay

    # Save registry
    registry_df = pd.DataFrame(registry)
    registry_df.to_csv("corpus/document_registry.csv", index=False)
    
    # Save report
    report = {
        "timestamp": time.time(),
        "total_papers": len(df),
        "processed": len(registry),
        "pdf_downloaded": sum(1 for r in registry if r["pdf_downloaded"]),
        "tei_downloaded": sum(1 for r in registry if r["tei_downloaded"]),
        "failed": sum(1 for r in registry if not r["pdf_downloaded"] and not r["tei_downloaded"]),
        "total_cost_usd": total_cost
    }
    with open("corpus/download_logs/download_report.json", "w") as f:
        json.dump(report, f, indent=4)
        
    print(f"\nDownload complete. Registry saved to corpus/document_registry.csv")
    print(f"Total PDFs: {report['pdf_downloaded']}, Total TEI: {report['tei_downloaded']}")

if __name__ == "__main__":
    main()
