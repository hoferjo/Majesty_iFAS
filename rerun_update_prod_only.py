#!/usr/bin/env python3
"""
One-off: Update only existingArticlesPROD.csv from
data/processed/cache/existing/existing_iFAS_articlesProd.csv (zeichnr)
"""
import csv
from pathlib import Path

BASE = Path(__file__).parent
SRC = BASE / "data" / "processed" / "cache" / "existing" / "existing_iFAS_articlesProd.csv"
TARGET = BASE / "data" / "processed" / "cache" / "existing" / "existingArticlesPROD.csv"

if not SRC.exists():
    print(f"Source not found: {SRC}")
    raise SystemExit(1)
if not TARGET.exists():
    print(f"Target not found: {TARGET}")
    raise SystemExit(1)

# Build mapping from SRC (semicolon-delimited)
mapping = {}
with open(SRC, "r", encoding="utf-8-sig", newline="") as f:
    r = csv.DictReader(f, delimiter=';')
    headers = r.fieldnames or []
    artcol = None
    zeichcol = None
    for h in headers:
        lh = (h or "").lower()
        if ("art" in lh) and ("nr" in lh or "nummer" in lh):
            artcol = h
        if "zeich" in lh or "zeichnung" in lh:
            zeichcol = h
    if not artcol:
        artcol = headers[0] if headers else "artnr"
    for row in r:
        art = str((row or {}).get(artcol, "") or "").strip()
        z = str((row or {}).get(zeichcol, "") or "").strip() if zeichcol else ""
        if art:
            mapping[art] = z
print(f"Loaded {len(mapping)} entries from source")

# Read target and update empty zeichnr only
rows = []
with open(TARGET, "r", encoding="utf-8-sig", newline="") as f:
    r = csv.DictReader(f, delimiter=',')
    for row in r:
        art = str((row or {}).get('artnr', '') or '').strip()
        z = str((row or {}).get('zeichnr', '') or '').strip()
        if art:
            if not z:
                z = mapping.get(art, '')
            rows.append((art, z))

# Write back
with open(TARGET, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter=',')
    w.writerow(["artnr", "zeichnr"])
    for art, z in rows:
        w.writerow([art, z])

matched = sum(1 for _, z in rows if z)
print(f"Updated {TARGET.name}: {len(rows)} articles, {matched} with zeichnr")
