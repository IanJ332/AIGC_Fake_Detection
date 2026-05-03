"""
scripts/download_corpus.py
--------------------------
Download accessible PDFs from the corpus manifest into a local output directory.

Usage:
    python scripts/download_corpus.py --out-dir ./corpus/pdfs
    python scripts/download_corpus.py --manifest corpus/manifest_100.csv --out-dir ./corpus/pdfs --delay 1.5

Policy:
  - Respects HTTP 403/429 responses and logs them as inaccessible (does NOT retry aggressively).
  - Does NOT commit downloaded PDFs to Git.
  - Writes a download_report.json summarising success, failure, and skip counts.
"""

import argparse
import json
import time
from pathlib import Path

import pandas as pd
import requests


BLOCKED_DOMAINS = [
    "ieee.org", "acm.org", "springer.com", "sciencedirect.com",
    "wiley.com", "nature.com", "tandfonline.com", "dl.acm.org",
]

HEADERS = {
    "User-Agent": (
        "AIGC-Research-System/1.0 (academic corpus assembly; "
        "contact: research@example.com)"
    )
}


def is_likely_blocked(url: str) -> bool:
    """Heuristically detect known paywalled publishers before attempting download."""
    url_lower = url.lower()
    return any(domain in url_lower for domain in BLOCKED_DOMAINS)


def download_pdf(url: str, dest: Path, delay: float = 1.0) -> dict:
    """Attempt to download a PDF. Returns a status dict."""
    if dest.exists():
        return {"status": "skipped", "reason": "already_exists", "url": url}

    if is_likely_blocked(url):
        return {"status": "skipped", "reason": "likely_paywalled", "url": url}

    try:
        time.sleep(delay)
        resp = requests.get(url, headers=HEADERS, timeout=30, stream=True)

        if resp.status_code == 403:
            return {"status": "blocked", "reason": "http_403", "url": url}
        if resp.status_code == 429:
            return {"status": "blocked", "reason": "http_429_rate_limited", "url": url}
        if resp.status_code != 200:
            return {"status": "failed", "reason": f"http_{resp.status_code}", "url": url}

        content_type = resp.headers.get("Content-Type", "")
        if "pdf" not in content_type and "octet-stream" not in content_type:
            # Might be an HTML paywall page
            first_bytes = b""
            for chunk in resp.iter_content(512):
                first_bytes = chunk
                break
            if first_bytes[:4] != b"%PDF":
                return {"status": "blocked", "reason": "not_a_pdf_response", "url": url}

        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)

        size_kb = dest.stat().st_size / 1024
        if size_kb < 10:
            dest.unlink()
            return {"status": "failed", "reason": "file_too_small", "url": url}

        return {"status": "success", "size_kb": round(size_kb, 1), "url": url}

    except requests.Timeout:
        return {"status": "failed", "reason": "timeout", "url": url}
    except requests.RequestException as e:
        return {"status": "failed", "reason": str(e)[:120], "url": url}


