#!/usr/bin/env python3
"""Test folder filter functionality"""
from pathlib import Path
from etl.create import create_from_drawingtree

base = Path.cwd()
tree_file = base / "data" / "raw" / "drawings_tree" / "tree_Eigenprodukte_Jost_Artikel.txt"

# Test 1: No filter - all drawings
output1 = base / "data" / "processed" / "cache" / "created_articles" / "test_all.csv"
print("Test 1: All drawings")
create_from_drawingtree(tree_file, output1)
if output1.exists():
    with open(output1) as f:
        lines = f.readlines()
    print(f"  Total rows: {len(lines)} ({len(lines)-1} data rows)")

# Test 2: Filter by "Holzer"
output2 = base / "data" / "processed" / "cache" / "created_articles" / "test_holzer.csv"
print("\nTest 2: Filter by 'Holzer'")
create_from_drawingtree(tree_file, output2, folder_filter="Holzer")
if output2.exists():
    with open(output2) as f:
        lines = f.readlines()
    print(f"  Total rows: {len(lines)} ({len(lines)-1} data rows)")
    print("  First 3 data rows:")
    for line in lines[1:4]:
        parts = line.strip().split(',')
        if len(parts) > 5:
            print(f"    Drawing: {parts[0]}, Category: {parts[4]}")

# Test 3: Filter by "KIZO"
output3 = base / "data" / "processed" / "cache" / "created_articles" / "test_kizo.csv"
print("\nTest 3: Filter by 'KIZO'")
create_from_drawingtree(tree_file, output3, folder_filter="KIZO")
if output3.exists():
    with open(output3) as f:
        lines = f.readlines()
    print(f"  Total rows: {len(lines)} ({len(lines)-1} data rows)")

# Test 4: Filter by non-existent folder
output4 = base / "data" / "processed" / "cache" / "created_articles" / "test_nonexistent.csv"
print("\nTest 4: Filter by non-existent 'NonExistent'")
create_from_drawingtree(tree_file, output4, folder_filter="NonExistent")
if output4.exists():
    with open(output4) as f:
        lines = f.readlines()
    print(f"  Total rows: {len(lines)} ({len(lines)-1} data rows)")
else:
    print("  No file created (as expected)")

print("\n✓ All tests completed")
