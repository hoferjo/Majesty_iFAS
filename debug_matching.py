#!/usr/bin/env python3
"""Debug script to trace matching logic for articles."""

from etl.transform import (
    _get_article_description_parts,
    _match_parameter_values,
    _flatten_din_normteile,
    _load_yaml_cached,
    _normalize_rule_text,
)
from pathlib import Path

artnr = '10.10.0092'
parts, blob, normalized_blob = _get_article_description_parts(artnr)

print("=== ARTICLE PARTS ===")
print(f"Parts: {parts}")
print(f"Blob: {blob}")
print(f"Normalized Blob: {normalized_blob}")
print()

# Load and flatten DIN entries
din_normteile_path = Path('config/templates/DIN-Normteile.yaml')
din_normteile = _load_yaml_cached(din_normteile_path)
din_entries = _flatten_din_normteile(din_normteile)

# Find the Sechskantschraube entry
sechskant_entry = None
for entry in din_entries:
    if 'sechskant' in _normalize_rule_text(entry.get('display_name', '')).lower():
        sechskant_entry = entry
        print(f"Found entry: {entry['display_name']}")
        print(f"DIN numbers: {entry.get('din_numbers')}")
        print(f"Parameter options keys: {list(entry.get('parameter_options', {}).keys())}")
        print(f"Material options: {entry.get('parameter_options', {}).get('Material', [])}")
        print()
        break

# Test parameter matching
if sechskant_entry:
    param_matches = _match_parameter_values(normalized_blob, sechskant_entry.get('parameter_options', {}))
    print("=== PARAMETER MATCHES ===")
    for key, val in param_matches.items():
        print(f"{key}: {val}")
    print()
    
    # Now check each Material option manually
    print("=== MATERIAL OPTION MATCHING ===")
    material_options = sechskant_entry.get('parameter_options', {}).get('Material', [])
    for option in material_options[:8]:
        normalized = _normalize_rule_text(option)
        in_blob = normalized in normalized_blob
        print(f"{option:30} -> {normalized:20} -> in_blob: {in_blob}")
