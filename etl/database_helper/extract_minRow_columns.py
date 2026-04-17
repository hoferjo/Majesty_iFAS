import yaml
from pathlib import Path

minimum_rows = 100
minimum_rows_in_columns = minimum_rows // 100

# Use the file with counts as input
input_path = Path("config/database_config/database_columns_with_counts.yaml")
if minimum_rows != minimum_rows_in_columns:
    output_path = Path(f"config/database_config/database_columns_min_{minimum_rows}.yaml")
else:
    output_path = Path(f"config/database_config/database_columns_file-min_{minimum_rows}_col-min_{minimum_rows_in_columns}.yaml")

def main():
    with open(input_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    result = {}
    for fname, entries in data.get("file_mappings", {}).items():
        columns = None
        rows = 0
        for entry in entries:
            if isinstance(entry, dict):
                if "columnheaders" in entry:
                    # Now columns is a list of dicts: [{col: count}, ...]
                    columns = entry["columnheaders"]
                if "rows" in entry:
                    rows = entry["rows"]
        if columns and rows and rows >= minimum_rows:
            # Only keep columns with count >= minimum_rows_in_columns
            filtered_columns = []
            for col in columns:
                if isinstance(col, dict):
                    for k, v in col.items():
                        if v >= minimum_rows_in_columns:
                            filtered_columns.append(k)
            if filtered_columns:
                result[fname] = filtered_columns

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(result, f, allow_unicode=True)

if __name__ == "__main__":
    main()
