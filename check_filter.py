#!/usr/bin/env python3
"""Check filter results"""
import csv

with open('data/processed/cache/created_articles/test_holzer.csv') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i < 5:
            print(f"Row {i}: drawing={row['drawing_number']}, cat={row['category']}, subcat={row['subcategory']}")
        if i == 5:
            break
