import os
import json
import sys

def check_notebook_paths():
    notebook_dir = 'notebooks'
    if not os.path.isdir(notebook_dir):
        print(f"Directory {notebook_dir} not found.")
        sys.exit(1)

    prohibited_strings = [
        '"/content/drive/MyDrive/AIGC/Data"',
        "'/content/drive/MyDrive/AIGC/Data'",
        'Data_v2',
        'manifest_executable_100.csv',
        'day9-corpus-expansion-100'
    ]

    required_strings = [
        'Data_V2',
        'corpus/manifest.csv',
        'day9-datav2-pipeline-fix'
    ]

    failed = False

    for root, _, files in os.walk(notebook_dir):
        for file in files:
            if not file.endswith('.ipynb'):
                continue
            
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

                # Check prohibited
                for prohibited in prohibited_strings:
                    if prohibited in content:
                        print(f"[FAIL] {filepath} contains prohibited string: {prohibited}")
                        failed = True

                # Check required
                for req in required_strings:
                    if req not in content:
                        print(f"[FAIL] {filepath} is missing required string: {req}")
                        failed = True

    if failed:
        print("Notebook path validation FAILED.")
        sys.exit(1)
    else:
        print("Notebook path validation PASSED.")

if __name__ == "__main__":
    check_notebook_paths()
