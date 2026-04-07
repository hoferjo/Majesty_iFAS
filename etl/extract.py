from dbfread import DBF
import pandas as pd
from pathlib import Path

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