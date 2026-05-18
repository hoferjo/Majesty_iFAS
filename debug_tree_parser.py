#!/usr/bin/env python3
"""Debug tree parser"""
from pathlib import Path
import re

tree_file = Path("data/raw/drawings_tree/tree_Eigenprodukte_Jost_Artikel.txt")

print(f"Reading tree file: {tree_file}")
print(f"File size: {tree_file.stat().st_size} bytes")
print("=" * 60)

drawings = []
current_category = ""
current_subcategory = ""
hierarchy_levels = {}

with open(tree_file, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}\n")

# Show first 30 lines as hex to understand encoding
print("First 30 lines (raw):")
for i, line in enumerate(lines[:30]):
    line_stripped = line.rstrip('\n')
    # Show hex for first few chars to debug special chars
    hex_chars = " ".join(f"{ord(c):02x}" for c in line_stripped[:10])
    print(f"Line {i:3d}: {repr(line_stripped[:60])} | hex: {hex_chars}")

print("\n" + "=" * 60)
print("Checking for files with extensions:\n")

file_count = 0
for i, line in enumerate(lines):
    text = line.rstrip('\n')
    if not text.strip():
        continue
    
    stripped = text.lstrip()
    
    # Check if this is a folder (has +---)
    if "+---" in text:
        indent_level = len(text) - len(text.lstrip()) 
        folder_name = stripped.replace("+---", "").replace("───", "").strip()
        if folder_name and indent_level < 20:
            print(f"Folder (level {indent_level}): {folder_name}")
            if indent_level < 5:
                current_category = folder_name
                current_subcategory = ""
            elif indent_level < 10:
                current_subcategory = folder_name
    
    # Check for files (has extension)
    extensions = [".pdf", ".stp", ".x_t", ".dxf", ".xls", ".xlsx", ".doc", ".docx"]
    if any(ext in stripped for ext in extensions):
        file_count += 1
        file_ext = ""
        if "." in stripped:
            file_ext = stripped.split(".")[-1].lower()
        
        # Try to extract drawing number
        match = re.match(r"^([0-9\s]+[a-z]?)\s*(?:-\s*)?(.+?)(?:\.[a-zA-Z]+)?$", stripped)
        drawing_num = ""
        description = ""
        if match:
            drawing_num = match.group(1).strip()
            description = match.group(2).strip()
        
        print(f"File {file_count}: {stripped[:70]}")
        print(f"  Drawing: '{drawing_num}' | Desc: '{description}' | Ext: {file_ext}")
        print(f"  Category: {current_category} | Subcat: {current_subcategory}")

print(f"\nTotal files found: {file_count}")
