import json
import os

def write_jsonl(data, filepath):
    """Writes a list of dictionaries to a JSONL file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        for entry in data:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def read_jsonl(filepath):
    """Reads a JSONL file and returns a list of dictionaries."""
    if not os.path.exists(filepath):
        return []
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data
