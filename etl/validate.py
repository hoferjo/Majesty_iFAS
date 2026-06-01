from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

# Import transform for group computation
import json

from etl.transform import getArticleGroup, _load_yaml_cached, _group_value_to_text, getBezeichnungselemente


def _normalize_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", normalized.lower())


def _select_bezeichnungen_template(base_dir: Path, artnr: str, bezeichnungen_cfg: Dict[str, Any]) -> Dict[str, str]:
    if not isinstance(bezeichnungen_cfg, dict):
        return {}

    top_cfg = bezeichnungen_cfg.get("Normteile") or {}
    if not isinstance(top_cfg, dict):
        return {}

    try:
        _, ug, spec = getArticleGroup(artnr)
    except Exception:
        ug, spec = "", ""

    # Prefer matching by specification layers (for DIN branches), then subgroup.
    spec_candidates: List[str] = []
    if isinstance(spec, list):
        spec_candidates.extend([str(x).strip() for x in spec if str(x or "").strip()])
    else:
        spec_text = str(spec or "").strip()
        if spec_text:
            spec_candidates.append(spec_text)

    if str(ug or "").strip():
        spec_candidates.append(str(ug).strip())

    for key in spec_candidates:
        if key in top_cfg and isinstance(top_cfg.get(key), dict):
            return top_cfg.get(key) or {}

    # Normalized fallback to handle tiny naming differences.
    normalized_index = {
        _normalize_key(k): v
        for k, v in top_cfg.items()
        if isinstance(v, dict)
    }
    for key in spec_candidates:
        hit = normalized_index.get(_normalize_key(key))
        if isinstance(hit, dict):
            return hit

    return {}


def _build_placeholder_values(bezeichnungselemente: List[Dict[str, Any]]) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for item in (bezeichnungselemente or []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "").strip()
        value = str(item.get("value", "") or "").strip()
        if not name:
            continue
        values[name] = value
        values[_normalize_key(name)] = value

    # Common aliases and typo-tolerant keys used in templates.
    if "Metrischer Nenndurchmesser" in values:
        m = values.get("Metrischer Nenndurchmesser", "")
        values["Metrische Nenndurchmesser"] = m
        values[_normalize_key("Metrische Nenndurchmesser")] = m
    if "Außendurchmesser" in values and "Aussendurchmesser" not in values:
        a = values.get("Außendurchmesser", "")
        values["Aussendurchmesser"] = a
        values[_normalize_key("Aussendurchmesser")] = a
    if "Aussendurchmesser" in values and "Außendurchmesser" not in values:
        a = values.get("Aussendurchmesser", "")
        values["Außendurchmesser"] = a
        values[_normalize_key("Außendurchmesser")] = a

    return values


def _render_bezeichnung_template(template: str, placeholder_values: Dict[str, str]) -> str:
    text = str(template or "")

    def repl(match: re.Match[str]) -> str:
        key = (match.group(1) or "").strip()
        direct = placeholder_values.get(key)
        if direct is not None:
            return str(direct)
        return str(placeholder_values.get(_normalize_key(key), ""))

    rendered = re.sub(r"\{([^{}]+)\}", repl, text)
    rendered = re.sub(r"\s+,", ",", rendered)
    rendered = re.sub(r",\s*,+", ", ", rendered)
    rendered = re.sub(r"\s{2,}", " ", rendered)
    return rendered.strip(" ,;-")


