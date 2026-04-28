from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


def _load_settings(base_dir: Path) -> Dict[str, Any]:
    settings_path = base_dir / "config" / "settings.yaml"
    with open(settings_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _cache_paths(base_dir: Path) -> Tuple[Path, Path, Path, Path]:
    settings = _load_settings(base_dir)
    sheets_dir = base_dir / settings["paths"]["sheets_dir"]
    raw_dir = base_dir / settings["paths"]["raw_dir"]
    artikelstamm_path = raw_dir / "artikelstamm" / settings["files"]["artikelstamm"]
    artikelstamm_cache_path = sheets_dir / "Artikelstamm_cache.csv"
    lieferant_cache_path = sheets_dir / "ArtikelLieferantendaten_cache.csv"
    validation_overrides_path = sheets_dir / "Artikelbezeichnungen_validation_overrides.csv"
    return artikelstamm_path, artikelstamm_cache_path, lieferant_cache_path, validation_overrides_path


def _read_csv_rows(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    if not path.exists():
        return [], []
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        fieldnames = list(reader.fieldnames or [])
        rows = [{key: value or "" for key, value in row.items()} for row in reader]
    return fieldnames, rows


def _write_csv_rows(path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _row_map(rows: List[Dict[str, str]], key_field: str) -> Dict[str, Dict[str, str]]:
    mapped: Dict[str, Dict[str, str]] = {}
    for row in rows:
        key = str(row.get(key_field, "") or "").strip()
        if key and key not in mapped:
            mapped[key] = row
    return mapped


def _merge_fieldnames(existing: List[str], extra: List[str]) -> List[str]:
    merged = list(existing)
    seen = set(merged)
    for field in extra:
        if field not in seen:
            merged.append(field)
            seen.add(field)
    return merged


def _upsert_row(path: Path, key_field: str, key_value: str, updates: Dict[str, str]) -> None:
    fieldnames, rows = _read_csv_rows(path)
    if not fieldnames:
        fieldnames = [key_field]

    fieldnames = _merge_fieldnames(fieldnames, [key_field, *updates.keys()])
    updated = False
    for row in rows:
        if str(row.get(key_field, "") or "").strip() == key_value:
            row.update({field: value for field, value in updates.items() if value is not None})
            row[key_field] = key_value
            updated = True
            break

    if not updated:
        new_row = {field: "" for field in fieldnames}
        new_row[key_field] = key_value
        new_row.update({field: value for field, value in updates.items() if value is not None})
        rows.append(new_row)

    _write_csv_rows(path, fieldnames, rows)


def load_article_validation_queue(base_dir: Path) -> Dict[str, Any]:
    artikelstamm_path, artikelstamm_cache_path, lieferant_cache_path, validation_overrides_path = _cache_paths(base_dir)

    _, artikelstamm_rows = _read_csv_rows(artikelstamm_path)
    _, artikelstamm_cache_rows = _read_csv_rows(artikelstamm_cache_path)
    _, lieferant_cache_rows = _read_csv_rows(lieferant_cache_path)
    _, validation_override_rows = _read_csv_rows(validation_overrides_path)

    artikelstamm_map = _row_map(artikelstamm_rows, "artnr")
    artikelstamm_cache_map = _row_map(artikelstamm_cache_rows, "Artikelnummer")
    lieferant_cache_map = _row_map(lieferant_cache_rows, "Artikelnummer")
    validation_override_map = _row_map(validation_override_rows, "artnr")

    ordered_artnrs: List[str] = []
    seen = set()
    for row in artikelstamm_cache_rows:
        artnr = str(row.get("Artikelnummer", "") or "").strip()
        if artnr and artnr not in seen:
            ordered_artnrs.append(artnr)
            seen.add(artnr)
    for row in lieferant_cache_rows:
        artnr = str(row.get("Artikelnummer", "") or "").strip()
        if artnr and artnr not in seen:
            ordered_artnrs.append(artnr)
            seen.add(artnr)

    items: List[Dict[str, Any]] = []
    for artnr in ordered_artnrs:
        raw_row = artikelstamm_map.get(artnr, {})
        article_row = artikelstamm_cache_map.get(artnr, {})
        supplier_row = lieferant_cache_map.get(artnr, {})
        override_row = validation_override_map.get(artnr, {})
        items.append({
            "artnr": artnr,
            "bezeichnung1_de": override_row.get("bezeichnung1_de", "") or article_row.get("Bezeichnung 1 [de]", "") or "",
            "bezeichnung2_de": override_row.get("bezeichnung2_de", "") or article_row.get("Bezeichnung 2 [de]", "") or "",
            "lieferant_bezeichnung": override_row.get("lieferant_bezeichnung", "") or supplier_row.get("Artikelbezeichnung Lieferant", "") or "",
            "lieferant_zusatz": override_row.get("lieferant_zusatz", "") or supplier_row.get("Artikel-Zusatz-Bezeichnung Lieferant", "") or "",
            "artbez1": raw_row.get("artbez1", "") or "",
            "artbez2": raw_row.get("artbez2", "") or "",
            "artbez3": raw_row.get("artbez3", "") or "",
            "artbezmem": raw_row.get("artbezmem", "") or "",
        })

    return {
        "status": "ok",
        "count": len(items),
        "items": items,
    }


def save_article_validation_item(base_dir: Path, artnr: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    artnr = str(artnr or "").strip()
    if not artnr:
        return {"status": "error", "message": "artnr is required"}

    artikelstamm_path, artikelstamm_cache_path, lieferant_cache_path, validation_overrides_path = _cache_paths(base_dir)

    normalized_updates = {
        key: "" if value is None else str(value)
        for key, value in (updates or {}).items()
    }

    article_updates = {
        "Bezeichnung 1 [de]": normalized_updates.get("bezeichnung1_de", ""),
        "Bezeichnung 2 [de]": normalized_updates.get("bezeichnung2_de", ""),
    }
    supplier_updates = {
        "Artikelbezeichnung Lieferant": normalized_updates.get("lieferant_bezeichnung", ""),
        "Artikel-Zusatz-Bezeichnung Lieferant": normalized_updates.get("lieferant_zusatz", ""),
    }
    raw_updates = {
        "artbez1": normalized_updates.get("artbez1", ""),
        "artbez2": normalized_updates.get("artbez2", ""),
        "artbez3": normalized_updates.get("artbez3", ""),
        "artbezmem": normalized_updates.get("artbezmem", ""),
    }
    override_updates = {
        "bezeichnung1_de": normalized_updates.get("bezeichnung1_de", ""),
        "bezeichnung2_de": normalized_updates.get("bezeichnung2_de", ""),
        "lieferant_bezeichnung": normalized_updates.get("lieferant_bezeichnung", ""),
        "lieferant_zusatz": normalized_updates.get("lieferant_zusatz", ""),
    }

    _upsert_row(artikelstamm_cache_path, "Artikelnummer", artnr, article_updates)
    _upsert_row(lieferant_cache_path, "Artikelnummer", artnr, supplier_updates)
    _upsert_row(artikelstamm_path, "artnr", artnr, raw_updates)
    _upsert_row(validation_overrides_path, "artnr", artnr, override_updates)

    return {"status": "ok", "artnr": artnr}