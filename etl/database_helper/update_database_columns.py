"""
Script to update database_columns.yaml with column headers and row counts for each CSV in data/raw/databases.
Run this script manually when you want to refresh the mapping.
"""
import os
import csv
import yaml
from pathlib import Path

CSV_DIR = Path('data/raw/databases')
YAML_PATH = Path('config/database_config/database_columns.yaml')

def get_csv_info(csv_path):
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader, [])
        row_count = sum(1 for _ in reader)
    return headers, row_count

def main():
    # Load existing YAML
    if YAML_PATH.exists():
        with open(YAML_PATH, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    if 'file_mappings' not in data:
        data['file_mappings'] = {}


    updated = False
    # Scan CSVs
    for csv_file in os.listdir(CSV_DIR):
        if not csv_file.lower().endswith('.csv'):
            continue
        csv_path = CSV_DIR / csv_file
        headers, row_count = get_csv_info(csv_path)
        existing = data['file_mappings'].get(csv_file, [{}, {}])
        existing_headers = existing[0].get('columnheaders', [])
        existing_rows = existing[1].get('rows', 0)
        if headers != existing_headers or row_count != existing_rows:
            data['file_mappings'][csv_file] = [
                {'columnheaders': headers},
                {'rows': row_count}
            ]
            updated = True

    if updated:
        with open(YAML_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        print(f"Updated {YAML_PATH} with column headers and row counts.")
    else:
        print(f"No changes detected. {YAML_PATH} is up to date.")

if __name__ == '__main__':
    main()
