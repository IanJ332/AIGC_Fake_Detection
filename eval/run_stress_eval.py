import json
import argparse
import subprocess
import os
from pathlib import Path

def run_stress_eval(data_dir, questions_path, output_dir=None):
    questions_path = Path(questions_path)
    data_dir = Path(data_dir)
    results_dir = Path(output_dir) if output_dir else Path("eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    outputs = []
    summary = {
        "total_questions": 0,
        "success": 0,
        "failure": 0,
        "insufficient_data_handled": 0
    }
    
    print(f"Running STRESS evaluation on {questions_path}...")
    with open(questions_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            q_data = json.loads(line)
            question = q_data["question"]
            summary["total_questions"] += 1
            
            try:
                cmd = [
                    "python", "-m", "src.query.cli",
                    "--data-dir", str(data_dir),
                    "--question", question
                ]
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONUTF8"] = "1"
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=60,
                    env=env,
                    encoding="utf-8",
                    errors="replace"
                )
                
                output_text = result.stdout
                is_success = (result.returncode == 0)
                
                # Check for "defensible limitation"
                is_limitation = "Insufficient" in output_text or "No internal citation path" in output_text or "No parameter count claims" in output_text
                
                if is_success:
                    summary["success"] += 1
                    if is_limitation:
                        summary["insufficient_data_handled"] += 1
                else:
                    summary["failure"] += 1
                
                outputs.append({
                    "id": q_data["id"],
                    "question": question,
                    "status": "success" if is_success else "failure",
                    "is_limitation": is_limitation,
                    "output": output_text
                })
                
            except Exception as e:
                summary["failure"] += 1
                outputs.append({
                    "id": q_data["id"],
                    "question": question,
                    "status": "error",
                    "error": str(e)
                })

    # Save outputs
    out_path = results_dir / "pdf_prompt_stress_outputs.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for o in outputs:
            f.write(json.dumps(o) + "\n")
            
    # Generate Summary
    summary_path = results_dir / "pdf_prompt_stress_summary.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# PDF Prompt Stress Evaluation Summary\n\n")
        f.write(f"- **Total Questions**: {summary['total_questions']}\n")
        f.write(f"- **Successful Execution**: {summary['success']}/{summary['total_questions']}\n")
        f.write(f"- **Defensible Limitations Reported**: {summary['insufficient_data_handled']}\n\n")
        
        f.write("## Question Breakdown\n")
        f.write("| ID | Question | Status | Type |\n| :--- | :--- | :--- | :--- |\n")
        for o in outputs:
            q_type = "Limitation" if o.get("is_limitation") else "Computed"
            f.write(f"| {o['id']} | {o['question']} | {o['status']} | {q_type} |\n")
            
    print(f"Stress evaluation complete. Summary: {summary_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--questions", default="eval/pdf_prompt_stress_questions.jsonl")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    run_stress_eval(args.data_dir, args.questions, args.output_dir)
