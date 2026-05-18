#!/usr/bin/env python3
"""
One-time script to add drawing numbers (Zeichnungsnummer) from
`data/raw/artikelstamm/artikelstamm_majesty_2026_03_30.csv` to the
existing articles files (existingArticlesPROD.csv, existingArticlesTEST.csv).

Behavior: For each artnr in the existing files, if the `zeichnr` is empty,
fill it from the majesty artikelstamm mapping. Do not overwrite non-empty zeichnr.
"""
import csv
from pathlib import Path

BASE_DIR = Path(__file__).parent
MAJESTY_PATH = BASE_DIR / "data" / "raw" / "artikelstamm" / "artikelstamm_majesty_2026_03_30.csv"
TARGETS = [
    BASE_DIR / "data" / "processed" / "cache" / "existing" / "existingArticlesPROD.csv",
    BASE_DIR / "data" / "processed" / "cache" / "existing" / "existingArticlesTEST.csv",
]


def load_majesty_map():
    if not MAJESTY_PATH.exists():
        print(f"Majesty source not found: {MAJESTY_PATH}")
        return {}
    mapping = {}
    with open(MAJESTY_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=';')
        # figure out artnr and zeichnr column names
        headers = [h or "" for h in (reader.fieldnames or [])]
        artkeys = [h for h in headers if "art" in h.lower() and ("nr" in h.lower() or "nummer" in h.lower())]
        zeichkeys = [h for h in headers if "zeich" in h.lower() or "zeichnung" in h.lower()]
        artcol = artkeys[0] if artkeys else headers[0] if headers else "artnr"
        zeichcol = zeichkeys[0] if zeichkeys else None
        for row in reader:
            artnr = str((row or {}).get(artcol, "") or "").strip()
            zeichnr = str((row or {}).get(zeichcol, "") or "").strip() if zeichcol else ""
            if artnr:
                mapping[artnr] = zeichnr
    print(f"Loaded {len(mapping)} artnr->zeichnr entries from majesty source")
    return mapping


def update_targets(mapping):
    for target in TARGETS:
        if not target.exists():
            print(f"Target not found, skipping: {target}")
            continue
        rows = []
        with open(target, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=',')
            headers = reader.fieldnames or ["artnr", "zeichnr"]
            for row in reader:
                artnr = str((row or {}).get("artnr", "") or "").strip()
                zeichnr = str((row or {}).get("zeichnr", "") or "").strip()
                if artnr:
                    if not zeichnr:
                        newz = mapping.get(artnr, "")
                        zeichnr = newz
                    rows.append((artnr, zeichnr))
        # write back
        with open(target, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerow(["artnr", "zeichnr"])
            for artnr, zeichnr in rows:
                writer.writerow([artnr, zeichnr])
        matched = sum(1 for _, z in rows if z)
        print(f"Updated {target.name}: {len(rows)} articles, {matched} with zeichnr")


if __name__ == "__main__":
    print("One-time: Adding zeichnr from artikelstamm_majesty to existing articles")
    mapping = load_majesty_map()
    if mapping:
        update_targets(mapping)
    else:
        print("No mapping available; nothing done.")
