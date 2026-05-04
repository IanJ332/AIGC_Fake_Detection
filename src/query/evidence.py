import json
from pathlib import Path

def is_valid_value(v):
    if v is None:
        return False
    s = str(v).strip()
    return s != "" and s.lower() not in {"unknown", "nan", "none", "null"}

def format_evidence_anchor(anchor):
    return str(anchor) if anchor else "unknown"

def get_section_snippet(paper_id, data_dir, section_type=None, anchor=None, max_chars=500):
    data_dir = Path(data_dir)
    sections_path = data_dir / "sections" / "sections.jsonl"
    
    if not sections_path.exists():
        return f"Evidence snippet unavailable (missing {sections_path})"
    
    def try_find(stype=None, anc=None):
        try:
            with open(sections_path, "r", encoding="utf-8-sig") as f:
                for line in f:
                    if not line.strip(): continue
                    row = json.loads(line)
                    if str(row["paper_id"]) != str(paper_id):
                        continue
                    
                    # Match anchor if provided
                    if anc and row.get("evidence_anchor") == anc:
                        text = row.get("text", "")
                        return text[:max_chars].replace("\n", " ") + ("..." if len(text) > max_chars else "")
                    
                    # Match section_type if provided
                    if stype:
                        stypes = [stype] if isinstance(stype, str) else stype
                        if row.get("section_type") in stypes:
                            text = row.get("text", "")
                            return text[:max_chars].replace("\n", " ") + ("..." if len(text) > max_chars else "")
                    
                    # Fallback if no specific target
                    if not anc and not stype:
                        text = row.get("text", "")
                        return text[:max_chars].replace("\n", " ") + ("..." if len(text) > max_chars else "")
        except:
            pass
        return None

    snippet = try_find(section_type, anchor)
    
    # If specific match failed, try any section for this paper
    if snippet is None and (section_type or anchor):
        snippet = try_find()
        
    return snippet if snippet else "No matching evidence snippet found in sections."

def collect_evidence(rows, data_dir, paper_meta=None, max_items=5, query=None):
    from .retrieval import retrieve_sections
    
    evidence = []
    seen = set()
    paper_meta = paper_meta or {}
    
    # Standard exact-match evidence
    for row in rows:
        if len(evidence) >= max_items:
            break
            
        pid = str(row.get("paper_id"))
        
        # Handle DATA_BASIS pseudo-evidence
        if pid == "DATA_BASIS":
            evidence.append({
                "paper_id": "DATA_BASIS",
                "title": row.get("title") or row.get("paper_title") or "Unknown Source",
                "year": "N/A",
                "anchor": "csv_index",
                "snippet": row.get("snippet", "Statistical aggregation source.")
            })
            continue

        anchor = row.get("evidence_anchor")
        section_type = row.get("section_type")
        key = (pid, anchor, section_type)
        
        if key in seen:
            continue
        seen.add(key)
        
        # Fetch snippet
        snippet = get_section_snippet(pid, data_dir, section_type=section_type, anchor=anchor)
        
        meta = paper_meta.get(pid, {})
        row_title = row.get("paper_title") or row.get("title")
        row_year = row.get("year") or row.get("publish_year")

        title = row_title if is_valid_value(row_title) else meta.get("title")
        year = row_year if is_valid_value(row_year) else meta.get("year")

        title = title if is_valid_value(title) else "Unknown"
        year = year if is_valid_value(year) else "Unknown"
        
        evidence.append({
            "paper_id": pid,
            "title": title,
            "year": year,
            "anchor": format_evidence_anchor(anchor) if anchor else (section_type or "paper_level"),
            "snippet": snippet
        })
        
    # If still no evidence and query provided, try retrieval
    if not evidence and query:
        retrieved = retrieve_sections(query, data_dir, top_k=max_items)
        for r in retrieved:
            pid = r["paper_id"]
            meta = paper_meta.get(pid, {})
            evidence.append({
                "paper_id": pid,
                "title": meta.get("title", "Unknown"),
                "year": meta.get("year", "Unknown"),
                "anchor": f"retrieval:{r['section_type']}",
                "snippet": r["text"][:500].replace("\n", " ") + ("..." if len(r["text"]) > 500 else "")
            })
            
    return evidence
