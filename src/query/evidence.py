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
                if row["paper_id"] != paper_id:
                    continue
                
                # If anchor is provided, match it
                if anchor and row.get("evidence_anchor") == anchor:
                    text = row.get("text", "")
                    return text[:max_chars].replace("\n", " ") + ("..." if len(text) > max_chars else "")
                
                # If section_type is provided, match it
                if section_type and row.get("section_type") == section_type:
                    text = row.get("text", "")
                    return text[:max_chars].replace("\n", " ") + ("..." if len(text) > max_chars else "")
                
                # Fallback to any section if nothing specific matched
                if not anchor and not section_type:
                    text = row.get("text", "")
                    return text[:max_chars].replace("\n", " ") + ("..." if len(text) > max_chars else "")
    except Exception as e:
        return f"Error retrieving snippet: {e}"
        
    return "No matching evidence snippet found in sections."

def collect_evidence(rows, data_dir, max_items=5):
    evidence = []
    seen = set()
    
    for row in rows:
        if len(evidence) >= max_items:
            break
            
        pid = row.get("paper_id")
        anchor = row.get("evidence_anchor")
        key = (pid, anchor)
        
        if key in seen:
            continue
        seen.add(key)
        
        snippet = get_section_snippet(pid, data_dir, anchor=anchor)
        
        evidence.append({
            "paper_id": pid,
            "title": row.get("paper_title", "Unknown"),
            "year": row.get("year", "Unknown"),
            "anchor": format_evidence_anchor(anchor),
            "snippet": snippet
        })
        
    return evidence
