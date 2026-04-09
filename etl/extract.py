import os
import csv
import yaml
from dbfread import DBF
from pathlib import Path
import pandas as pd 

def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
    

BASE_DIR = Path(__file__).parent.parent
settings_path = BASE_DIR / "config" / "settings.yaml"
settings = load_yaml(settings_path)
if not settings:
    raise RuntimeError(f"Failed to load settings from {settings_path}. File is empty or invalid.")
try:
    raw_dir = settings["paths"]["raw_dir"]
    artikelstamm_file = settings["files"]["artikelstamm"]
except Exception as e:
    raise RuntimeError(f"Error reading keys from settings.yaml: {e}")
dbf_path = BASE_DIR / settings["paths"]["dbf_dir"]


def auto_update_dbf_csv(dbf_dir=dbf_path, out_dir="data/raw/databases", force=False):
    """
    For each .dbf in dbf_dir, update the corresponding .csv in out_dir if the dbf is newer or csv does not exist.
    """
    dbf_dir = Path(dbf_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dbf_files = list(dbf_dir.glob("*.dbf"))
    updated = []
    for dbf_path in dbf_files:
        out_csv = out_dir / (dbf_path.stem + ".csv")
        dbf_mtime = dbf_path.stat().st_mtime
        csv_mtime = out_csv.stat().st_mtime if out_csv.exists() else 0
        if force or not out_csv.exists() or dbf_mtime > csv_mtime:
            print(f"Updating {out_csv} from {dbf_path}")
            encodings = ["utf-8", "latin-1", "cp850", "cp437"]
            for enc in encodings:
                try:
                    table = DBF(dbf_path, encoding=enc, load=True)
                    fieldnames = list(table.field_names)
                    with open(out_csv, "w", encoding="utf-8", newline="") as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                        writer.writeheader()
                        for i, record in enumerate(table):
                            writer.writerow(dict(record))
                    updated.append(str(out_csv))
                    break
                except Exception as e:
                    last_error = e
            else:
                # Try with errors ignored
                try:
                    table = DBF(dbf_path, encoding="latin-1", ignore_errors=True, load=True)
                    fieldnames = list(table.field_names)
                    with open(out_csv, "w", encoding="utf-8", newline="") as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                        writer.writeheader()
                        for i, record in enumerate(table):
                            writer.writerow(dict(record))
                    updated.append(str(out_csv))
                except Exception as e:
                    print(f"Error reading {dbf_path}: {e}")
    return updated

def extract_dbf_headers_and_rows(db_path, extract_dir=None, rows=5, out_dir="data/raw/databases"):
    """
    Extracts the header and first N rows of every DBF file in the given folder.
    Writes each result to a CSV with the same name in data/raw/databases.
    """
    dbf_dir = Path(db_path) if extract_dir is None else Path(extract_dir)
    os.makedirs(out_dir, exist_ok=True)

    dbf_files = list(dbf_dir.glob("*.dbf"))
    for dbf_path in dbf_files:
        out_csv = os.path.join(out_dir, dbf_path.stem + ".csv")
        print(f"Extracting {dbf_path} to {out_csv}")
        encodings = ["utf-8", "latin-1", "cp850", "cp437"]
        for enc in encodings:
            try:
                table = DBF(dbf_path, encoding=enc, load=True)
                fieldnames = list(table.field_names)
                with open(out_csv, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    for i, record in enumerate(table):
                        if i >= rows:
                            break
                        writer.writerow(dict(record))
                break
            except Exception as e:
                last_error = e
        else:
            # Try with errors ignored
            try:
                table = DBF(dbf_path, encoding="latin-1", ignore_errors=True, load=True)
                fieldnames = list(table.field_names)
                with open(out_csv, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    for i, record in enumerate(table):
                        if i >= rows:
                            break
                        writer.writerow(dict(record))
            except Exception as e:
                print(f"Error reading {dbf_path}: {e}")


def extract_dbf_to_csv(dbf_path: Path, csv_path: Path, encoding_dbf = 'latin-1', encoding_csv = 'utf-8'):
    # Read the DBF file
    table = DBF(dbf_path, encoding_dbf)  # Adjust encoding if needed
    df = pd.DataFrame(iter(table))
    
    # Save to CSV
    df.to_csv(csv_path, index=False, encoding=encoding_csv)
    print(f"Extracted {dbf_path} to {csv_path}")

def extract_all_dbf_files(raw_data_dir, extracted_data_dir):
    raw_data_path = Path(raw_data_dir)
    extracted_data_path = Path(extracted_data_dir)
    extracted_data_path.mkdir(parents=True, exist_ok=True)

    for dbf_file in raw_data_path.glob("*.dbf"):
        csv_file = extracted_data_path / (dbf_file.stem + ".csv")
        extract_dbf_to_csv(dbf_file, csv_file)