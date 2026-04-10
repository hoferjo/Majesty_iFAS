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



settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
etl_dir = Path(__file__).parent.parent / "etl"
sys.path.append(str(etl_dir))
article_list_path = Path(__file__).parent.parent / "data" / "processed" / "csv" / "cache" / "article_list.csv"

from etl.transform import process_module_structure, build_sheet_cache_CSV
from etl.load import (
    create_import_excel_from_templates,
    archive_module_export,
    resolve_existing_articles_file,
    append_article_list_to_existing,
    update_existing_articles_from_ifas_upload,
    create_partlist_excel_from_template,
)

app = FastAPI()

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
    artikelstamm_path = base / "data" / "raw" / "artikelstamm" / "artikelstamm_majesty_2026_03_30.csv"
    stueckliste_path = base / "data" / "raw" / "stücklistenstamm" / "20410917_stuelipo.csv"
    article_list_path = base / "data" / "processed" / "csv" / "cache" / "article_list.csv"
    partlist_path = base / "data" / "processed" / "csv" / "cache" / "partlist.csv"
    try:
        existing_articles_file = resolve_existing_articles_file(base, existing_articles_target)
        _MODULE_EXISTING_TARGET_CACHE[str(artnr)] = existing_articles_target

        process_module_structure(
            str(artnr),
            str(artikelstamm_path),
            str(stueckliste_path),
            str(article_list_path),
            str(partlist_path),
            existing_articles_file=str(existing_articles_file) if existing_articles_file else None,
            replacement_map=normalized_replacement_map,
        )
        _MODULE_ARTICLES_CACHE[str(artnr)] = _read_article_list_rows(article_list_path)

        # Count rows in article_list.csv and partlist.csv (excluding header)
        def count_csv_rows(path):
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    return sum(1 for _ in f) - 1
            except Exception:
                return 0

        article_count = count_csv_rows(article_list_path)
        partlist_count = count_csv_rows(partlist_path)
        blocked_articles_path = base / "data" / "processed" / "csv" / "cache" / "blocked_articles.csv"
        blocked_count = count_csv_rows(blocked_articles_path)
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
    artikelstamm_path = base / "data" / "raw" / "artikelstamm" / "artikelstamm_majesty_2026_03_30.csv"
    stueckliste_path = base / "data" / "raw" / "stücklistenstamm" / "20410917_stuelipo.csv"
    article_list_path = base / "data" / "processed" / "csv" / "cache" / "article_list.csv"
    partlist_path = base / "data" / "processed" / "csv" / "cache" / "partlist.csv"
    blocked_articles_path = base / "data" / "processed" / "csv" / "cache" / "blocked_articles.csv"

    try:
        existing_articles_file = resolve_existing_articles_file(base, existing_articles_target)
        _MODULE_EXISTING_TARGET_CACHE[str(artnr)] = existing_articles_target

        process_module_structure(
            str(artnr),
            str(artikelstamm_path),
            str(stueckliste_path),
            str(article_list_path),
            str(partlist_path),
            existing_articles_file=str(existing_articles_file) if existing_articles_file else None,
            replacement_map=normalized_replacement_map,
        )

        _MODULE_ARTICLES_CACHE[str(artnr)] = _read_article_list_rows(article_list_path)

        def count_csv_rows(path):
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    return sum(1 for _ in f) - 1
            except Exception:
                return 0

        article_count = count_csv_rows(article_list_path)
        partlist_count = count_csv_rows(partlist_path)
        blocked_count = count_csv_rows(blocked_articles_path)
        blocked_articles_data = ""
        if blocked_count > 0 and blocked_articles_path.exists():
            with open(blocked_articles_path, "r", encoding="utf-8-sig") as f:
                blocked_articles_data = f.read()

        blocked_items = _read_blocked_article_details(blocked_articles_path, artikelstamm_path)

        msg = (
            f"Modulestructure generated for {artnr} articles to migrate: {article_count} "
            f"partlist entries: {partlist_count} blocked articles: {blocked_count}"
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

        article_list_path = base / "data" / "processed" / "csv" / "cache" / "article_list.csv"
        summary = update_existing_articles_from_ifas_upload(
            upload_path=uploaded_path,
            existing_articles_path=target_file,
            article_list_path=article_list_path,
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
    if not artnr:
        return {"status": "error", "message": "No artnr provided"}
    if not isinstance(selected_headers, list):
        return {"status": "error", "message": "selected_headers must be a list"}

    base = Path(__file__).parent.parent
    article_list_path = base / "data" / "processed" / "csv" / "cache" / "article_list.csv"
    sheets_path = base / "config" / "sheets.csv"
    active_sheets_path = base / "config" / "active_sheets.csv"
    sheets_output_dir = base / "data" / "processed" / "csv" / "cache" / "sheets"

    try:
        if not article_list_path.exists():
            return {
                "status": "error",
                "message": "article_list.csv not found. Generate module structure first."
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
        build_sheet_cache_CSV(str(article_list_path), build_sheet_names, articles=cached_articles)
        # Also generate for blocked articles
        blocked_articles_path = base / "data" / "processed" / "csv" / "cache" / "blocked_articles.csv"
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
def download_partlist_excel():
    base = Path(__file__).parent.parent
    partlist_csv = base / "data" / "processed" / "csv" / "cache" / "partlist.csv"
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
    partlist_path = base / "data" / "processed" / "csv" / "cache" / "partlist.csv"
    partlist_tree_path = base / "data" / "processed" / "csv" / "cache" / "partlist_tree.txt"
    article_list_path = base / "data" / "processed" / "csv" / "cache" / "article_list.csv"
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
):
    requested_target = _normalize_existing_target(existing_articles_target)
    cached_target = _MODULE_EXISTING_TARGET_CACHE.get(str(artnr), "none")
    effective_target = requested_target if requested_target != "none" else cached_target
    print(f"[DEBUG] /download-module-excel triggered for artnr={artnr}, target={effective_target}")
    base = Path(__file__).parent.parent

    template_path = base / "data" / "raw" / "templates" / "Vorlage_edit_jhofer.xlsx"
    cache_dir = base / "data" / "processed" / "csv" / "cache" / "sheets"
    partlist_path = base / "data" / "processed" / "csv" / "cache" / "partlist.csv"
    partlist_tree_path = base / "data" / "processed" / "csv" / "cache" / "partlist_tree.txt"
    article_list_path = base / "data" / "processed" / "csv" / "cache" / "article_list.csv"
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

        if effective_target in {"prod", "test"}:
            target_file = resolve_existing_articles_file(base, effective_target)
            append_article_list_to_existing(article_list_path, target_file)

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
def download_partlist_tree(artnr: str = Query(..., min_length=1)):
    base = Path(__file__).parent.parent
    partlist_tree_path = base / "data" / "processed" / "csv" / "cache" / "partlist_tree.txt"
    # Optionally, support per-artnr tree files if needed:
    # partlist_tree_path = base / "data" / "processed" / "csv" / "cache" / f"partlist_tree_{artnr}.txt"
    if not partlist_tree_path.exists():
        return JSONResponse(status_code=404, content={"error": f"partlist_tree.txt not found for {artnr}"})
    try:
        return FileResponse(str(partlist_tree_path), filename=f"partlist_tree_{artnr}.txt", media_type="text/plain")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    











