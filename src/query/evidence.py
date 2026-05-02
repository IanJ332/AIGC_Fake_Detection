import json
from pathlib import Path

def format_evidence_anchor(anchor):
    return str(anchor) if anchor else "unknown"

def get_section_snippet(paper_id, data_dir, section_type=None, anchor=None, max_chars=500):
    data_dir = Path(data_dir)
    sections_path = data_dir / "sections" / "sections.jsonl"
    
    if not sections_path.exists():
        return f"Evidence snippet unavailable (missing {sections_path})"
    
    try:
        with open(sections_path, "r", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                if str(row["paper_id"]) != str(paper_id):
                    continue
                
                # If anchor is provided, match it
                if anchor and row.get("evidence_anchor") == anchor:
                    text = row.get("text", "")
                    return text[:max_chars].replace("\n", " ") + ("..." if len(text) > max_chars else "")
                
                # If section_type is provided, match it (handle list of types)
                if section_type:
                    stypes = [section_type] if isinstance(section_type, str) else section_type
                    if row.get("section_type") in stypes:
                        text = row.get("text", "")
                        return text[:max_chars].replace("\n", " ") + ("..." if len(text) > max_chars else "")
                
                # Fallback to any section if nothing specific matched and we are just looking for a paper snippet
                if not anchor and not section_type:
                    text = row.get("text", "")
                    return text[:max_chars].replace("\n", " ") + ("..." if len(text) > max_chars else "")
    except Exception as e:
        return f"Error retrieving snippet: {e}"
        
    return "No matching evidence snippet found in sections."

def collect_evidence(rows, data_dir, paper_meta=None, max_items=5):
    evidence = []
    seen = set()
    paper_meta = paper_meta or {}
    
    for row in rows:
        if len(evidence) >= max_items:
            break
            
        pid = str(row.get("paper_id"))
        anchor = row.get("evidence_anchor")
        section_type = row.get("section_type")
        key = (pid, anchor, section_type)
        
        if key in seen:
            continue
        seen.add(key)
        
        # Use provided snippet if available, else fetch it
        snippet = row.get("snippet") or get_section_snippet(pid, data_dir, section_type=section_type, anchor=anchor)
        
        meta = paper_meta.get(pid, {})
        title = row.get("paper_title") or meta.get("title") or "Unknown"
        year = row.get("year") or meta.get("year") or "Unknown"
        
        evidence.append({
            "paper_id": pid,
            "title": title,
            "year": year,
            "anchor": format_evidence_anchor(anchor) if anchor else (section_type or "paper_level"),
            "snippet": snippet
        })
        
    return evidence
