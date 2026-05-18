import csv
from pathlib import Path

# Use absolute path with CORRECT filename
base = Path(__file__).parent
existing_path = base / 'data' / 'processed' / 'cache' / 'existing' / 'existingArticlesPROD.csv'

print(f"Looking for: {existing_path}")
print(f"Exists: {existing_path.exists()}")

existing_zeich = set()
if existing_path.exists():
    print(f"Reading from {existing_path}")
    with open(existing_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=',')
        count = 0
        for r in reader:
            count += 1
            zn = (r.get('zeichnr') or '').strip()
            artnr = (r.get('artnr') or '').strip()
            if zn and '025 08' in zn:
                print(f'Found at row {count}: artnr={artnr}, zeichnr={repr(zn)}')
            if zn:
                existing_zeich.add(zn)
        print(f'Processed {count} rows')
else:
    print(f"File not found at {existing_path}")

print(f'\nTotal zeichnr loaded: {len(existing_zeich)}')
print(f'"025 08 01" in set: {"025 08 01" in existing_zeich}')
print(f'"025 08 05" in set: {"025 08 05" in existing_zeich}')

# Show first 10 non-empty zeichnr to debug
zlist = sorted([z for z in existing_zeich if z])[:10]
print(f'\nFirst 10 zeichnr: {zlist}')