def overwrite_bezeichnungen_from_config(base_dir: Path) -> Dict[str, Any]:
    artikelstamm_path, artikelstamm_cache_path, lieferant_cache_path, validation_overrides_path = _cache_paths(base_dir)

    bezeichnungen_cfg = _load_yaml_cached(Path(base_dir) / "config" / "Bezeichnungen.yaml") or {}
    article_fields, article_rows = _read_csv_rows(artikelstamm_cache_path)
    supplier_fields, supplier_rows = _read_csv_rows(lieferant_cache_path)
    _, validation_override_rows = _read_csv_rows(validation_overrides_path)

    validation_override_map = _row_map(validation_override_rows, "artnr")

    article_fields = _merge_fieldnames(article_fields, ["Artikelnummer", "Bezeichnung 1 [de]", "Bezeichnung 2 [de]"])
    supplier_fields = _merge_fieldnames(
        supplier_fields,
        ["Artikelnummer", "Artikelbezeichnung Lieferant", "Artikel-Zusatz-Bezeichnung Lieferant"],
    )

    article_updated = 0
    supplier_updated = 0
    override_updated = 0

    for row in article_rows:
        artnr = str(row.get("Artikelnummer", "") or "").strip()
        if not artnr:
            continue

        template_set = _select_bezeichnungen_template(base_dir, artnr, bezeichnungen_cfg)
        if not template_set:
            continue

        elements = getBezeichnungselemente(artnr) or []
        placeholders = _build_placeholder_values(elements)

        b1 = _render_bezeichnung_template(template_set.get("Bezeichnung 1", ""), placeholders)
        b2 = _render_bezeichnung_template(template_set.get("Bezeichnung 2", ""), placeholders)
        lb = _render_bezeichnung_template(template_set.get("Artikelbezeichnung Lieferant", ""), placeholders)
        lz = _render_bezeichnung_template(template_set.get("Artikel-Zusatz-Bezeichnung", ""), placeholders)

        row["Bezeichnung 1 [de]"] = b1
        row["Bezeichnung 2 [de]"] = b2
        article_updated += 1

        override_row = validation_override_map.get(artnr, {})
        override_updates = {
            "bezeichnung1_de": b1,
            "bezeichnung2_de": b2,
            "lieferant_bezeichnung": lb,
            "lieferant_zusatz": lz,
            "hauptgruppe": override_row.get("hauptgruppe", "") or "",
            "untergruppe": override_row.get("untergruppe", "") or "",
            "spezifikation": override_row.get("spezifikation", "") or "",
            "bezeichnungselemente": override_row.get("bezeichnungselemente", "") or "",
        }
        _upsert_row(validation_overrides_path, "artnr", artnr, override_updates)
        override_updated += 1

    supplier_map = _row_map(supplier_rows, "Artikelnummer")
    for artnr, row in supplier_map.items():
        template_set = _select_bezeichnungen_template(base_dir, artnr, bezeichnungen_cfg)
        if not template_set:
            continue
        elements = getBezeichnungselemente(artnr) or []
        placeholders = _build_placeholder_values(elements)

        row["Artikelbezeichnung Lieferant"] = _render_bezeichnung_template(
            template_set.get("Artikelbezeichnung Lieferant", ""), placeholders
        )
        row["Artikel-Zusatz-Bezeichnung Lieferant"] = _render_bezeichnung_template(
            template_set.get("Artikel-Zusatz-Bezeichnung", ""), placeholders
        )
        supplier_updated += 1

    _write_csv_rows(artikelstamm_cache_path, article_fields, article_rows)
    _write_csv_rows(lieferant_cache_path, supplier_fields, supplier_rows)

    return {
        "status": "ok",
        "artikelstamm_rows_updated": article_updated,
        "lieferant_rows_updated": supplier_updated,
        "overrides_rows_updated": override_updated,
        "artikelstamm_cache": str(artikelstamm_cache_path),
        "lieferant_cache": str(lieferant_cache_path),
    }


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


