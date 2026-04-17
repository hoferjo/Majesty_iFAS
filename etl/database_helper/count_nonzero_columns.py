import csv
from pathlib import Path
import sys

def count_nonzero_entries(csv_path):
    csv_path = Path(csv_path)
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="," if csv_path.suffix == ".csv" else ";")
        columns = reader.fieldnames
        counts = {col: 0 for col in columns}
        for row in reader:
            for col in columns:
                val = row.get(col, "")
                if val and str(val).strip() not in ("0", "0.0", ""):  # count as nonzero if not 0/0.0/empty
                    counts[col] += 1
    return counts

def main():
    if len(sys.argv) < 2:
        print("Usage: python count_nonzero_columns.py <csv_file>")
        sys.exit(1)
    csv_file = sys.argv[1]
    counts = count_nonzero_entries(csv_file)
    print(f"Non-zero entry counts for {csv_file}:")
    for col, count in counts.items():
        print(f"{col}: {count}")

if __name__ == "__main__":
    main()
