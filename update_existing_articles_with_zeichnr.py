#!/usr/bin/env python3
"""
Script to update existing articles files with drawing numbers (Zeichnungsnummer) 
from the iFAS artikelstamm file (existing_iFAS_articlesProd.csv)
"""
import csv
from pathlib import Path

BASE_DIR = Path(__file__).parent

def update_existing_articles_from_ifas_source():
    """
    Read drawing numbers from existing_iFAS_articlesProd.csv and update 
    the existing articles files (existingArticlesPROD.csv, existingArticlesTEST.csv)
    with the zeichnr column.
    """
    
    # Source file with full iFAS data
    ifas_source = BASE_DIR / "data" / "processed" / "cache" / "existing" / "existing_iFAS_articlesProd.csv"
    
    # Target files to update
    existing_prod = BASE_DIR / "data" / "processed" / "cache" / "existing" / "existingArticlesPROD.csv"
    existing_test = BASE_DIR / "data" / "processed" / "cache" / "existing" / "existingArticlesTEST.csv"
    
    if not ifas_source.exists():
        print(f"Source file not found: {ifas_source}")
        return False
    
    # Read iFAS source to build artnr -> zeichnr mapping
    artnr_zeichnr_map = {}
    try:
        with open(ifas_source, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            if not reader.fieldnames:
                print("Source file has no header")
                return False
            
            # Find the column indices
            artnr_col = None
            zeichnr_col = None
            
            for i, fieldname in enumerate(reader.fieldnames or []):
                field_lower = str(fieldname or "").strip().lower()
                if "artikel" in field_lower and ("nr" in field_lower or "nummer" in field_lower):
                    artnr_col = fieldname
                elif "zeichnung" in field_lower and "nummer" in field_lower:
                    zeichnr_col = fieldname
            
            if not artnr_col:
                print(f"Could not find Artikelnummer column. Available columns: {reader.fieldnames}")
                return False
            
            print(f"Using columns: Artikelnummer={artnr_col}, Zeichnungsnummer={zeichnr_col}")
            
            for row in reader:
                artnr = str((row or {}).get(artnr_col, "") or "").strip()
                zeichnr = str((row or {}).get(zeichnr_col, "") or "").strip() if zeichnr_col else ""
                if artnr:
                    artnr_zeichnr_map[artnr] = zeichnr
        
        print(f"Read {len(artnr_zeichnr_map)} articles from source file")
    except Exception as e:
        print(f"Error reading source file: {e}")
        return False
    
    # Update existing articles files
    updated_files = []
    for target_file in [existing_prod, existing_test]:
        if not target_file.exists():
            print(f"Target file not found: {target_file}, skipping")
            continue
        
        try:
            # Read existing articles
            existing_artnrs = []
            existing_data = []
            with open(target_file, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f, delimiter=",")
                header = reader.fieldnames or []
                for row in reader:
                    artnr = str((row or {}).get("artnr", "") or "").strip()
                    if artnr:
                        existing_artnrs.append(artnr)
                        zeichnr = artnr_zeichnr_map.get(artnr, "")
                        existing_data.append((artnr, zeichnr))
            
            # Write updated file
            with open(target_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter=",")
                writer.writerow(["artnr", "zeichnr"])
                for artnr, zeichnr in existing_data:
                    writer.writerow([artnr, zeichnr])
            
            updated_count = len(existing_data)
            matched_count = sum(1 for _, zeichnr in existing_data if zeichnr)
            print(f"✓ Updated {target_file.name}: {updated_count} articles, {matched_count} with drawing numbers")
            updated_files.append(target_file.name)
        
        except Exception as e:
            print(f"Error updating {target_file}: {e}")
            continue
    
    if updated_files:
        print(f"\n✓ Successfully updated {len(updated_files)} file(s)")
        return True
    else:
        print("\n✗ No files were updated")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("Updating existing articles with drawing numbers from iFAS source")
    print("=" * 70)
    
    success = update_existing_articles_from_ifas_source()
    
    if success:
        print("\n" + "=" * 70)
        print("✓ Update completed successfully!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("✗ Update failed")
        print("=" * 70)
