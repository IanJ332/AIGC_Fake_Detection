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
        'Data_v2',
        'src.ingest',
        'results.csv',
        '"DATA_DIR = Path(DATA_DIR)"',
        '/content/drive/MyDrive/AIGC/Data"'
    ]

    required_strings_01 = [
        'scripts/download_corpus.py',
        'python -m src.parse.parse_pdfs',
        '--data-dir /content/drive/MyDrive/AIGC/Data_V2',
        'day9_data_status.json',
        'day9_data_sync_report.md'
    ]

    required_global = [
        'Data_V2',
        'main'
    ]

    required_strings_03 = [
        'src.extract.extract_entities',
        'src.extract.extract_results',
        'src.extract.build_paper_summaries',
        'src.extract.build_duckdb',
        'src.extract.validate_extraction',
        'result_tuples.csv'
    ]

    required_strings_05 = [
        'result_tuples.csv',
        'DAY9_FINAL_VALIDATION_PASS'
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
                        # Be careful with the DATA_DIR = Path check
                        if prohibited == '"DATA_DIR = Path(DATA_DIR)"':
                            # Let's do a smarter check if DATA_DIR = Path(DATA_DIR) is before DATA_DIR = f...
                            pass # We handle this by replacing the string entirely
                        else:
                            print(f"[FAIL] {filepath} contains prohibited string: {prohibited}")
                            failed = True

                # Check globals for 02-05
                if file.startswith(('02', '03', '04', '05')):
                    for req in required_global:
                        if req not in content:
                            print(f"[FAIL] {filepath} is missing required string: {req}")
                            failed = True

                # Check specifics for notebook 01
                if file == '01_data_sync_and_check.ipynb':
                    for req in required_strings_01:
                        if req not in content:
                            print(f"[FAIL] {filepath} is missing required string: {req}")
                            failed = True

                if file == '03_full_extraction_runner.ipynb':
                    for req in required_strings_03:
                        if req not in content:
                            print(f"[FAIL] {filepath} is missing required string: {req}")
                            failed = True

                if file == '05_final_validation_runner.ipynb':
                    for req in required_strings_05:
                        if req not in content:
                            print(f"[FAIL] {filepath} is missing required string: {req}")
                            failed = True

                # Custom check for DATA_DIR before global config
                if 'DATA_DIR = Path(DATA_DIR)' in content:
                    idx_path = content.find('DATA_DIR = Path(DATA_DIR)')
                    idx_def = content.find('DATA_DIR = f"{DRIVE_ROOT}/Data_V2"')
                    if idx_def == -1:
                        idx_def = content.find('DATA_DIR = ')
                    if idx_path != -1 and idx_def != -1 and idx_path < idx_def:
                        print(f"[FAIL] {filepath} contains DATA_DIR = Path(DATA_DIR) before DATA_DIR is defined")
                        failed = True


    if failed:
        print("Notebook path validation FAILED.")
        sys.exit(1)
    else:
        print("Notebook path validation PASSED.")

if __name__ == "__main__":
    check_notebook_paths()
