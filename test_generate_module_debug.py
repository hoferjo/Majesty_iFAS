#!/usr/bin/env python3
"""Check the generate-module-data endpoint to see what error is returned"""
import requests
import json

base_url = 'http://127.0.0.1:8000'

# Test the generate-module-data endpoint with minimal data
print("Testing generate-module-data endpoint with debug output...\n")
payload = {
    'artnr': '01',
    'selected_headers': ['Artikelstamm'],
    'mode': 'module'
}
resp = requests.post(
    f'{base_url}/generate-module-data',
    json=payload,
    timeout=30
)
print(f"Response status: {resp.status_code}")
print(f"Response headers: {dict(resp.headers)}")
print(f"\nFull Response:")
print(json.dumps(resp.json(), indent=2))
