import pandas as pd
from pathlib import Path
import csv
def download_excel_file(url, save_path):
    try:
        df = pd.read_excel(url)
        df.to_csv(save_path, index=False, sep=';')
        print(f"File downloaded and saved to {save_path}")
    except Exception as e:
        print(f"Error downloading or saving the file: {e}")