def main():
    parser = argparse.ArgumentParser(description="Download accessible corpus PDFs.")
    parser.add_argument(
        "--manifest",
        default="corpus/manifest.csv",
        help="Path to manifest CSV (must have id/paper_id and pdf_url columns).",
    )
    parser.add_argument(
        "--out-dir",
        default="corpus/pdfs",
        help="Output directory for downloaded PDFs.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Seconds to wait between requests (be polite).",
    )
    parser.add_argument(
        "--report",
        default="corpus/download_report.json",
        help="Path to write the download report JSON.",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Root directory for Data_V2 structure. Overrides --out-dir and --report.",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        # Fallback to artifacts manifest
        manifest_path = Path("artifacts/manifests/manifest_100.csv")
    if not manifest_path.exists():
        print(f"[ERROR] Manifest not found at {args.manifest} or artifacts/manifests/manifest_100.csv")
        return

    if args.data_dir:
        data_dir = Path(args.data_dir)
        out_dir = data_dir / "pdfs"
        report_path = data_dir / "download_logs" / "download_report.json"
        report_csv_path = data_dir / "download_logs" / "download_report.csv"
        report_md_path = data_dir / "download_logs" / "download_report.md"
        registry_path = data_dir / "registry" / "document_registry.csv"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = Path(args.out_dir)
        report_path = Path(args.report)
        report_csv_path = report_path.with_suffix(".csv")
        report_md_path = report_path.with_suffix(".md")
        registry_path = Path("corpus/document_registry.csv")
        
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(manifest_path)

    # Synthesise paper_id if missing (handle 'id' column from manifest.csv)
    if "paper_id" not in df.columns and "id" in df.columns:
        df["paper_id"] = df["id"]
    elif "paper_id" not in df.columns:
        df["paper_id"] = [f"P{i+1:03d}" for i in range(len(df))]

    if "pdf_url" not in df.columns:
        print("[ERROR] Manifest has no 'pdf_url' column.")
        return

    results = []
    counts = {"success": 0, "skipped": 0, "blocked": 0, "failed": 0}
    registry_rows = []

    total = len(df)
    for i, row in df.iterrows():
        pid = str(row["paper_id"])
        url = str(row.get("pdf_url", "")).strip()
        dest = out_dir / f"{pid}.pdf"

        if not url or url in ("nan", "None", ""):
            result = {"paper_id": pid, "status": "skipped", "reason": "no_url", "url": ""}
        else:
            result = download_pdf(url, dest, delay=args.delay)
            result["paper_id"] = pid

        counts[result["status"]] = counts.get(result["status"], 0) + 1
        results.append(result)
        
        pdf_downloaded = result["status"] in ("success", "skipped") and result.get("reason") == "already_exists" or result["status"] == "success"
        if result["status"] == "skipped" and result.get("reason") != "already_exists":
            pdf_downloaded = False
            
        registry_rows.append({
            "paper_id": pid,
            "title": row.get("title", ""),
            "year": row.get("year", ""),
            "source_url": row.get("source_url", ""),
            "pdf_url": url,
            "pdf_downloaded": pdf_downloaded,
            "pdf_path": str(dest) if pdf_downloaded else "",
            "download_status": result["status"],
            "download_reason": result.get("reason", ""),
            "file_size_bytes": int(result.get("size_kb", 0) * 1024) if "size_kb" in result else 0
        })

        symbol = {"success": "✓", "skipped": "–", "blocked": "✗", "failed": "!"}.get(
            result["status"], "?"
        )
        print(f"[{i+1:3d}/{total}] {symbol} {pid}: {result['status']} — {result.get('reason', result.get('size_kb', ''))}")

    report = {
        "manifest": str(manifest_path),
        "out_dir": str(out_dir),
        "summary": counts,
        "results": results,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
        
    results_df = pd.DataFrame(results)
    results_df.to_csv(report_csv_path, index=False)
    
    with open(report_md_path, "w") as f:
        f.write("# Download Report\n\n")
        f.write(f"- Success: {counts.get('success', 0)}\n")
        f.write(f"- Skipped: {counts.get('skipped', 0)}\n")
        f.write(f"- Blocked: {counts.get('blocked', 0)}\n")
        f.write(f"- Failed: {counts.get('failed', 0)}\n")
        
    registry_df = pd.DataFrame(registry_rows)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_df.to_csv(registry_path, index=False)

    print(f"\n=== Download Report ===")
    print(f"  Success  : {counts.get('success', 0)}")
    print(f"  Skipped  : {counts.get('skipped', 0)} (already exists or paywalled)")
    print(f"  Blocked  : {counts.get('blocked', 0)} (HTTP 403/429 or non-PDF response)")
    print(f"  Failed   : {counts.get('failed', 0)}")
    print(f"\nReport written to: {report_path}")


if __name__ == "__main__":
    main()
