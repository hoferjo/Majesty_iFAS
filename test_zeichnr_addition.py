#!/usr/bin/env python3
"""
Test script to verify zeichnr is correctly added to existing articles
"""
import csv
import tempfile
from pathlib import Path
import sys

# Add etl to path
sys.path.insert(0, str(Path(__file__).parent / "etl"))

from etl.load import (
    append_article_list_to_existing,
    update_existing_articles_from_ifas_upload,
    _read_existing_article_keys,
)

def test_append_article_list_to_existing():
    """Test appending articles with zeichnr to existing articles file"""
    print("Testing append_article_list_to_existing...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create article_list.csv (semicolon-delimited with zeichnr)
        article_list_path = tmppath / "article_list.csv"
        with open(article_list_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["artnr", "artbez1", "zeichnr"], delimiter=";")
            writer.writeheader()
            writer.writerow({"artnr": "001", "artbez1": "Article 1", "zeichnr": "Z001"})
            writer.writerow({"artnr": "002", "artbez1": "Article 2", "zeichnr": ""})
            writer.writerow({"artnr": "003", "artbez1": "Article 3", "zeichnr": "Z003"})
        
        # Create initial existing_articles.csv
        existing_path = tmppath / "existing.csv"
        
        # First append
        count = append_article_list_to_existing(article_list_path, existing_path)
        print(f"  First append: {count} articles added")
        assert count == 3, f"Expected 3 articles, got {count}"
        
        # Verify content
        with open(existing_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter=",")
            rows = list(reader)
        
        print(f"  File content after first append:")
        for row in rows:
            print(f"    {row}")
        
        assert rows[0] == ["artnr", "zeichnr"], f"Expected header ['artnr', 'zeichnr'], got {rows[0]}"
        assert rows[1] == ["001", "Z001"], f"Expected row ['001', 'Z001'], got {rows[1]}"
        assert rows[2] == ["002", ""], f"Expected row ['002', ''], got {rows[2]}"
        assert rows[3] == ["003", "Z003"], f"Expected row ['003', 'Z003'], got {rows[3]}"
        
        # Test duplicate prevention
        count = append_article_list_to_existing(article_list_path, existing_path)
        print(f"  Second append: {count} articles added (should be 0)")
        assert count == 0, f"Expected 0 new articles, got {count}"
        
    print("  ✓ Test passed!\n")

def test_read_existing_article_keys():
    """Test reading existing article keys from new format"""
    print("Testing _read_existing_article_keys with new format...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create existing_articles.csv with new format (artnr, zeichnr)
        existing_path = tmppath / "existing.csv"
        with open(existing_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(["artnr", "zeichnr"])
            writer.writerow(["001", "Z001"])
            writer.writerow(["002", ""])
            writer.writerow(["003", "Z003"])
        
        # Read keys
        keys = _read_existing_article_keys(existing_path)
        print(f"  Keys read: {keys}")
        
        assert keys == {"001", "002", "003"}, f"Expected {{'001', '002', '003'}}, got {keys}"
    
    print("  ✓ Test passed!\n")

def test_read_existing_article_keys_old_format():
    """Test reading existing article keys from old format (backward compatibility)"""
    print("Testing _read_existing_article_keys with old format (backward compatibility)...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create existing_articles.csv with old format (artnr only)
        existing_path = tmppath / "existing_old.csv"
        with open(existing_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(["artnr"])
            writer.writerow(["001"])
            writer.writerow(["002"])
            writer.writerow(["003"])
        
        # Read keys
        keys = _read_existing_article_keys(existing_path)
        print(f"  Keys read from old format: {keys}")
        
        assert keys == {"001", "002", "003"}, f"Expected {{'001', '002', '003'}}, got {keys}"
    
    print("  ✓ Test passed!\n")

if __name__ == "__main__":
    print("=" * 60)
    print("Running zeichnr addition tests...")
    print("=" * 60 + "\n")
    
    try:
        test_append_article_list_to_existing()
        test_read_existing_article_keys()
        test_read_existing_article_keys_old_format()
        
        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
