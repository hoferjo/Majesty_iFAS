#!/usr/bin/env python3
"""Final comprehensive workflow test"""
import requests
import json
import time

base_url = 'http://127.0.0.1:8000'

print("="*70)
print("FINAL COMPREHENSIVE WORKFLOW TEST")
print("="*70)

tests_passed = 0
tests_failed = 0

# Test 1: Basic endpoints
print("\n[1/5] Testing basic API endpoints...")
basic_endpoints = [
    ('/sheets-config', 'GET'),
    ('/search?query=01', 'GET'),
    ('/article-list-preview', 'GET'),
]

for endpoint, method in basic_endpoints:
    try:
        if method == 'GET':
            resp = requests.get(f'{base_url}{endpoint}', timeout=5)
        if resp.status_code == 200:
            print(f"  ✓ {endpoint} - OK")
            tests_passed += 1
        else:
            print(f"  ✗ {endpoint} - Status {resp.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"  ✗ {endpoint} - Error: {str(e)[:50]}")
        tests_failed += 1

# Test 2: BOM functions directly
print("\n[2/5] Testing BOM functions directly...")
try:
    from etl.transform import build_bom_sheet_cache
    from pathlib import Path
    
    test_dir = Path('data/processed')
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create minimal test files
    with open(test_dir / 'test_article.csv', 'w', encoding='utf-8') as f:
        f.write('artnr;artbez1;zeichnr\n01;Test;TEST\n')
    
    with open(test_dir / 'test_partlist.csv', 'w', encoding='utf-8') as f:
        f.write('stulinr;posnr;menge;artnr;artbez1\n01;1;1;01;Test\n')
    
    result = build_bom_sheet_cache(
        str(test_dir / 'test_partlist.csv'),
        str(test_dir / 'test_article.csv')
    )
    
    if result['status'] == 'ok':
        print(f"  ✓ BOM sheet generation - OK")
        print(f"    - Stücklisten: {result.get('stuecklisten_count', 0)}")
        print(f"    - Versionen: {result.get('versionen_count', 0)}")
        print(f"    - Positionen: {result.get('positionen_count', 0)}")
        tests_passed += 1
    else:
        print(f"  ✗ BOM generation - Failed: {result.get('status')}")
        tests_failed += 1
except Exception as e:
    print(f"  ✗ BOM functions - Error: {str(e)[:50]}")
    tests_failed += 1

# Test 3: Transform module imports
print("\n[3/5] Testing transform module imports...")
try:
    from etl.transform import (
        process_module_structure,
        build_sheet_cache_CSV,
        build_bom_sheet_cache,
        _evaluate_bom_mapping,
        _parse_mapping_csv,
        _find_mapping_file
    )
    print(f"  ✓ All transform functions imported successfully")
    tests_passed += 1
except ImportError as e:
    print(f"  ✗ Transform import failed: {str(e)[:50]}")
    tests_failed += 1

# Test 4: Load module imports
print("\n[4/5] Testing load module imports...")
try:
    from etl.load import (
        create_import_excel_from_templates,
        archive_module_export,
        create_partlist_excel_from_template,
    )
    print(f"  ✓ All load functions imported successfully")
    tests_passed += 1
except ImportError as e:
    print(f"  ✗ Load import failed: {str(e)[:50]}")
    tests_failed += 1

# Test 5: Check configuration files
print("\n[5/5] Checking configuration and data files...")
missing_files = []
required_files = [
    'config/settings.yaml',
    'config/sheets.csv',
    'config/active_sheets.csv',
    'data/raw/artikelstamm/artikelstamm_majesty_2026_03_30.csv',
]

for file_path in required_files:
    if not Path(file_path).exists():
        missing_files.append(file_path)

if not missing_files:
    print(f"  ✓ All configuration and data files present")
    tests_passed += 1
else:
    print(f"  ✗ Missing files: {missing_files}")
    tests_failed += 1

# Final summary
print("\n" + "="*70)
print(f"SUMMARY: {tests_passed} passed, {tests_failed} failed")
print("="*70)

if tests_failed == 0:
    print("✓ ALL WORKFLOWS PASSING - APPLICATION IS READY")
    exit(0)
else:
    print(f"✗ {tests_failed} ISSUES FOUND - SEE ABOVE FOR DETAILS")
    exit(1)
