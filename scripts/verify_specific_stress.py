import json
import sys
from pathlib import Path

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

p = Path("eval/results/pdf_prompt_stress_outputs.jsonl")
rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
for r in rows:
    if r.get("id") in ["STRESS_002", "STRESS_003"]:
        print(f"\n=== {r.get('id')} ===")
        print("tier:", r.get("tier") or r.get("expected_tier"))
        print("status:", r.get("status"))
        print("question:", r.get("question"))
        out = r.get("system_output") or r.get("output") or r.get("answer") or ""
        print(out)
