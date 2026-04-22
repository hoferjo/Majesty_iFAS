#!/usr/bin/env python3
"""Test all workflows to ensure they run without errors"""
import requests
import json
import time
from pathlib import Path

base_url = 'http://127.0.0.1:8000'

def test_endpoint(name, method, endpoint, **kwargs):
    """Test an API endpoint"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    try:
        if method == 'GET':
            resp = requests.get(f'{base_url}{endpoint}', **kwargs, timeout=10)
        elif method == 'POST':
            resp = requests.post(f'{base_url}{endpoint}', **kwargs, timeout=10)
        else:
            print(f"Unknown method: {method}")
            return False
        
        print(f"Status: {resp.status_code}")
        
        if resp.status_code in [200, 201]:
            if 'application/json' in resp.headers.get('Content-Type', ''):
                data = resp.json()
                if isinstance(data, dict):
                    print(f"Response keys: {list(data.keys())}")
                elif isinstance(data, list):
                    print(f"Response count: {len(data)} items")
                    if len(data) > 0 and isinstance(data[0], dict):
                        print(f"First item keys: {list(data[0].keys())}")
            else:
                print(f"Response length: {len(resp.text)} bytes")
            return True
        else:
            print(f"Error status code: {resp.status_code}")
            if resp.text:
                print(f"Response: {resp.text[:500]}")
            return False
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

# Run tests
results = {}

# Test 1: Sheets config
results['sheets-config'] = test_endpoint(
    'Get Sheets Config',
    'GET',
    '/sheets-config'
)

# Test 2: Search
results['search'] = test_endpoint(
    'Search for Articles',
    'GET',
    '/search',
    params={'query': '01'}
)

# Test 3: Article list preview
results['article-list-preview'] = test_endpoint(
    'Get Article List Preview',
    'GET',
    '/article-list-preview'
)

# Test 4: Create root article endpoint
results['create-root-article'] = test_endpoint(
    'Create Root Article',
    'POST',
    '/api/create-root-article'
)

# Summary
print(f"\n\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
for test_name, passed in results.items():
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status} - {test_name}")

all_passed = all(results.values())
print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
