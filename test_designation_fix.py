#!/usr/bin/env python3
"""Comprehensive test of matching fixes."""

from etl.transform import getBezeichnungselemente
import json

artnr = '10.10.0092'
elems = getBezeichnungselemente(artnr)

print("=== BEZEICHNUNGSELEMENTE RESOLUTION ===")
for elem in elems:
    print(f"{elem['name']:30} = {elem['value']}")

print("\n=== DETAILED VIEW ===")
print(json.dumps(elems, ensure_ascii=False, indent=2))
