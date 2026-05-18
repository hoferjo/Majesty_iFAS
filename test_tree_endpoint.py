#!/usr/bin/env python3
"""Quick test of create_from_drawingtree function"""
from pathlib import Path
from etl.create import create_from_drawingtree

base = Path.cwd()
tree_file = base / "data" / "raw" / "drawings_tree" / "tree_Eigenprodukte_Jost_Artikel.txt"
output_csv = base / "data" / "processed" / "cache" / "created_articles" / "article_list_from_tree.csv"

print(f"Tree file: {tree_file}")
print(f"Tree file exists: {tree_file.exists()}")
print(f"Output CSV: {output_csv}")

try:
    create_from_drawingtree(tree_file, output_csv)
    print("✓ Function executed successfully")
    if output_csv.exists():
        with open(output_csv) as f:
            lines = f.readlines()
        print(f"✓ Output file created with {len(lines)} lines ({len(lines)-1} data rows)")
        print(f"First 2 lines:")
        for line in lines[:2]:
            print(f"  {line.rstrip()}")
    else:
        print("✗ Output file not created")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
