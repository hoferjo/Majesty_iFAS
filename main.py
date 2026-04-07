from pathlib import Path
import yaml
from etl.transform import getEntryFromCSV
BASE_DIR = Path(__file__).parent


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
    


settings_path = BASE_DIR / "config" / "settings.yaml"
settings = load_yaml(settings_path)
if not settings:
    raise RuntimeError(f"Failed to load settings from {settings_path}. File is empty or invalid.")
try:
    raw_dir = settings["paths"]["raw_dir"]
    artikelstamm_file = settings["files"]["artikelstamm"]
except Exception as e:
    raise RuntimeError(f"Error reading keys from settings.yaml: {e}")
file_artikelstamm = BASE_DIR / raw_dir / "artikelstamm" / artikelstamm_file

#def main():
#    config_path = BASE_DIR / "config" / "mapping_kunden.yaml"
#    mapping = load_yaml(config_path)
#    for entry in mapping:
#        print(getEntryFromCSV(file_artikelstamm, "columnname", entry["artnr"]))

print("this is a test:\n input:          print(getEntryFromCSV(file_artikelstamm, 'artbez1', '60.06.0500'))\noutput:         ",getEntryFromCSV(file_artikelstamm, '60.06.0500', 'artbez1'))


