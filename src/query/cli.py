import argparse
import sys
from .router import classify_question
from .operators import load_context, answer_single_doc, answer_aggregation, answer_contradiction, answer_temporal, answer_citation_graph, answer_multihop, answer_negation, answer_quantitative
from .answer_builder import build_final_answer

def configure_utf8_output():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

def main():
    parser = argparse.ArgumentParser(description="AIGC Research QA Engine")
    parser.add_argument("--data-dir", default="/content/drive/MyDrive/AIGC/Data", help="Path to Data directory")
    parser.add_argument("--question", required=True, help="Research question to ask")
    args = parser.parse_args()
    
    configure_utf8_output()
    
    # 1. Routing
    route = classify_question(args.question)
    
    # 2. Context Loading
    ctx = load_context(args.data_dir)
    
    # 3. Dispatch to Operator
    tier = route["tier"]
    ans_text, evidence, limitations = "Unsupported tier.", [], []
    
    if tier == "single_doc":
        ans_text, evidence, limitations = answer_single_doc(args.question, route, ctx)
    elif tier == "aggregation":
        ans_text, evidence, limitations = answer_aggregation(args.question, route, ctx)
    elif tier == "contradiction":
        ans_text, evidence, limitations = answer_contradiction(args.question, route, ctx)
    elif tier == "temporal":
        ans_text, evidence, limitations = answer_temporal(args.question, route, ctx)
    elif tier == "citation_graph":
        ans_text, evidence, limitations = answer_citation_graph(args.question, route, ctx)
    elif tier == "multihop":
        ans_text, evidence, limitations = answer_multihop(args.question, route, ctx)
    elif tier == "negation":
        ans_text, evidence, limitations = answer_negation(args.question, route, ctx)
    elif tier == "quantitative":
        ans_text, evidence, limitations = answer_quantitative(args.question, route, ctx)
    else:
        ans_text = "I'm sorry, I couldn't classify that question into one of my analytical tiers."
        limitations = ["Query routing returned 'unknown'."]
        
    # 4. Build and Print Answer
    final_output = build_final_answer(ans_text, evidence, limitations)
    
    print("-" * 40)
    print(f"QUESTION: {args.question}")
    print(f"TIER: {tier}")
    print("-" * 40)
    try:
        print(final_output)
    except UnicodeEncodeError:
        print(final_output.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))
    print("-" * 40)

if __name__ == "__main__":
    main()
