#!/usr/bin/env python3
"""Test complex workflows like generate module, BOM sheet generation, etc."""
import requests
import json
from pathlib import Path

base_url = 'http://127.0.0.1:8000'

def test_generate_module_workflow():
    """Test the complete generate module workflow"""
    print("\n" + "="*60)
    print("TEST: Complete Generate Module Workflow")
    print("="*60)
    
    try:
        # Step 1: Get sheets config
        print("\n1. Getting sheets config...")
        resp = requests.get(f'{base_url}/sheets-config')
        if resp.status_code != 200:
            print(f"ERROR: Failed to get sheets config: {resp.status_code}")
            return False
        print("✓ Sheets config loaded")
        
        # Step 2: Search for an article
        print("\n2. Searching for article...")
        resp = requests.get(f'{base_url}/search', params={'query': '01'})
        if resp.status_code != 200:
            print(f"ERROR: Search failed: {resp.status_code}")
            return False
        results = resp.json().get('results', [])
        if not results:
            print("WARNING: No articles found in search")
            # Let's just use a known article
            selected_artnr = '01'
        else:
            selected_artnr = results[0].get('artnr', '01')
        print(f"✓ Found article: {selected_artnr}")
        
        # Step 3: Check if BOM mapping files exist
        print("\n3. Checking BOM mapping files...")
        bom_sheets = [
            'Stücklisten',
            'Stücklistenversionen',
            'Stücklistenpositionen',
            'Stücklistenvarianten',
            'Stücklstenauswahlvarianten'
        ]
        
        base_dir = Path('.')
        missing_sheets = []
        for sheet in bom_sheets:
            mapping_path = base_dir / 'config' / 'sheet_mappings' / 'BOM' / f'mapping_plan_{sheet}.csv'
            if not mapping_path.exists():
                missing_sheets.append(sheet)
        
        if missing_sheets:
            print(f"WARNING: Missing BOM mapping files: {missing_sheets}")
        else:
            print("✓ All BOM mapping files exist")
        
        # Step 4: Check transform.py for errors
        print("\n4. Checking transform.py imports...")
        try:
            from etl.transform import build_bom_sheet_cache, build_sheet_cache_CSV, process_module_structure
            print("✓ All transform functions import successfully")
        except ImportError as e:
            print(f"ERROR: Import error in transform: {e}")
            return False
        
        # Step 5: Check load.py for errors
        print("\n5. Checking load.py imports...")
        try:
            from etl.load import create_import_excel_from_templates
            print("✓ Load functions import successfully")
        except ImportError as e:
            print(f"ERROR: Import error in load: {e}")
            return False
        
        # Step 6: Test the generate-module-data endpoint with minimal data
        print("\n6. Testing generate-module-data endpoint...")
        payload = {
            'selected_artnr': selected_artnr,
            'mode': 'module'
        }
        resp = requests.post(
            f'{base_url}/generate-module-data',
            json=payload,
            timeout=30
        )
        print(f"Response status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"✓ Generate module succeeded: {data.get('status')}")
            if 'warnings' in data:
                print(f"  Warnings: {data['warnings']}")
            return True
        else:
            print(f"ERROR: Generate module failed")
            if resp.text:
                error_text = resp.text[:500]
                print(f"  Response: {error_text}")
            return False
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_bom_functions():
    """Test BOM generation functions directly"""
    print("\n" + "="*60)
    print("TEST: BOM Sheet Generation Functions")
    print("="*60)
    
    try:
        from etl.transform import build_bom_sheet_cache
        from pathlib import Path
        
        # Create minimal test data
        base_dir = Path('.')
        processed_dir = base_dir / 'data' / 'processed'
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        partlist_path = processed_dir / 'test_partlist.csv'
        article_list_path = processed_dir / 'test_article_list.csv'
        
        # Create minimal test files
        with open(article_list_path, 'w', encoding='utf-8') as f:
            f.write('artnr;artbez1;zeichnr\n')
            f.write('01;OPTIONSTEXT;\n')
        
        with open(partlist_path, 'w', encoding='utf-8') as f:
            f.write('stulinr;posnr;menge;artnr;artbez1\n')
            f.write('01;1;1;01;OPTIONSTEXT\n')
        
        print(f"\n1. Testing build_bom_sheet_cache function...")
        try:
            result = build_bom_sheet_cache(str(partlist_path), str(article_list_path))
            if result['status'] == 'ok':
                print(f"✓ BOM sheet generation succeeded")
                print(f"  - Stücklisten count: {result.get('stuecklisten_count', 0)}")
                print(f"  - Versionen count: {result.get('versionen_count', 0)}")
                print(f"  - Positionen count: {result.get('positionen_count', 0)}")
                return True
            else:
                print(f"ERROR: BOM generation returned status: {result.get('status')}")
                return False
        except Exception as e:
            print(f"ERROR: BOM generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# Run tests
if __name__ == '__main__':
    results = {}
    
    results['generate_module'] = test_generate_module_workflow()
    results['bom_functions'] = test_bom_functions()
    
    # Summary
    print(f"\n\n{'='*60}")
    print("EXTENDED TEST SUMMARY")
    print(f"{'='*60}")
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    print(f"\nResult: {'ALL TESTS PASSED ✓' if all_passed else 'SOME TESTS FAILED ✗'}")
