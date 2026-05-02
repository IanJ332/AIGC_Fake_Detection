def build_final_answer(ans_text, evidence, limitations):
    output = "Answer:\n"
    output += ans_text + "\n\n"
    
    if evidence:
        output += "Evidence:\n"
        for ev in evidence:
            if ev["paper_id"] == "DATA_BASIS":
                output += f"- Data Basis: {ev['title']}\n"
                output += f"  Anchor: {ev['anchor']}\n"
                output += f"  Snippet: {ev['snippet']}\n"
                continue
            
            output += f"- {ev['paper_id']} ({ev['title']}, {ev['year']})\n"
            output += f"  Anchor: {ev['anchor']}\n"
            output += f"  Snippet: {ev['snippet']}\n"
        output += "\n"
    else:
        output += "Evidence:\n- No specific evidence snippets retrieved for this query.\n\n"
        
    if limitations:
        output += "Limitations:\n"
        for lim in limitations:
            output += f"- {lim}\n"
    else:
        output += "Limitations:\n- Answer derived from current extracted deterministic indices."
        
    return output