def load_article_group_validation_queue(base_dir: Path) -> Dict[str, Any]:
    """Return list of articles to validate groups with available options.

    Each item contains artnr, artbez1..mem and current hauptgruppe/untergruppe/spezifikation
    plus lists of available options for the dropdowns based on config/groups.yaml.
    """
    artikelstamm_path, artikelstamm_cache_path, lieferant_cache_path, validation_overrides_path = _cache_paths(base_dir)

    # reuse the same ordered list as the existing validation queue
    queue = load_article_validation_queue(base_dir)
    items = queue.get('items', [])

    groups_cfg = _load_yaml_cached(Path(base_dir) / 'config' / 'groups.yaml') or {}

    result_items: List[Dict[str, Any]] = []
    # load validation overrides so we can prefer persisted presets
    _, validation_override_rows = _read_csv_rows(validation_overrides_path)
    validation_override_map = _row_map(validation_override_rows, "artnr")
    for itm in items:
        artnr = itm.get('artnr')
        try:
            hg, ug, spec = getArticleGroup(artnr)
        except Exception:
            hg, ug, spec = ('', '', '')

        override_row = validation_override_map.get(str(artnr or ''), {})
        preset_hg = str(override_row.get('hauptgruppe', '') or hg or '')
        preset_ug = str(override_row.get('untergruppe', '') or ug or '')
        preset_spec = str(override_row.get('spezifikation', '') or _group_value_to_text(spec) or '')

        # resolve bezeichnungselemente for UI display (list of {name, value})
        try:
            bezeichnungselemente = getBezeichnungselemente(
                artnr,
                group_path={
                    'hauptgruppe': preset_hg,
                    'untergruppe': preset_ug,
                    'spezifikation': preset_spec,
                },
            ) or []
        except Exception:
            bezeichnungselemente = []

        # build options: always include config options + preserve presets even if stale/misspelled
        hauptgruppen = list(groups_cfg.keys()) if isinstance(groups_cfg, dict) else []
        untergruppen = []
        spezifikationen = []
        
        # Load options based on current hauptgruppe (hg) if preset_hg exists in config
        current_hauptgruppe = preset_hg if (isinstance(groups_cfg, dict) and preset_hg in groups_cfg) else hg
        
        # Load untergruppen from current hauptgruppe
        if isinstance(groups_cfg, dict) and current_hauptgruppe in groups_cfg and isinstance(groups_cfg.get(current_hauptgruppe), dict):
            untergruppen = list(groups_cfg.get(current_hauptgruppe).keys())
            # Load spezifikationen from current untergruppe if it exists
            if current_hauptgruppe in groups_cfg and isinstance(groups_cfg.get(current_hauptgruppe), dict):
                ug_to_check = preset_ug if preset_ug in groups_cfg.get(current_hauptgruppe, {}) else (groups_cfg.get(current_hauptgruppe, {}).get(list(groups_cfg.get(current_hauptgruppe, {}).keys())[0]) if groups_cfg.get(current_hauptgruppe, {}) else None)
                if preset_ug and isinstance(groups_cfg.get(current_hauptgruppe, {}).get(preset_ug), dict):
                    spezifikationen = list(groups_cfg.get(current_hauptgruppe, {}).get(preset_ug).keys())
        
        # Always add presets to options even if not in config (in case of stale/misspelled values)
        if preset_hg and preset_hg not in hauptgruppen:
            hauptgruppen.append(preset_hg)
        if preset_ug and preset_ug not in untergruppen:
            untergruppen.append(preset_ug)
        if preset_spec and preset_spec not in spezifikationen:
            spezifikationen.append(preset_spec)

        result_items.append({
            'artnr': artnr,
            'artbez1': itm.get('artbez1', ''),
            'artbez2': itm.get('artbez2', ''),
            'artbez3': itm.get('artbez3', ''),
            'artbezmem': itm.get('artbezmem', ''),
            'hauptgruppe': preset_hg,
            'untergruppe': preset_ug,
            'spezifikation': preset_spec,
            'spezifikation_layers': spec if isinstance(spec, list) else [],
            'preset_hauptgruppe': preset_hg,
            'preset_untergruppe': preset_ug,
            'preset_spezifikation': preset_spec,
            'bezeichnungselemente': bezeichnungselemente,
            'hauptgruppen_options': hauptgruppen,
            'untergruppen_options': untergruppen,
            'spezifikation_options': spezifikationen,
        })

    return {'status': 'ok', 'count': len(result_items), 'items': result_items, 'groups_tree': groups_cfg}
    


