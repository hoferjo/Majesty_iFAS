from etl.create import ArticleCreator
from etl.extract import auto_update_dbf_csv
from etl.extract import extract_dbf_headers_and_rows
import threading
from pathlib import Path
from fastapi import Body
import sys
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import shutil
import os
import json
import csv
from fastapi import Query
from fastapi.responses import JSONResponse

BASE_DIR = Path(__file__).parent.parent

def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
    
settings_path = BASE_DIR / "config" / "settings.yaml"
settings = load_yaml(settings_path)
if not settings:
    raise RuntimeError(f"Failed to load settings from {settings_path}. File is empty or invalid.")
try:
    raw_dir = settings["paths"]["raw_dir"]
    artikelstamm_file = settings["files"]["artikelstamm"]
except Exception as e:
    raise RuntimeError(f"Error reading keys from settings.yaml: {e}")
etl_dir = BASE_DIR / settings["paths"]["etl_dir"]
sys.path.append(str(etl_dir))

artikelstamm_path = BASE_DIR / settings["paths"]["raw_dir"] / settings["files"]["artikelstamm"]
#waren_artikelgruppe_path = BASE_DIR / settings["paths"]["waren_artikelgruppe_dir"] / settings["files"]["waren_artikelgruppe"]
#lieferanten_mapping_path = BASE_DIR / settings["paths"]["lieferanten_mapping_dir"] / settings["files"]["lieferanten_mapping"]

article_list_article_mode_path = BASE_DIR / settings["paths"]["article_list_dir"] / settings["files"]["article_list_article_mode"]
article_list_module_mode_path = BASE_DIR / settings["paths"]["article_list_dir"] / settings["files"]["article_list_module_mode"]
article_list_creation_mode_path = BASE_DIR / settings["paths"]["article_list_dir"] / settings["files"]["article_list_creation_mode"]



existing_articles_PROD_path = BASE_DIR / settings["paths"]["existing_articles_dir"] / settings["files"]["existing_articles_PROD"]
existing_articles_TEST_path = BASE_DIR / settings["paths"]["existing_articles_dir"] / settings["files"]["existing_articles_TEST"]

from etl.transform import process_module_structure
from etl.load import (
    create_import_excel_from_templates,
    archive_module_export,
    resolve_existing_articles_file,
    append_article_list_to_existing,
    update_existing_articles_from_ifas_upload,
    create_partlist_excel_from_template,
)



app = FastAPI()

# --- Root Article/Module Creation Workflow ---
from fastapi import APIRouter
from typing import Dict, Any

@app.post("/api/create-root-article")
def api_create_root_article():
    """
    Returns the required fields for all active sheets, with default values if available.
    """
    base = Path(__file__).parent.parent
    _, headers, aliases, flags, active_headers, _ = _load_sheets_config(base)
    # For each active sheet, collect its fields (headers)
    active_sheets = []
    for idx, header in enumerate(headers):
        if header not in active_headers:
            continue
        alias = str(aliases[idx]).strip() if idx < len(aliases) else ""
        sheet_name = _resolve_sheet_for_mapping(base, header, alias)
        if not sheet_name:
            continue
        # Try to load default values from config/create_defaults.yaml if present
        defaults = {}
        defaults_path = base / "config" / "create_defaults.yaml"
        if defaults_path.exists():
            import yaml
            with open(defaults_path, "r", encoding="utf-8") as f:
                all_defaults = yaml.safe_load(f) or {}
            defaults = all_defaults.get(sheet_name, {})
        # For now, just use the header names as fields
        active_sheets.append({
            "sheet": sheet_name,
            "fields": list(defaults.keys()) if defaults else [],
            "defaults": defaults,
        })
    return {"status": "ok", "sheets": active_sheets}

# Global flag to clear article cache files after import
ARTICLE_CACHE_CLEAR = 0

# Keeps the latest generated module article rows per artnr in this process.
_MODULE_ARTICLES_CACHE = {}
_MODULE_EXISTING_TARGET_CACHE = {}


def _strip_trailing_empty(values):
    trimmed = list(values)
    while trimmed and str(trimmed[-1]).strip() == "":
        trimmed.pop()
    return trimmed


def _load_sheets_config(base: Path):
    sheets_path = base / "config" / "sheets.csv"
    if not sheets_path.exists():
        raise FileNotFoundError(f"sheets.csv not found at {sheets_path}")

    with open(sheets_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f, delimiter=';'))

    if not rows:
        raise ValueError("sheets.csv is empty.")

    headers = _strip_trailing_empty(rows[0])
    aliases = _strip_trailing_empty(rows[1]) if len(rows) > 1 else []
    flags = _strip_trailing_empty(rows[2]) if len(rows) > 2 else []

    active_headers = []
    for idx, header in enumerate(headers):
        flag = str(flags[idx]).strip().lower() if idx < len(flags) else "0"
        if flag in {"1", "true", "yes", "y", "on"}:
            active_headers.append(header)

    return sheets_path, headers, aliases, flags, active_headers, rows


def _mapping_exists(base: Path, sheet_name: str):
    return (base / "config" / f"mapping_plan_{sheet_name}.csv").exists()


def _resolve_sheet_for_mapping(base: Path, header: str, alias: str):
    candidates = []
    if alias:
        candidates.append(alias)
    if header:
        candidates.append(header)
        candidates.append(header.replace("_", ""))
    if alias and alias.endswith("steuerung"):
        candidates.append(alias + "en")
    if header and header.endswith("_steuerung"):
        candidates.append(header.replace("_", "") + "en")

    seen = set()
    for candidate in candidates:
        candidate = str(candidate).strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if _mapping_exists(base, candidate):
            return candidate
    return None


def _read_article_list_rows(article_list_path: Path):
    with open(article_list_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=';')
        return list(reader)


