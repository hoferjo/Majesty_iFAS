import yaml
from pathlib import Path
import csv

def count_nonzero_entries(csv_path, delimiter=None):
    with open(csv_path, encoding="utf-8-sig") as f:
        # Try to auto-detect delimiter if not provided
        if delimiter is None:
            sample = f.read(2048)
            f.seek(0)
            delimiter = ',' if sample.count(',') > sample.count(';') else ';'
        reader = csv.DictReader(f, delimiter=delimiter)
        columns = reader.fieldnames
        counts = {col: 0 for col in columns}
        for row in reader:
            for col in columns:
                val = row.get(col, "")
                if val and str(val).strip() not in ("0", "0.0", ""):
                    counts[col] += 1
    return counts

def main():
    yaml_path = Path("config/database_config/database_columns.yaml")
    data_dir = Path("data/raw/databases")
    with open(yaml_path, encoding="utf-8") as f:
        db_yaml = yaml.safe_load(f)
    for fname, entries in db_yaml.get("file_mappings", {}).items():
        csv_file = data_dir / fname
        if not csv_file.exists():
            continue
        # Find the columnheaders entry
        for entry in entries:
            if isinstance(entry, dict) and "columnheaders" in entry:
                counts = count_nonzero_entries(csv_file)
                # Replace list of columns with dict of column:count
                entry["columnheaders"] = [
                    {col: counts.get(col, 0)} for col in entry["columnheaders"]
                ]
    # Write back to a new file to preserve the original
    out_path = yaml_path.parent / "database_columns_with_counts.yaml"
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(db_yaml, f, allow_unicode=True)
    print(f"Wrote column counts to {out_path}")

if __name__ == "__main__":
    main()
