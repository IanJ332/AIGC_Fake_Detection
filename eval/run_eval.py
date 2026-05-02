import json
import argparse
import subprocess
import pandas as pd
from pathlib import Path
from src.query.router import classify_question

def run_eval(data_dir, questions_path, output_dir=None):
    questions_path = Path(questions_path)
    data_dir = Path(data_dir)
    results_dir = Path(output_dir) if output_dir else Path("eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    outputs = []
    summary = {
        "total_questions": 0,
        "correct_tier_routing": 0,
        "unknown_tier_routing": 0,
        "operator_success": 0,
        "operator_failure": 0,
        "with_evidence": 0,
        "with_limitations": 0,
        "tier_counts": {}
    }
    
    print(f"Running evaluation on {questions_path}...")
    with open(questions_path, "r", encoding="utf-8") as f:
        for line in f:
            q_data = json.loads(line)
            question = q_data["question"]
            expected_tier = q_data["tier"]
            summary["total_questions"] += 1
            
            # 1. Routing check
            route = classify_question(question)
            actual_tier = route["tier"]
            is_tier_correct = (actual_tier == expected_tier)
            if is_tier_correct:
                summary["correct_tier_routing"] += 1
            if actual_tier == "unknown":
                summary["unknown_tier_routing"] += 1
                
            summary["tier_counts"][expected_tier] = summary["tier_counts"].get(expected_tier, 0) + 1
            
            # 2. Operator run (via CLI to simulate full path)
            try:
                cmd = [
                    "python", "-m", "src.query.cli",
                    "--data-dir", str(data_dir),
                    "--question", question
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    summary["operator_success"] += 1
                    output_text = result.stdout
                    # Improved evidence detection criteria
                    has_p_evidence = "Evidence:" in output_text and "- P" in output_text
                    has_data_basis = "Data Basis:" in output_text or any(csv in output_text for csv in ["entities.csv", "result_tuples.csv", "paper_entity_summary.csv", "paper_section_stats.csv", "extraction_registry.csv"])
                    has_graph_limit = "Citation data missing" in output_text
                    
                    has_evidence = has_p_evidence or has_data_basis or has_graph_limit
                    has_limitations = "Limitations:" in output_text and "- " in output_text
                    
                    if has_evidence: summary["with_evidence"] += 1
                    if has_limitations: summary["with_limitations"] += 1
                    
                    outputs.append({
                        "id": q_data["id"],
                        "question": question,
                        "expected_tier": expected_tier,
                        "actual_tier": actual_tier,
                        "routing_correct": is_tier_correct,
                        "status": "success",
                        "output_snippet": output_text[:500] + "..."
                    })
                else:
                    summary["operator_failure"] += 1
                    outputs.append({
                        "id": q_data["id"],
                        "status": "failure",
                        "error": result.stderr
                    })
                    
            except Exception as e:
                summary["operator_failure"] += 1
                outputs.append({
                    "id": q_data["id"],
                    "status": "error",
                    "error": str(e)
                })

    # Save detailed results
    out_path = results_dir / "day6_eval_outputs.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for o in outputs:
            f.write(json.dumps(o) + "\n")
            
    # Generate Summary Markdown
    summary_path = results_dir / "day6_eval_summary.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# Day 6 QA Engine Evaluation Summary\n\n")
        f.write(f"- **Total Questions**: {summary['total_questions']}\n")
        f.write(f"- **Tier Routing Accuracy**: {summary['correct_tier_routing']}/{summary['total_questions']} ({summary['correct_tier_routing']/summary['total_questions']*100:.1f}%)\n")
        f.write(f"- **Unknown Tier Count**: {summary['unknown_tier_routing']}\n")
        f.write(f"- **Operator Execution Success**: {summary['operator_success']}/{summary['total_questions']}\n")
        f.write(f"- **Answers with Evidence**: {summary['with_evidence']}\n")
        f.write(f"- **Answers with Limitations**: {summary['with_limitations']}\n\n")
        
        f.write("## Per-Tier Distribution\n")
        f.write("| Tier | Count |\n| :--- | :--- |\n")
        for t, c in summary["tier_counts"].items():
            f.write(f"| {t} | {c} |\n")
            
    print(f"Evaluation complete. Summary saved to {summary_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="/content/drive/MyDrive/AIGC/Data")
    parser.add_argument("--questions", default="eval/questions_40.jsonl")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    run_eval(args.data_dir, args.questions, args.output_dir)
