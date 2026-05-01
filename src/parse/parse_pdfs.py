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
    parser.add_argument("--registry", default="corpus/document_registry.csv", help="Path to document registry")
    args = parser.parse_args()

    if not os.path.exists(args.registry):
        print(f"Error: Registry {args.registry} not found.")
        return

    df = pd.read_csv(args.registry)
    parse_results = []
    
    os.makedirs("corpus/parsed", exist_ok=True)
    os.makedirs("corpus/parse_logs", exist_ok=True)
    
    pdf_rows = df[df["pdf_downloaded"] == True]
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
        
        if row.get("pdf_downloaded") == True:
            pdf_path = f"corpus/pdfs/{paper_id}.pdf"
            if os.path.exists(pdf_path):
                data, error = parse_pdf(pdf_path, paper_id, row)
                if data:
                    output_path = f"corpus/parsed/{paper_id}.json"
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
        else:
            parse_status["error"] = "No PDF available"
            
        parse_results.append(parse_status)

    # Save parse registry
    parse_df = pd.DataFrame(parse_results)
    parse_df.to_csv("corpus/parse_registry.csv", index=False)
    
    # Save report
    success_df = parse_df[parse_df["parse_success"] == True]
    report = {
        "timestamp": time.time(),
        "total_attempted": len(parse_results),
        "success_count": int(parse_df["parse_success"].sum()),
        "needs_ocr_count": int(parse_df["needs_ocr"].sum()),
        "avg_chars": float(success_df["total_chars"].mean()) if not success_df.empty else 0.0
    }
    with open("corpus/parse_logs/parse_report.json", "w") as f:
        json.dump(report, f, indent=4)
        
    print(f"Parsing complete. Successfully parsed {report['success_count']} PDFs.")
    print(f"Registry: corpus/parse_registry.csv")

if __name__ == "__main__":
    main()
