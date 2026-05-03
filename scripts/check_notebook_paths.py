import os
import sys

def check_notebook_paths():
    notebook_dir = 'notebooks'
    if not os.path.isdir(notebook_dir):
        print(f"Directory {notebook_dir} not found.")
        sys.exit(1)

    prohibited_strings = [
        'DATA_PATH',
        'RESET_DATA',
        'MIN_PDF_REQUIRED_FOR_PARSE',
        'STOP_AFTER_PDF_COUNT',
        'src.acquire.validate_documents',
        'src.acquire.download_documents',
        'corpus/document_registry.csv',
        '--registry corpus/document_registry.csv',
        '--parsed-dir corpus/parsed',
        'manifest_executable_100.csv',
        'day9-corpus-expansion-100',
        'Data_v2'
    ]

    required_strings_01 = [
        'scripts/download_corpus.py',
        'python -m src.parse.parse_pdfs',
        '--data-dir /content/drive/MyDrive/AIGC/Data_V2',
        'day9_data_status.json',
        'day9_data_sync_report.md'
    ]

    failed = False

    for root, _, files in os.walk(notebook_dir):
        for file in files:
            if not file.endswith('.ipynb'):
                continue
            
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

                # Check prohibited everywhere
                for prohibited in prohibited_strings:
                    if prohibited in content:
                        print(f"[FAIL] {filepath} contains prohibited string: {prohibited}")
                        failed = True
                        
                # Check specifics for notebook 01
                if file == '01_data_sync_and_check.ipynb':
                    for req in required_strings_01:
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
