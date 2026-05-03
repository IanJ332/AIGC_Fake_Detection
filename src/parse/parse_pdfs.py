import argparse
import pandas as pd
import os
import json
import fitz # PyMuPDF
import time

def parse_pdf(pdf_path, paper_id, metadata):
    try:
        doc = fitz.open(pdf_path)
        pages_data = []
        total_chars = 0
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            blocks = page.get_text("blocks", sort=True)
            
            page_blocks = []
            for b in blocks:
                # b = (x0, y0, x1, y1, "text", block_no, block_type)
                # block_type 0 = text, 1 = image
                block_text = b[4].strip()
                if block_text:
                    page_blocks.append({
                        "block_id": b[5],
                        "bbox": [round(c, 2) for c in b[:4]],
                        "text": block_text,
                        "char_count": len(block_text)
                    })
            
            pages_data.append({
                "page_num": page_num + 1,
                "text": text,
                "blocks": page_blocks
            })
            total_chars += len(text)
            
        result = {
            "paper_id": paper_id,
            "title": str(metadata.get("title", "Unknown")),
            "year": metadata.get("year"),
            "doi": metadata.get("doi"),
            "source_url": metadata.get("source_url"),
            "pdf_path": pdf_path,
            "page_count": len(doc),
            "total_chars": total_chars,
            "pages": pages_data
        }
        return result, None
    except Exception as e:
        return None, str(e)

def main():
    parser = argparse.ArgumentParser(description="Parse PDFs into JSON.")
    parser.add_argument("--registry", default=None, help="Path to document registry")
    parser.add_argument("--data-dir", default=None, help="Base data directory")
    args = parser.parse_args()

    data_dir = args.data_dir if args.data_dir else "corpus"
    registry_path = args.registry if args.registry else f"{data_dir}/registry/document_registry.csv"
    # Fallback to older path structure if not found in registry folder
    if not os.path.exists(registry_path) and not args.registry:
        if os.path.exists(f"{data_dir}/document_registry.csv"):
            registry_path = f"{data_dir}/document_registry.csv"

    if not os.path.exists(registry_path):
        print(f"Error: Registry {registry_path} not found.")
        return

    df = pd.read_csv(registry_path)
    parse_results = []
    
    parsed_out = f"{data_dir}/parsed"
    logs_out = f"{data_dir}/parse_logs"
    os.makedirs(parsed_out, exist_ok=True)
    os.makedirs(logs_out, exist_ok=True)
    
    pdf_rows = df[df["pdf_downloaded"] == True] if "pdf_downloaded" in df.columns else df
    # Some registries may not have pdf_downloaded column directly, but rather just pdfs in the folder

    print(f"Parsing {len(pdf_rows)} PDFs...")
    
    for idx, row in df.iterrows():
        paper_id = row["paper_id"]
        
        parse_status = {
            "paper_id": paper_id,
            "parse_success": False,
            "needs_ocr": False,
            "total_chars": 0,
            "page_count": 0,
            "error": None
        }
        
        # Check if PDF exists instead of relying entirely on pdf_downloaded column (which may be missing)
        pdf_path = f"{data_dir}/pdfs/{paper_id}.pdf"
        
        if os.path.exists(pdf_path):
            data, error = parse_pdf(pdf_path, paper_id, row)
            if data:
                output_path = f"{parsed_out}/{paper_id}.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    
                parse_status["parse_success"] = True
                parse_status["total_chars"] = data["total_chars"]
                parse_status["page_count"] = data["page_count"]
                if data["total_chars"] < 500:
                    parse_status["needs_ocr"] = True
            else:
                parse_status["error"] = error
        else:
            parse_status["error"] = "File missing despite registry status"
            parse_status["error"] = "No PDF available"
            
        parse_results.append(parse_status)

    # Save parse registry
    parse_df = pd.DataFrame(parse_results)
    parse_reg_path = f"{data_dir}/registry/parse_registry.csv"
    os.makedirs(os.path.dirname(parse_reg_path), exist_ok=True)
    parse_df.to_csv(parse_reg_path, index=False)
    
    # Save report
    success_df = parse_df[parse_df["parse_success"] == True]
    report = {
        "timestamp": time.time(),
        "total_attempted": len(parse_results),
        "success_count": int(parse_df["parse_success"].sum()),
        "needs_ocr_count": int(parse_df["needs_ocr"].sum()),
        "avg_chars": float(success_df["total_chars"].mean()) if not success_df.empty else 0.0
    }
    with open(f"{logs_out}/parse_report.json", "w") as f:
        json.dump(report, f, indent=4)
        
    print(f"Parsing complete. Successfully parsed {report['success_count']} PDFs.")
    print(f"Registry: {parse_reg_path}")

if __name__ == "__main__":
    main()