def save_article_group_item(base_dir: Path, artnr: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Save group/subgroup/spec overrides for an article into the validation overrides CSV.

    This will upsert fields `hauptgruppe`, `untergruppe`, `spezifikation` into the same overrides file used
    for Bezeichnung overrides so the UI can persist choices.
    """
    artnr = str(artnr or '').strip()
    if not artnr:
        return {'status': 'error', 'message': 'artnr required'}

    artikelstamm_path, artikelstamm_cache_path, lieferant_cache_path, validation_overrides_path = _cache_paths(base_dir)

    # Normalize values to strings
    normalized = {k: ('' if v is None else str(v)) for k, v in (updates or {}).items()}

    override_updates = {
        'hauptgruppe': normalized.get('hauptgruppe', ''),
        'untergruppe': normalized.get('untergruppe', ''),
        'spezifikation': normalized.get('spezifikation', ''),
        'bezeichnungselemente': json.dumps(updates.get('bezeichnungselemente', []), ensure_ascii=False),
        'bezeichnung1_de': normalized.get('bezeichnung1_de', ''),
        'bezeichnung2_de': normalized.get('bezeichnung2_de', ''),
    }

    _upsert_row(validation_overrides_path, 'artnr', artnr, override_updates)
    return {'status': 'ok', 'artnr': artnr}


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
        "hauptgruppe": normalized_updates.get("hauptgruppe", ""),
        "untergruppe": normalized_updates.get("untergruppe", ""),
        "spezifikation": normalized_updates.get("spezifikation", ""),
    }

    _upsert_row(artikelstamm_cache_path, "Artikelnummer", artnr, article_updates)
    _upsert_row(lieferant_cache_path, "Artikelnummer", artnr, supplier_updates)
    _upsert_row(artikelstamm_path, "artnr", artnr, raw_updates)
    _upsert_row(validation_overrides_path, "artnr", artnr, override_updates)

    return {"status": "ok", "artnr": artnr}


def add_group_entry(base_dir: Path, hauptgruppe: str | None, untergruppe: str | None, spezifikation: str | None) -> Dict[str, Any]:
    """Add a new hauptgruppe/untergruppe/spezifikation into config/groups.yaml.

    - If only `hauptgruppe` is provided, add a new top-level group.
    - If `hauptgruppe` and `untergruppe` provided, add the untergruppe under the hauptgruppe.
    - If all three provided, add the spezifikation under hauptgruppe->untergruppe.

    Returns a status dict.
    """
    config_path = Path(base_dir) / 'config' / 'groups.yaml'
    if not config_path.parent.exists():
        return {'status': 'error', 'message': f'Config path not found: {config_path.parent}'}

    try:
        data = {}
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as handle:
                data = yaml.safe_load(handle) or {}
        # Ensure dict
        if not isinstance(data, dict):
            data = {}

        hg = (str(hauptgruppe or '')).strip()
        ug = (str(untergruppe or '')).strip()
        spec = (str(spezifikation or '')).strip()

        if not hg:
            return {'status': 'error', 'message': 'hauptgruppe is required'}

        # Add hauptgruppe if missing
        if hg not in data:
            data[hg] = {}

        # If only hauptgruppe requested, persist and return
        if hg and not ug and not spec:
            with open(config_path, 'w', encoding='utf-8') as handle:
                yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)
            return {'status': 'ok', 'message': f'Added hauptgruppe {hg}'}

        # Ensure untergruppe exists under hauptgruppe
        if ug:
            if not isinstance(data.get(hg), dict):
                data[hg] = {}
            if ug not in data[hg]:
                data[hg][ug] = {}

        # If only hauptgruppe+untergruppe requested, persist and return
        if hg and ug and not spec:
            with open(config_path, 'w', encoding='utf-8') as handle:
                yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)
            return {'status': 'ok', 'message': f'Added untergruppe {ug} under {hg}'}

        # Add specification under hauptgruppe->untergruppe
        if hg and ug and spec:
            if not isinstance(data.get(hg), dict):
                data[hg] = {}
            if not isinstance(data[hg].get(ug), dict):
                data[hg][ug] = {}
            # Add spec as key with null value
            if spec not in data[hg][ug]:
                data[hg][ug][spec] = None

            with open(config_path, 'w', encoding='utf-8') as handle:
                yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)
            return {'status': 'ok', 'message': f'Added spezifikation {spec} under {hg}/{ug}'}

        return {'status': 'error', 'message': 'No action taken'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def load_article_group_validation_queue_from_csv(base_dir: Path, csv_path: Path) -> Dict[str, Any]:
    """Load a group-validation queue from a simple CSV of created articles.

    Expected CSV columns (semicolon-delimited): artnr;zeichnr;zeichindex;description
    Returns items in the same shape as `load_article_group_validation_queue` so the UI can reuse it.
    """
    groups_cfg = _load_yaml_cached(Path(base_dir) / 'config' / 'groups.yaml') or {}

    # read csv_path with semicolon delimiter
    if not csv_path.exists():
        return {'status': 'error', 'message': f'Input CSV not found: {csv_path}'}

    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle, delimiter=';')
        rows = [ {k: (v or '') for k, v in row.items()} for row in reader ]

    result_items = []
    for row in rows:
        artnr = str(row.get('artnr', '') or '').strip()
        desc = str(row.get('description', '') or '').strip()
        saved_hg = str(row.get('hauptgruppe', '') or '').strip()
        saved_ug = str(row.get('untergruppe', '') or '').strip()
        saved_spec = str(row.get('spezifikation', '') or '').strip()

        try:
            hg, ug, spec = getArticleGroup(artnr)
        except Exception:
            hg, ug, spec = ('', '', '')

        preset_hg = saved_hg or hg or ''
        preset_ug = saved_ug or ug or ''
        preset_spec = saved_spec or (_group_value_to_text(spec) if spec is not None else '')

        hauptgruppen = list(groups_cfg.keys()) if isinstance(groups_cfg, dict) else []
        untergruppen = []
        spezifikationen = []

        current_hauptgruppe = preset_hg if (isinstance(groups_cfg, dict) and preset_hg in groups_cfg) else (hg or preset_hg)
        if isinstance(groups_cfg, dict) and current_hauptgruppe in groups_cfg and isinstance(groups_cfg.get(current_hauptgruppe), dict):
            untergruppen = list(groups_cfg.get(current_hauptgruppe).keys())
            if preset_ug and isinstance(groups_cfg.get(current_hauptgruppe, {}).get(preset_ug), dict):
                spezifikationen = list(groups_cfg.get(current_hauptgruppe, {}).get(preset_ug).keys())

        if preset_hg and preset_hg not in hauptgruppen:
            hauptgruppen.append(preset_hg)
        if preset_ug and preset_ug not in untergruppen:
            untergruppen.append(preset_ug)
        if preset_spec and preset_spec not in spezifikationen:
            spezifikationen.append(preset_spec)

        result_items.append({
            'artnr': artnr,
            'artbez1': desc,
            'artbez2': '',
            'artbez3': '',
            'artbezmem': '',
            'hauptgruppe': preset_hg,
            'untergruppe': preset_ug,
            'spezifikation': preset_spec,
            'spezifikation_layers': spec if isinstance(spec, list) else [],
            'preset_hauptgruppe': preset_hg,
            'preset_untergruppe': preset_ug,
            'preset_spezifikation': preset_spec,
            'bezeichnungselemente': getBezeichnungselemente(
                artnr,
                group_path={
                    'hauptgruppe': preset_hg,
                    'untergruppe': preset_ug,
                    'spezifikation': preset_spec,
                },
            ) or [],
            'hauptgruppen_options': hauptgruppen,
            'untergruppen_options': untergruppen,
            'spezifikation_options': spezifikationen,
        })

    return {'status': 'ok', 'count': len(result_items), 'items': result_items, 'groups_tree': groups_cfg}


def save_article_group_item_to_csv(base_dir: Path, artnr: str, updates: Dict[str, Any], out_path: Path) -> Dict[str, Any]:
    """Persist group overrides for an article into a CSV at `out_path`.

    This behaves like `save_article_group_item` but writes to the specified CSV file (semicolon-delimited).
    """
    artnr = str(artnr or '').strip()
    if not artnr:
        return {'status': 'error', 'message': 'artnr required'}

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing rows
    fieldnames, rows = _read_csv_rows(out_path) if out_path.exists() else ([], [])

    key_field = 'artnr'
    if not fieldnames:
        fieldnames = [key_field, 'hauptgruppe', 'untergruppe', 'spezifikation', 'bezeichnungselemente']
    else:
        fieldnames = _merge_fieldnames(fieldnames, [key_field, 'hauptgruppe', 'untergruppe', 'spezifikation', 'bezeichnungselemente'])

    # Normalize updates
    normalized = {k: ('' if v is None else (json.dumps(v, ensure_ascii=False) if k == 'bezeichnungselemente' else str(v))) for k, v in (updates or {}).items()}

    updated = False
    for row in rows:
        if str(row.get(key_field, '') or '').strip() == artnr:
            row.update({field: normalized.get(field, row.get(field, '')) for field in fieldnames})
            row[key_field] = artnr
            updated = True
            break

    if not updated:
        new_row = {f: '' for f in fieldnames}
        new_row[key_field] = artnr
        for field in ['hauptgruppe', 'untergruppe', 'spezifikation', 'bezeichnungselemente']:
            new_row[field] = normalized.get(field, '')
        rows.append(new_row)

    _write_csv_rows(out_path, fieldnames, rows)
    return {'status': 'ok', 'artnr': artnr, 'output': str(out_path)}