def _load_artikelstamm_details_map(artikelstamm_path: Path):
    details = {}
    if not artikelstamm_path.exists():
        return details
    with open(artikelstamm_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            artnr = str(row.get("artnr", "")).strip()
            if not artnr:
                continue
            details[artnr] = {
                "artnr": artnr,
                "artbez1": row.get("artbez1", "") or "",
                "artbez2": row.get("artbez2", "") or "",
                "artbez3": row.get("artbez3", "") or "",
                "artbezmem": row.get("artbezmem", "") or "",
                "zeichnr": row.get("zeichnr", "") or "",
            }
    return details


def _read_blocked_article_details(blocked_articles_path: Path, artikelstamm_path: Path):
    if not blocked_articles_path.exists():
        return []

    details_map = _load_artikelstamm_details_map(artikelstamm_path)
    blocked_items = []
    seen = set()

    with open(blocked_articles_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            artnr = str(row.get("artnr", "")).strip()
            if not artnr or artnr in seen:
                continue
            seen.add(artnr)

            enriched = details_map.get(artnr, {
                "artnr": artnr,
                "artbez1": row.get("artbez1", "") or "",
                "artbez2": "",
                "artbez3": "",
                "artbezmem": "",
                "zeichnr": row.get("zeichnr", "") or "",
            })
            blocked_items.append(enriched)

    return blocked_items


def _resolved_active_sheet_names(base: Path):
    _, headers, aliases, _, active_headers, _ = _load_sheets_config(base)
    active_set = set(active_headers)
    resolved = []
    for idx, header in enumerate(headers):
        if header not in active_set:
            continue
        alias = str(aliases[idx]).strip() if idx < len(aliases) else ""
        sheet_name = _resolve_sheet_for_mapping(base, header, alias)
        if sheet_name:
            resolved.append(sheet_name)
    return list(dict.fromkeys(resolved))


def _normalize_mode(mode: str | None, default: str = "module"):
    mode_value = str(mode or default).strip().lower()
    return "article" if mode_value == "article" else "module"


def _cache_paths(base: Path, mode: str):
    normalized_mode = _normalize_mode(mode)
    if normalized_mode == "creation":
        return {
            "mode": normalized_mode,
            "article_list": base / "data" / "processed" / "csv" / "cache" / "article_list_creation_mode.csv",
            "blocked_articles": base / "data" / "processed" / "csv" / "cache" / "blocked_articles_creation_mode.csv",
            "partlist": base / "data" / "processed" / "csv" / "cache" / "partlist_creation_mode.csv",
            "partlist_tree": base / "data" / "processed" / "csv" / "cache" / "partlist_creation_mode_tree.txt",
        }
    suffix = "article_mode" if normalized_mode == "article" else "module_mode"
    return {
        "mode": normalized_mode,
        "article_list": base / "data" / "processed" / "csv" / "cache" / f"article_list_{suffix}.csv",
        "blocked_articles": base / "data" / "processed" / "csv" / "cache" / f"blocked_articles_{suffix}.csv",
        "partlist": base / "data" / "processed" / "csv" / "cache" / f"partlist_{suffix}.csv",
        "partlist_tree": base / "data" / "processed" / "csv" / "cache" / f"partlist_{suffix}_tree.txt",
    }


def _reset_mode_cache_files(base: Path, mode: str):
    paths = _cache_paths(base, mode)
    headers = {
        "article_list": "artnr;artbez1;zeichnr\n",
        "blocked_articles": "artnr;artbez1;zeichnr\n",
        "partlist": "stulinr;posnr;menge;artnr;artbez1\n",
    }
    for key, header in headers.items():
        with open(paths[key], "w", encoding="utf-8") as f:
            f.write(header)
    if paths["partlist_tree"].exists():
        paths["partlist_tree"].unlink()
    return paths


def _count_csv_rows(path: Path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return max(sum(1 for _ in f) - 1, 0)
    except Exception:
        return 0


def _normalize_existing_target(value: str):
    target = str(value or "none").strip().lower()
    if target not in {"none", "prod", "test"}:
        raise ValueError("existing_articles_target must be one of: none, prod, test")
    return target

# Get the absolute path to the web directory
web_dir = Path(__file__).parent.absolute()

# Mount static files (JS, CSS)
app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    template_path = web_dir / "templates" / "index.html"
    return open(template_path, "r", encoding="utf-8").read()

@app.get("/settings", response_class=HTMLResponse)
def settings():
    template_path = web_dir / "templates" / "settings.html"
    return open(template_path, "r", encoding="utf-8").read()

@app.post("/upload-file")
def upload_file(file: UploadFile = File(...)):
    upload_dir = "data/uploaded_files"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "status": "uploaded"}



@app.get("/search")
def search(query: str = Query(..., min_length=1), mode: str = Query("article")):
    # Path to the artikelstamm CSV (adjust as needed)
    csv_path = Path(__file__).parent.parent / "data" / "raw" / "artikelstamm" / "artikelstamm_majesty_2026_03_30.csv"
    results = []
    # Map search fields for each mode
    if mode == "article":
        search_fields = ["artnr", "zeichnr", "artbez1", "artbez2", "artbez3"]
    elif mode == "module":
        # For now, use the same fields; adjust as needed for real module data
        search_fields = ["artnr", "zeichnr", "artbez1", "artbez2", "artbez3"]
    else:
        search_fields = ["artnr", "zeichnr", "artbez1", "artbez2", "artbez3"]
    try:
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                if any(query.lower() in str(row.get(field, '')).lower() for field in search_fields):
                    # Only include artnr, artbez1, zeichnr in the result
                    filtered = {
                        "artnr": row.get("artnr", ""),
                        "artbez1": row.get("artbez1", ""),
                        "zeichnr": row.get("zeichnr", "")
                    }
                    results.append(filtered)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    return {"results": results}


@app.get("/sheets-config")
def sheets_config():
    base = Path(__file__).parent.parent
    try:
        _, headers, _, _, active_headers, _ = _load_sheets_config(base)
        return {
            "status": "success",
            "headers": headers,
            "active_headers": active_headers,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})



# --- Generate Module endpoint ---
@app.post("/generate-module")
def generate_module(data: dict = Body(...)):
    artnr = data.get("artnr")
    existing_articles_target = _normalize_existing_target(data.get("existing_articles_target", "none"))
    replacement_map = data.get("replacement_map") or {}
    if not isinstance(replacement_map, dict):
        return JSONResponse(status_code=400, content={"status": "error", "message": "replacement_map must be an object"})

    normalized_replacement_map = {}
    for key, value in replacement_map.items():
        key_s = str(key or "").strip()
        value_s = str(value or "").strip()
        if key_s and value_s:
            normalized_replacement_map[key_s] = value_s

    if not artnr:
        return JSONResponse(status_code=400, content={"status": "error", "message": "No artnr provided"})

    # Define paths
    base = Path(__file__).parent.parent
    stueckliste_path = base / "data" / "raw" / "stücklistenstamm" / "20410917_stuelipo.csv"

    ####
    cache_paths = _cache_paths(base, "module")
    ####

    partlist_path = cache_paths["partlist"]
    blocked_articles_path = cache_paths["blocked_articles"]
    try:
        existing_articles_file = resolve_existing_articles_file(base, existing_articles_target)
        _MODULE_EXISTING_TARGET_CACHE[str(artnr)] = existing_articles_target

        process_module_structure(
            str(artnr),
            str(artikelstamm_path),
            str(stueckliste_path),
            str(article_list_module_mode_path),
            str(partlist_path),
            existing_articles_file=str(existing_articles_file) if existing_articles_file else None,
            replacement_map=normalized_replacement_map,
            reset_files=True,
        )
        _MODULE_ARTICLES_CACHE[str(artnr)] = _read_article_list_rows(article_list_module_mode_path)

        article_count = _count_csv_rows(article_list_module_mode_path)
        partlist_count = _count_csv_rows(partlist_path)
        blocked_count = _count_csv_rows(blocked_articles_path)
        blocked_articles_data = ""
        if blocked_count > 0 and blocked_articles_path.exists():
            with open(blocked_articles_path, "r", encoding="utf-8-sig") as f:
                blocked_articles_data = f.read()
        blocked_items = _read_blocked_article_details(blocked_articles_path, artikelstamm_path)

        msg = f"Modulestructure generated for {artnr} articles to migrate: {article_count} partlist entries: {partlist_count} blocked articles: {blocked_count}"
        return JSONResponse(status_code=200, content={
            "status": "success",
            "message": msg,
            "blocked_articles": blocked_articles_data,
            "blocked_items": blocked_items
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/generate-module-apply-replacements")
def generate_module_apply_replacements(data: dict = Body(...)):
    artnr = data.get("artnr")
    existing_articles_target = _normalize_existing_target(data.get("existing_articles_target", "none"))
    replacement_map = data.get("replacement_map") or {}

    if not artnr:
        return JSONResponse(status_code=400, content={"status": "error", "message": "No artnr provided"})
    if not isinstance(replacement_map, dict):
        return JSONResponse(status_code=400, content={"status": "error", "message": "replacement_map must be an object"})

    normalized_replacement_map = {}
    for key, value in replacement_map.items():
        key_s = str(key or "").strip()
        # Accept dict for textartikel action
        if isinstance(value, dict) and value.get("textartikel"):
            normalized_replacement_map[key_s] = {"textartikel": True}
        else:
            value_s = str(value or "").strip()
            if key_s and value_s:
                normalized_replacement_map[key_s] = value_s

    base = Path(__file__).parent.parent
    stueckliste_path = base / "data" / "raw" / "stücklistenstamm" / "20410917_stuelipo.csv"
    cache_paths = _cache_paths(base, "module")
    partlist_path = cache_paths["partlist"]
    blocked_articles_path = cache_paths["blocked_articles"]

    try:
        existing_articles_file = resolve_existing_articles_file(base, existing_articles_target)
        _MODULE_EXISTING_TARGET_CACHE[str(artnr)] = existing_articles_target

        process_module_structure(
            str(artnr),
            str(artikelstamm_path),
            str(stueckliste_path),
            str(article_list_module_mode_path),
            str(partlist_path),
            existing_articles_file=str(existing_articles_file) if existing_articles_file else None,
            replacement_map=normalized_replacement_map,
            reset_files=True,
        )

        _MODULE_ARTICLES_CACHE[str(artnr)] = _read_article_list_rows(article_list_module_mode_path)

        article_count = _count_csv_rows(article_list_module_mode_path)
        partlist_count = _count_csv_rows(partlist_path)
        blocked_count = _count_csv_rows(blocked_articles_path)
        blocked_articles_data = ""
        if blocked_count > 0 and blocked_articles_path.exists():
            with open(blocked_articles_path, "r", encoding="utf-8-sig") as f:
                blocked_articles_data = f.read()

        blocked_items = _read_blocked_article_details(blocked_articles_path, artikelstamm_path)

        msg = (
            f"Modulestructure generated for {artnr}: "
            f"articles to migrate: {article_count}, partlist entries: {partlist_count}, blocked articles: {blocked_count}"
        )

        return JSONResponse(status_code=200, content={
            "status": "success",
            "message": msg,
            "blocked_articles": blocked_articles_data,
            "blocked_items": blocked_items,
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/upload-ifas-artikelstamm")
def upload_ifas_artikelstamm(
    file: UploadFile = File(...),
    target_env: str = Form("test"),
):
    base = Path(__file__).parent.parent
    env = str(target_env or "").strip().lower()
    if env not in {"prod", "test"}:
        return JSONResponse(status_code=400, content={"status": "error", "message": "target_env must be prod or test"})

    try:
        target_file = resolve_existing_articles_file(base, env)
        if not target_file:
            return JSONResponse(status_code=400, content={"status": "error", "message": "No target file resolved"})

        upload_dir = base / "data" / "uploaded_files"
        upload_dir.mkdir(parents=True, exist_ok=True)
        uploaded_path = upload_dir / file.filename

        with open(uploaded_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        summary = update_existing_articles_from_ifas_upload(
            upload_path=uploaded_path,
            existing_articles_path=target_file,
        
        )

        return {
            "status": "success",
            "message": (
                f"Updated existing articles {env.upper()}: "
                f"uploaded={summary['uploaded_count']}, "
                f"added={summary['added_count']}"
            ),
            "summary": summary,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/generate-module-data")
def generate_module_data(data: dict = Body(...)):
    artnr = data.get("artnr")
    selected_headers = data.get("selected_headers", [])
    mode = _normalize_mode(data.get("mode"), "module")
    if not artnr:
        return {"status": "error", "message": "No artnr provided"}
    if not isinstance(selected_headers, list):
        return {"status": "error", "message": "selected_headers must be a list"}

    base = Path(__file__).parent.parent
    cache_paths = _cache_paths(base, mode)
    blocked_articles_path = cache_paths["blocked_articles"]
    sheets_path = base / "config" / "sheets.csv"
    active_sheets_path = base / "config" / "active_sheets.csv"
    sheets_output_dir = base / "data" / "processed" / "csv" / "cache" / "sheets"


    try:
        if not article_list_module_mode_path.exists():
            return {
                "status": "error",
                "message": f"{article_list_module_mode_path.name} not found. Generate {mode} structure first."
            }

        if not sheets_path.exists():
            return {
                "status": "error",
                "message": "sheets.csv not found in config."
            }

        sheets_output_dir.mkdir(parents=True, exist_ok=True)

        _, headers, aliases, _, _, rows = _load_sheets_config(base)
        selected_set = {str(h).strip() for h in selected_headers if str(h).strip()}

        unknown = [h for h in selected_set if h not in headers]
        if unknown:
            return {
                "status": "error",
                "message": f"Unknown sheet headers selected: {', '.join(sorted(unknown))}"
            }

        # Ensure at least 3 rows and normalize row lengths.
        while len(rows) < 3:
            rows.append([])
        rows[0] = headers
        if len(rows[1]) < len(headers):
            rows[1] = rows[1] + [""] * (len(headers) - len(rows[1]))
        rows[1] = rows[1][:len(headers)]
        rows[2] = ["1" if header in selected_set else "0" for header in headers]

        with open(sheets_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=';')
            for row in rows:
                writer.writerow(row)

        # Renew active_sheets.csv with only marked column headers.
        selected_in_order = [h for h in headers if h in selected_set]
        with open(active_sheets_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(selected_in_order)

        if not selected_in_order:
            return {
                "status": "error",
                "message": "No sheets selected."
            }

        # Build using resolvable mapping names from selected columns.
        build_sheet_names = []
        for idx, header in enumerate(headers):
            if header not in selected_set:
                continue
            alias = str(aliases[idx]).strip() if idx < len(aliases) else ""
            resolved = _resolve_sheet_for_mapping(base, header, alias)
            if resolved:
                build_sheet_names.append(resolved)

        build_sheet_names = list(dict.fromkeys(build_sheet_names))
        if not build_sheet_names:
            return {
                "status": "error",
                "message": "Selected sheets have no matching mapping_plan_*.csv files."
            }

        cached_articles = _MODULE_ARTICLES_CACHE.get(str(artnr))
        build_sheet_cache_CSV(str(article_list_module_mode_path), build_sheet_names, articles=cached_articles)
        # Also generate for blocked articles
        if blocked_articles_path.exists():
            with blocked_articles_path.open("r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=';')
                blocked_articles = list(reader)
            if blocked_articles:
                build_sheet_cache_CSV(str(blocked_articles_path), build_sheet_names, articles=blocked_articles)
        # After generating, count entries in each sheet's cache CSV
        sheet_entry_counts = []
        for sheet in build_sheet_names:
            cache_csv = base / "data" / "processed" / "csv" / "cache" / "sheets" / f'{sheet}_cache.csv'
            count = 0
            if cache_csv.exists():
                with cache_csv.open("r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.reader(f, delimiter=";")
                    next(reader, None)  # skip header
                    count = sum(1 for _ in reader)
            # Count blocked from *_cache_blocked.csv
            blocked_cache_csv = base / "data" / "processed" / "csv" / "cache" / "sheets" / f'{sheet}_cache_blocked.csv'
            blocked_count = 0
            if blocked_cache_csv.exists():
                with blocked_cache_csv.open("r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.reader(f, delimiter=";")
                    next(reader, None)
                    blocked_count = sum(1 for _ in reader)
            sheet_entry_counts.append(f"{sheet}: {count} entries, blocked: {blocked_count}")
        msg = "Module data generated. " + ", ".join(sheet_entry_counts)
        return {
            "status": "success",
            "message": msg
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}



# New endpoint: Download Partlist Excel
@app.get("/download-partlist-excel")
def download_partlist_excel(mode: str = Query("module")):
    base = Path(__file__).parent.parent
    partlist_csv = _cache_paths(base, mode)["partlist"]
    template_xlsx = base / "data" / "raw" / "templates" / "VorlageStücklisteV1.xlsx"
    output_xlsx = base / "data" / "processed" / "csv" / "cache" / "partlist_export.xlsx"
    if not partlist_csv.exists() or not template_xlsx.exists():
        return JSONResponse(status_code=404, content={"error": "partlist.csv or template not found."})
    create_partlist_excel_from_template(partlist_csv, template_xlsx, output_xlsx)
    return FileResponse(str(output_xlsx), filename="partlist_export.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/download-module-export")
def download_module_export(
    artnr: str = Query(..., min_length=1),
    existing_articles_target: str = Query("none"),
):
    requested_target = _normalize_existing_target(existing_articles_target)
    cached_target = _MODULE_EXISTING_TARGET_CACHE.get(str(artnr), "none")
    effective_target = requested_target if requested_target != "none" else cached_target
    print(f"[DEBUG] /download-module-export triggered for artnr={artnr}, target={effective_target}")
    base = Path(__file__).parent.parent

    template_path = base / "data" / "raw" / "templates" / "Vorlage_edit_jhofer.xlsx"
    cache_dir = base / "data" / "processed" / "csv" / "cache" / "sheets"
    cache_paths = _cache_paths(base, "module")
    partlist_path = cache_paths["partlist"]
    partlist_tree_path = cache_paths["partlist_tree"]
    archive_dir = base / "data" / "archive"
    temp_export_dir = base / "data" / "processed" / "csv" / "cache" / "export"
    temp_export_dir.mkdir(parents=True, exist_ok=True)

    if not template_path.exists():
        return JSONResponse(status_code=404, content={"status": "error", "message": f"Template not found: {template_path}"})

    try:
        sheet_names = _resolved_active_sheet_names(base)
        if not sheet_names:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "No active sheets resolved. Generate module data first or check settings."},
            )

        temp_excel_path = temp_export_dir / f"{artnr}_iFAS_import.xlsx"
        create_import_excel_from_templates(
            template_path=template_path,
            cache_dir=cache_dir,
            active_sheet_names=sheet_names,
            output_path=temp_excel_path,
            default_column_width=14,
        )

        # Existing articles append now only happens in /download-module-excel

        _, zip_path = archive_module_export(
            module_artnr=artnr,
            excel_path=temp_excel_path,
            partlist_csv_path=partlist_path,
            partlist_tree_path=partlist_tree_path,
            archive_dir=archive_dir,
        )

        return FileResponse(
            str(zip_path),
            media_type="application/zip",
            filename=zip_path.name,
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    

@app.get("/download-module-excel")
def download_module_excel(
    artnr: str = Query(..., min_length=1),
    existing_articles_target: str = Query("none"),
    mode: str = Query("module"),
):
    mode = _normalize_mode(mode, "module")
    requested_target = _normalize_existing_target(existing_articles_target)
    cached_target = _MODULE_EXISTING_TARGET_CACHE.get(str(artnr), "none")
    effective_target = requested_target if requested_target != "none" else cached_target
    print(f"[DEBUG] /download-module-excel triggered for artnr={artnr}, target={effective_target}, mode={mode}")
    base = Path(__file__).parent.parent

    template_path = base / "data" / "raw" / "templates" / "Vorlage_edit_jhofer.xlsx"
    cache_dir = base / "data" / "processed" / "csv" / "cache" / "sheets"
    cache_paths = _cache_paths(base, mode)
    partlist_path = cache_paths["partlist"]
    partlist_tree_path = cache_paths["partlist_tree"]
    archive_dir = base / "data" / "archive"
    temp_export_dir = base / "data" / "processed" / "csv" / "cache" / "export"
    temp_export_dir.mkdir(parents=True, exist_ok=True)

    if not template_path.exists():
        return JSONResponse(status_code=404, content={"status": "error", "message": f"Template not found: {template_path}"})

    global ARTICLE_CACHE_CLEAR
    try:
        sheet_names = _resolved_active_sheet_names(base)
        if not sheet_names:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "No active sheets resolved. Generate module data first or check settings."},
            )

        print(f"[DEBUG] /download-module-excel: artnr={artnr}, active_sheet_names={sheet_names}")
        temp_excel_path = temp_export_dir / f"{artnr}_iFAS_import.xlsx"
        print(f"[DEBUG] Creating Excel: template={template_path}, cache_dir={cache_dir}, output={temp_excel_path}")
        create_import_excel_from_templates(
            template_path=template_path,
            cache_dir=cache_dir,
            active_sheet_names=sheet_names,
            output_path=temp_excel_path,
            default_column_width=14,
        )
        print(f"[DEBUG] Excel creation complete for {artnr}")

        if mode == "module" and effective_target in {"prod", "test"}:
            target_file = resolve_existing_articles_file(base, effective_target)
            append_article_list_to_existing(article_list_module_mode_path, target_file)

        # Archive in background after sending Excel
        def archive_job():
            try:
                archive_module_export(
                    module_artnr=artnr,
                    excel_path=temp_excel_path,
                    partlist_csv_path=partlist_path,
                    partlist_tree_path=partlist_tree_path,
                    archive_dir=archive_dir,
                )
                print(f"[DEBUG] Archive complete for artnr={artnr}")
            except Exception as e:
                print(f"[ERROR] Archive failed for artnr={artnr}: {e}")

        threading.Thread(target=archive_job, daemon=True).start()

        if mode == "article":
            _reset_mode_cache_files(base, "article")
            ARTICLE_CACHE_CLEAR = 1

        return FileResponse(
            str(temp_excel_path),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=temp_excel_path.name,
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    
    
# --- Majesty DBF Extraction Endpoint ---
from etl.extract import auto_update_dbf_csv

@app.post("/update-majesty-data")
def update_majesty_data():
    try:
        updated = auto_update_dbf_csv()
        if updated:
            return {"status": "success", "message": f"Updated: {', '.join(updated)}"}
        else:
            return {"status": "success", "message": "No DBF files needed updating."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
    
@app.post("/hard-update-majesty-data")
def hard_update_majesty_data():
    try:
        updated = auto_update_dbf_csv(force=True)
        if updated:
            return {"status": "success", "message": f"Hard updated: {', '.join(updated)}"}
        else:
            # Check if there are any DBF files at all
            from pathlib import Path
            from etl.extract import dbfs_path
            dbf_dir = Path(dbfs_path)
            dbf_files = list(dbf_dir.glob("*.dbf"))
            if not dbf_files:
                return {"status": "error", "message": "No DBF files found in the Majesty DBF directory. Check your configuration and file locations."}
            else:
                return {"status": "success", "message": "No DBF files needed updating."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@app.get("/download-partlist-tree")
def download_partlist_tree(artnr: str = Query(..., min_length=1), mode: str = Query("module")):
    base = Path(__file__).parent.parent
    partlist_tree_path = _cache_paths(base, mode)["partlist_tree"]
    # Optionally, support per-artnr tree files if needed:
    # partlist_tree_path = base / "data" / "processed" / "csv" / "cache" / f"partlist_tree_{artnr}.txt"
    if not partlist_tree_path.exists():
        return JSONResponse(status_code=404, content={"error": f"partlist_tree.txt not found for {artnr} (mode={mode})"})
    try:
        return FileResponse(str(partlist_tree_path), filename=f"partlist_tree_{artnr}.txt", media_type="text/plain")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    

@app.post("/add-article")
def add_article(data: dict = Body(...)):
    artnr = data.get("artnr")
    if not artnr:
        return JSONResponse(status_code=400, content={"status": "error", "message": "No artnr provided"})

    base = Path(__file__).parent.parent
    artikelstamm_path = base / "data" / "raw" / "artikelstamm" / "artikelstamm_majesty_2026_03_30.csv"
    cache_paths = _cache_paths(base, "article")
    global ARTICLE_CACHE_CLEAR
    try:
        # If cache clear flag is set, clear article mode cache files and reset flag
        if ARTICLE_CACHE_CLEAR == 1:
            _reset_mode_cache_files(base, "article")
            ARTICLE_CACHE_CLEAR = 0
        import csv
        from etl.transform import check_utf8_file
        if not check_utf8_file(artikelstamm_path):
            return JSONResponse(status_code=500, content={"status": "error", "message": f"artikelstamm not valid UTF-8: {artikelstamm_path}"})
        # Read article-mode list entries to avoid duplicates
        existing_artnr = set()
        if article_list_article_mode_path.exists():
            with open(article_list_article_mode_path, 'r', encoding='utf-8-sig') as f:
                next(f, None)
                for line in f:
                    key = line.strip().split(';')[0].strip()
                    if key:
                        existing_artnr.add(key)
        # Also check both existing-articles targets, because these should not be appended either.
        existing_targets_artnr = set()
        for target in ["prod", "test"]:
            target_file = resolve_existing_articles_file(base, target)
            if not target_file or not target_file.exists():
                continue
            with open(target_file, 'r', encoding='utf-8-sig') as f:
                next(f, None)
                for line in f:
                    key = line.strip().split(',')[0].strip()
                    if key:
                        existing_targets_artnr.add(key)
        # Find the article in artikelstamm
        found = False
        with open(artikelstamm_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                if str(row.get('artnr', '')).strip() == str(artnr).strip():
                    artbez1 = row.get('artbez1', '')
                    zeichnr = row.get('zeichnr', '')
                    if artnr in existing_artnr:
                        return {
                            "status": "success",
                            "message": f"Article {artnr} already exists in article_list_article_mode.csv. Nothing appended."
                        }
                    if artnr in existing_targets_artnr:
                        return {
                            "status": "success",
                            "message": f"Article {artnr} already exists in existing articles (PROD/TEST). Nothing appended."
                        }
                    if artnr not in existing_artnr:
                        # Write header if file does not exist or is empty
                        write_header = not article_list_article_mode_path.exists() or article_list_article_mode_path.stat().st_size == 0
                        with open(article_list_article_mode_path, 'a', encoding='utf-8') as out:
                            if write_header:
                                out.write('artnr;artbez1;zeichnr\n')
                            out.write(f"{artnr};{artbez1};{zeichnr}\n")
                    found = True
                    break
        if not found:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Article {artnr} not found in artikelstamm."})
        return {"status": "success", "message": f"Added article {artnr} to article_list_article_mode.csv."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# --- Article Mode: Generate Article Export and Partlist ---
@app.post("/generate-article")
def generate_article(data: dict = Body(...)):
    artnr_list = data.get("artnr_list")
    if not artnr_list or not isinstance(artnr_list, list):
        return JSONResponse(status_code=400, content={"status": "error", "message": "No article list provided"})

    base = Path(__file__).parent.parent
    # Use dedicated creation mode cache files (CSV) for isolation
    creation_cache_dir = base / "data" / "processed" / "cache" / "created_articles"
    creation_partlist_path = creation_cache_dir / "partlist_creation_mode.csv"
    creation_partlist_tree_path = creation_cache_dir / "partlist_creation_mode_tree.txt"
    try:
        import csv
        from etl.transform import check_utf8_file, process_module_structure
        # Read existing articles to avoid duplicates
        existing_artnr = set()
        if article_list_creation_mode_path.exists():
            with open(article_list_creation_mode_path, 'r', encoding='utf-8-sig') as f:
                next(f, None)
                for line in f:
                    key = line.strip().split(';')[0].strip()
                    if key:
                        existing_artnr.add(key)
        # Generate export, partlist, and tree for all articles in the list
        write_header = not article_list_creation_mode_path.exists() or article_list_creation_mode_path.stat().st_size == 0
        for idx, artnr in enumerate(artnr_list):
            if not check_utf8_file(artikelstamm_path):
                return JSONResponse(status_code=500, content={"status": "error", "message": f"artikelstamm not valid UTF-8: {artikelstamm_path}"})
            # Find the article in artikelstamm
            found = False
            with open(artikelstamm_path, encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    if str(row.get('artnr', '')).strip() == str(artnr).strip():
                        artbez1 = row.get('artbez1', '')
                        zeichnr = row.get('zeichnr', '')
                        if artnr not in existing_artnr:
                            with open(article_list_creation_mode_path, 'a', encoding='utf-8') as out:
                                if write_header:
                                    out.write('artnr;artbez1;zeichnr\n')
                                    write_header = False
                                out.write(f"{artnr};{artbez1};{zeichnr}\n")
                            existing_artnr.add(artnr)
                        found = True
                        break
            if not found:
                return JSONResponse(status_code=404, content={"status": "error", "message": f"Article {artnr} not found in artikelstamm."})

            # Generate partlist and tree for this article (creation mode, isolated files)
            stueckliste_path = base / "data" / "raw" / "stücklistenstamm" / "20410917_stuelipo.csv"
            # Always reset files for the first article, then append for others
            reset_files = (idx == 0)
            process_module_structure(
                str(artnr),
                str(artikelstamm_path),
                str(stueckliste_path),
                str(article_list_creation_mode_path),
                str(creation_partlist_path),
                reset_files=reset_files
            )
        # Return download links (point to creation mode files if needed)
        return {
            "status": "success",
            "message": f"Generated export and partlist for {len(artnr_list)} articles (creation mode).",
            "creation_article_list": str(article_list_creation_mode_path.name),
            "creation_partlist": str(creation_partlist_path.name),
            "creation_partlist_tree": str(creation_partlist_tree_path.name)
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    
    
@app.post("/reset-article-list")
def reset_article_list():
    """Truncate article-mode list files and write only the headers."""
    base = Path(__file__).parent.parent
    _reset_mode_cache_files(base, "article")
    return {"status": "success", "message": "Article list reset."}

@app.get("/article-list-preview")
def article_list_preview():
    """Return the current contents of article_list_article_mode.csv as JSON."""
    try:
        base = Path(__file__).parent.parent
        article_list_creation_mode_path = _cache_paths(base, "article")["article_list"]
        with open(article_list_creation_mode_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            rows = list(reader)
        return {"status": "success", "rows": rows}
    except Exception as e:
        return {"status": "error", "message": str(e), "rows": []}

@app.post("/remove-article-from-list")
def remove_article_from_list(data: dict = Body(...)):
    """Remove an article by artnr from article_list_article_mode.csv."""
    artnr = str(data.get("artnr", "")).strip()
    if not artnr:
        return {"status": "error", "message": "No artnr provided."}
    base = Path(__file__).parent.parent
    article_list_creation_mode_path = _cache_paths(base, "article")["article_list"]
    try:
        # Read all rows except the one to remove
        with open(article_list_creation_mode_path, 'r', encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f, delimiter=';'))
        new_rows = [row for row in rows if str(row.get("artnr", "")).strip() != artnr]
        # Write back, preserving header
        with open(article_list_creation_mode_path, 'w', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["artnr", "artbez1", "zeichnr"], delimiter=';')
            writer.writeheader()
            for row in new_rows:
                writer.writerow(row)
        return {"status": "success", "message": f"Removed article {artnr} from list."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ─── Creation Session State ────────────────────────────────────────────────────

_creation_session: dict | None = None



# --- Creation Session CSV Storage ---
def _cs_cache_dir() -> Path:
    return Path(__file__).parent.parent / "data" / "processed" / "csv" / "cache"

def _cs_session_csv_path() -> Path:
    return _cs_cache_dir() / "creation_session.csv"

def _cs_new() -> dict:
    return {
        "is_active": False,
        "is_complete": False,
        "stack": [],
        "articles": [],
        "partlist_rows": [],
        "tree_lines": [],
    }

def _cs_save(session: dict) -> None:
    """Save the session to a single CSV file (creation_session.csv) and update partlist_creation_mode.csv for uniformity."""
    path = _cs_session_csv_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write all articles, partlist, and tree info in one CSV
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["type","artnr","artbez1","zeichnr","depth","posnr","menge","stulinr","tree_depth","tree_artnr","tree_artbez1","tree_zeichnr"])
        for a in session.get("articles", []):
            writer.writerow([
                a.get("type","article"), a.get("artnr",""), a.get("artbez1",""), a.get("zeichnr",""), a.get("depth",0), "", "", "", "", "", "", ""
            ])
        for p in session.get("partlist_rows", []):
            writer.writerow([
                "", p.get("artnr",""), p.get("artbez1",""), "", "", p.get("posnr",""), p.get("menge",""), p.get("stulinr",""), "", "", "", ""
            ])
        for t in session.get("tree_lines", []):
            writer.writerow([
                "", "", "", "", "", "", "", "", t.get("depth",0), t.get("artnr",""), t.get("artbez1",""), t.get("zeichnr","")
            ])

    # --- Uniform partlist file for creation mode ---
    partlist_path = _cs_cache_dir() / "partlist_creation_mode.csv"
    with open(partlist_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["stulinr","posnr","menge","artnr","artbez1"])
        for p in session.get("partlist_rows", []):
            writer.writerow([
                p.get("stulinr",""), p.get("posnr",""), p.get("menge",""), p.get("artnr",""), p.get("artbez1","")
            ])

def _cs_load() -> dict:
    """Load the session from the single CSV file (creation_session.csv)."""
    path = _cs_session_csv_path()
    session = _cs_new()
    if not path.exists():
        return session
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            # Article row
            if row["type"]:
                session["articles"].append({
                    "type": row["type"],
                    "artnr": row["artnr"],
                    "artbez1": row["artbez1"],
                    "zeichnr": row["zeichnr"],
                    "depth": int(row["depth"] or 0)
                })
            # Partlist row
            elif row["posnr"]:
                session["partlist_rows"].append({
                    "stulinr": row["stulinr"],
                    "posnr": int(row["posnr"] or 0),
                    "menge": int(row["menge"] or 0),
                    "artnr": row["artnr"],
                    "artbez1": row["artbez1"]
                })
            # Tree line
            elif row["tree_artnr"]:
                session["tree_lines"].append({
                    "depth": int(row["tree_depth"] or 0),
                    "artnr": row["tree_artnr"],
                    "artbez1": row["tree_artbez1"],
                    "zeichnr": row["tree_zeichnr"]
                })
    # Heuristics for is_active/is_complete/stack
    session["is_active"] = not session["is_complete"] and bool(session["stack"] or session["articles"])
    return session

def _cs_tree_text(session: dict) -> str:
    lines = []
    for item in session.get("tree_lines", []):
        depth = item.get("depth", 0)
        artnr = item.get("artnr", "")
        artbez1 = item.get("artbez1", "")
        zeichnr = item.get("zeichnr", "")
        indent = "  " * depth
        zeichnr_part = f" | {zeichnr}" if zeichnr else ""
        lines.append(f"{indent}{artnr} | {artbez1}{zeichnr_part}")
    return "\n".join(lines)


def _cs_do_create_article(creator: "ArticleCreator", type_name: str, input_data: dict, cache_dir: Path) -> dict:
    """Create + save YAML cache for one article. Returns article field dict."""
    article = creator.create_article(type_name, input_data)
    artnr = input_data.get("artnr") or input_data.get("modnr") or "article"
    cache_path = cache_dir / f"{type_name}_{artnr}.yaml"
    creator.save_article_cache(article, cache_path)
    return article


@app.get("/api/creation/state")
def api_creation_state():
    """Return the current creation session state."""
    session = _cs_load()
    if not session:
        empty = _cs_new()
        return {**empty, "tree_text": ""}
    return {**session, "tree_text": _cs_tree_text(session)}


@app.post("/api/creation/start")
def api_creation_start(data: dict = Body(...)):
    """Start a new creation session with a root article/module."""
    config_dir = Path(__file__).parent.parent / "config"
    creator = ArticleCreator(config_dir)
    type_name = data.get("type")
    if not type_name:
        return {"status": "error", "message": "No article type provided."}
    tpl = creator.get_template(type_name)
    if not tpl:
        return {"status": "error", "message": f"Template '{type_name}' not found."}
    input_data = {k: v for k, v in data.items() if k not in ("type", "is_module")}
    cache_dir = _cs_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        _cs_do_create_article(creator, type_name, input_data, cache_dir)
    except Exception as e:
        return {"status": "error", "message": str(e)}
    artnr = input_data.get("artnr") or input_data.get("modnr") or "root_article"
    artbez1 = input_data.get("artbez1", "")
    zeichnr = input_data.get("zeichnr", "")
    session = _cs_new()
    session["is_active"] = True
    session["stack"] = [{"artnr": artnr, "artbez1": artbez1, "zeichnr": zeichnr, "pos_counter": 1}]
    session["articles"] = [{"artnr": artnr, "artbez1": artbez1, "zeichnr": zeichnr, "type": type_name, "depth": 0}]
    session["tree_lines"] = [{"depth": 0, "artnr": artnr, "artbez1": artbez1, "zeichnr": zeichnr}]
    _cs_save(session)
    _cs_append_article_list(cache_dir, artnr, artbez1, zeichnr)
    _cs_flush_to_csv(session, cache_dir)
    return {"status": "success", "artnr": artnr, "state": {**session, "tree_text": _cs_tree_text(session)}}


@app.post("/api/creation/add-child")
def api_creation_add_child(data: dict = Body(...)):
    """Add a child article or module to the current parent."""
    session = _cs_load()
    if not session or not session.get("is_active"):
        return {"status": "error", "message": "No active creation session. Start a root article first."}
    stack = session.get("stack", [])
    if not stack:
        return {"status": "error", "message": "No parent in stack."}
    config_dir = Path(__file__).parent.parent / "config"
    creator = ArticleCreator(config_dir)
    type_name = data.get("type")
    is_module = bool(data.get("is_module", False))
    if not type_name:
        return {"status": "error", "message": "No article type provided."}
    tpl = creator.get_template(type_name)
    if not tpl:
        return {"status": "error", "message": f"Template '{type_name}' not found."}
    input_data = {k: v for k, v in data.items() if k not in ("type", "is_module")}
    cache_dir = _cs_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        _cs_do_create_article(creator, type_name, input_data, cache_dir)
    except Exception as e:
        return {"status": "error", "message": str(e)}
    artnr = input_data.get("artnr") or input_data.get("modnr") or "article"
    artbez1 = input_data.get("artbez1", "")
    zeichnr = input_data.get("zeichnr", "")
    parent = stack[-1]
    depth = len(stack)
    # Partlist row
    pos_counter = parent["pos_counter"]
    session["partlist_rows"].append({
        "stulinr": parent["artnr"],
        "posnr": pos_counter,
        "menge": 1,
        "artnr": artnr,
        "artbez1": artbez1,
    })
    session["stack"][-1]["pos_counter"] = pos_counter + 1
    # Register article
    session["articles"].append({"artnr": artnr, "artbez1": artbez1, "zeichnr": zeichnr, "type": type_name, "depth": depth})
    session["tree_lines"].append({"depth": depth, "artnr": artnr, "artbez1": artbez1, "zeichnr": zeichnr})
    # If it's a module, push it onto the stack so subsequent children attach to it
    if is_module:
        session["stack"].append({"artnr": artnr, "artbez1": artbez1, "zeichnr": zeichnr, "pos_counter": 1})
    _cs_save(session)
    _cs_append_article_list(cache_dir, artnr, artbez1, zeichnr)
    _cs_flush_to_csv(session, cache_dir)
    return {"status": "success", "artnr": artnr, "is_module": is_module, "state": {**session, "tree_text": _cs_tree_text(session)}}


@app.post("/api/creation/finish-module")
def api_creation_finish_module():
    """Finish the current module and go up one level. If at root, mark session complete."""
    session = _cs_load()
    if not session or not session.get("is_active"):
        return {"status": "error", "message": "No active creation session."}
    stack = session.get("stack", [])
    if len(stack) <= 1:
        session["is_active"] = False
        session["is_complete"] = True
        _cs_save(session)
        _cs_flush_to_csv(session, _cs_cache_dir())
        return {"status": "complete", "message": "Root module finished. Session complete.", "state": {**session, "tree_text": _cs_tree_text(session)}}
    session["stack"].pop()
    _cs_save(session)
    return {"status": "success", "state": {**session, "tree_text": _cs_tree_text(session)}}


@app.post("/api/creation/reset")
def api_creation_reset():
    """Reset the creation session and clear related files."""
    global _creation_session
    _creation_session = None
    cache_dir = _cs_cache_dir()
    for fname in [
        "creation_session.json",
        "article_list_creation_mode.csv",
        "partlist_creation_mode.csv",
        "partlist_creation_mode_tree.txt",
    ]:
        p = cache_dir / fname
        if p.exists():
            p.unlink()
    return {"status": "success", "message": "Creation session reset."}


# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/article-types")
def api_article_types():
    """
    Returns a list of available article types/templates from article_templates.yaml
    """
    config_dir = Path(__file__).parent.parent / "config"
    creator = ArticleCreator(config_dir)
    types = creator.list_templates()
    return {"types": types}

@app.get("/api/article-fields")
def api_article_fields(type: str):
    """
    Returns the fields for a given article type/template.
    """
    config_dir = Path(__file__).parent.parent / "config"
    creator = ArticleCreator(config_dir)
    tpl = creator.get_template(type)
    if not tpl:
        return {"status": "error", "fields": []}
    # Return all fields with their properties
    fields = [f.as_dict() for f in tpl.fields]
    return {"status": "ok", "fields": fields}

@app.post("/api/generate-root-article")
def api_generate_root_article(data: dict = Body(...)):
    """
    Creates and saves a root article of the selected type with the provided data.
    """
    config_dir = Path(__file__).parent.parent / "config"
    creator = ArticleCreator(config_dir)
    type_name = data.get("type")
    if not type_name:
        return {"status": "error", "message": "No article type provided."}
    tpl = creator.get_template(type_name)
    if not tpl:
        return {"status": "error", "message": f"Template '{type_name}' not found."}
    # Remove 'type' from data
    input_data = {k: v for k, v in data.items() if k != "type"}
    try:
        article = creator.create_article(type_name, input_data)
        # Save to cache (YAML for now, could be CSV)
        artnr = input_data.get("artnr") or input_data.get("modnr") or "root_article"
        cache_path = Path(__file__).parent.parent / "data" / "processed" / "csv" / "cache" / f"{type_name}_{artnr}.yaml"
        creator.save_article_cache(article, cache_path)

        # --- Also append to partlist_creation_mode.csv and partlist_creation_mode_tree.txt ---
        cache_dir = Path(__file__).parent.parent / "data" / "processed" / "csv" / "cache"
        partlist_path = cache_dir / "partlist_creation_mode.csv"
        tree_path = cache_dir / "partlist_creation_mode_tree.txt"

        # Compose values for partlist and tree
        artbez1 = input_data.get("artbez1", "")
        zeichnr = input_data.get("zeichnr", "")
        # For partlist: stulinr;posnr;menge;artnr;artbez1
        partlist_row = {
            "stulinr": artnr,
            "posnr": "1",
            "menge": "1",
            "artnr": artnr,
            "artbez1": artbez1
        }
        # Write header if file does not exist
        write_header = not partlist_path.exists() or partlist_path.stat().st_size == 0
        with open(partlist_path, "a", encoding="utf-8") as f:
            if write_header:
                f.write("stulinr;posnr;menge;artnr;artbez1\n")
            f.write(f"{partlist_row['stulinr']};{partlist_row['posnr']};{partlist_row['menge']};{partlist_row['artnr']};{partlist_row['artbez1']}\n")

        # For tree: artnr, artbez1, zeichnr
        with open(tree_path, "a", encoding="utf-8") as f:
            f.write(f"{artnr}, {artbez1}, {zeichnr}\n")

        return {"status": "success", "message": f"{type_name} created and saved as {cache_path.name}. Also added to partlist and tree.", "article": article}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/check-article-exists")
def check_article_exists(artnr: str, mode: str = Query("article")):
    """
    Check if an article exists in Majesty data (artikelstamm CSV) or in creation cache if mode=creation.
    """
    base = Path(__file__).parent.parent
    if mode == "creation":
        # Check active session articles first (in-memory)
        active_session = _cs_load()
        if active_session:
            for art in active_session.get("articles", []):
                if str(art.get("artnr", "")).strip() == str(artnr).strip():
                    return {"status": "found_in_creation", "artnr": artnr, "data": art}
        # Fallback: check creation cache CSV
        article_list_creation_mode_path = base / "data" / "processed" / "csv" / "cache" / "article_list_creation_mode.csv"
        if article_list_creation_mode_path.exists():
            with open(article_list_creation_mode_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    if str(row.get("artnr", "")).strip() == str(artnr).strip():
                        return {"status": "found_in_creation", "artnr": artnr, "data": row}
    # Always check Majesty data as well
    if not artikelstamm_path.exists():
        return {"status": "error", "message": "Majesty artikelstamm not found."}
    with open(artikelstamm_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if str(row.get("artnr", "")).strip() == str(artnr).strip():
                return {"status": "found", "artnr": artnr, "data": row}
    return {"status": "not_found", "artnr": artnr}

# Live field-by-field YAML cache endpoint
@app.post("/api/cache-article-field")
def cache_article_field(data: dict = Body(...)):
    """
    Cache a single field value for an article/module to a YAML file.
    Expects: {"cache_id": str, "field": str, "value": any}
    """
    cache_id = str(data.get("cache_id") or "").strip()
    field = str(data.get("field") or "").strip()
    value = data.get("value")
    if not cache_id or not field:
        return {"status": "error", "message": "cache_id and field required"}
    base = Path(__file__).parent.parent
    cache_dir = base / "data" / "processed" / "csv" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{cache_id}.yaml"
    # Load existing cache
    cache_data = {}
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            try:
                cache_data = yaml.safe_load(f) or {}
            except Exception:
                cache_data = {}
    cache_data[field] = value
    with open(cache_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(cache_data, f, allow_unicode=True)
    return {"status": "ok", "cache_id": cache_id, "field": field, "value": value}

@app.get("/api/search-lieferant")
def search_lieferant(q: str = Query("", min_length=1)):
    """
    Search lieferanten_mapping.csv for supplier by name or ifas_nummer. Returns list of dicts with ifas_nummer and name.
    """
    base = Path(__file__).parent.parent
    mapping_path = base / "config" / "lieferanten_mapping.csv"
    results = []
    if not mapping_path.exists():
        return JSONResponse(status_code=404, content={"error": "lieferanten_mapping.csv not found"})
    try:
        with open(mapping_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=';' if ';' in f.read(1024) else ',')
            f.seek(0)
            for row in reader:
                ifas_nummer = str(row.get("ifas_nummer", "")).strip()
                name = str(row.get("name", "")).strip()
                # Search in ifas_nummer or name (case-insensitive)
                if q.lower() in ifas_nummer.lower() or q.lower() in name.lower():
                    results.append({"ifas_nummer": ifas_nummer, "name": name})
                    if len(results) >= 20:
                        break
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    return results

@app.get("/download-partlist")
def download_partlist(artnr: str = Query(..., min_length=1), mode: str = Query("creation")):
    """Download the partlist CSV for the current session (creation mode)."""
    base = Path(__file__).parent.parent
    partlist_path = _cache_paths(base, mode)["partlist"]
    if not partlist_path.exists():
        return JSONResponse(status_code=404, content={"error": f"partlist.csv not found for {artnr} (mode={mode})"})
    try:
        return FileResponse(str(partlist_path), filename=f"partlist_{artnr}.csv", media_type="text/csv")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- Download Group Excel for Creation Session ---
@app.get("/download-group-excel")
def download_group_excel(artnr: str = Query(..., min_length=1), mode: str = Query("creation")):
    """Download a group Excel (XLSX) for the current creation session."""
    base = Path(__file__).parent.parent
    partlist_csv = _cache_paths(base, mode)["partlist"]
    template_xlsx = base / "data" / "raw" / "templates" / "VorlageStücklisteV1.xlsx"
    output_xlsx = base / "data" / "processed" / "csv" / "cache" / f"group_export_{artnr}.xlsx"
    if not partlist_csv.exists() or not template_xlsx.exists():
        return JSONResponse(status_code=404, content={"error": "partlist.csv or template not found."})
    try:
        create_partlist_excel_from_template(partlist_csv, template_xlsx, output_xlsx)
        return FileResponse(str(output_xlsx), filename=f"group_export_{artnr}.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
