import csv
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter

BASE_DIR = Path(__file__).parent.parent



"""
def resolve_existing_articles_file(base_dir, target):
    
    #Resolve existing articles destination file for target in {'prod','test'}.
    #Returns None when target is empty/none.
    
    normalized = str(target or "").strip().lower()
    if normalized in {"", "none", "off", "false", "0"}:
        return None

    mapping = {
        "prod": "existing_articles_PROD.csv",
        "test": "existing_articles_TEST.csv",
    }
    if normalized not in mapping:
        raise ValueError("existing_articles_target must be one of: none, prod, test")

    cache_dir = Path(base_dir) / "data" / "processed" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / mapping[normalized]
"""

def _read_existing_article_keys(path: Path):
    keys = set()
    if not path.exists():
        return keys

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=",")
        rows = list(reader)

    if not rows:
        return keys

    header = [str(c or "").strip().lower() for c in rows[0]]
    data_rows = rows[1:] if header and "artnr" in header else rows
    idx = header.index("artnr") if header and "artnr" in header else 0

    for row in data_rows:
        if idx < len(row):
            key = str(row[idx] or "").strip()
            if key:
                keys.add(key)
    return keys



def _detect_encoding(file_path: Path):
    """Detect encoding for uploaded text/csv file (UTF-8, UTF-16, Latin1 fallback)."""
    with open(file_path, "rb") as f:
        raw = f.read(4096)
    # BOM detection
    if raw.startswith(b"\xff\xfe"):
        return "utf-16"
    if raw.startswith(b"\xfe\xff"):
        return "utf-16"
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    try:
        raw.decode("utf-8")
        return "utf-8"
    except Exception:
        pass
    try:
        raw.decode("latin1")
        return "latin1"
    except Exception:
        pass
    return "utf-8"  # fallback


def _extract_artnr_from_excel(file_path: Path):
    """
    Extract article numbers from the first worksheet of an Excel file.
    Supports files with or without a header row.
    """
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    try:
        if not wb.worksheets:
            return set()

        ws = wb.worksheets[0]
        rows = []
        for row in ws.iter_rows(values_only=True):
            normalized = [str(c or "").strip() for c in row]
            if any(normalized):
                rows.append(normalized)

        if not rows:
            return set()

        candidate_headers = {"artnr", "artikelnummer", "artikel_nr", "artikel-nr", "article", "article_no"}
        first_row_lower = [c.lower() for c in rows[0]]

        has_header = any(h in candidate_headers for h in first_row_lower)
        idx = 0
        if has_header:
            for i, h in enumerate(first_row_lower):
                if h in candidate_headers:
                    idx = i
                    break

        data_rows = rows[1:] if has_header else rows
        result = set()
        for row in data_rows:
            if idx < len(row):
                artnr = str(row[idx] or "").strip()
                if artnr:
                    result.add(artnr)
        return result
    finally:
        wb.close()

def _extract_artnr_from_file(file_path: Path):
    """
    Extract article numbers from uploaded iFAS artikelstamm files.
    - Text/CSV: supports ; , tab and pipe delimiters, with or without headers.
    - Excel: supports .xlsx/.xlsm/.xltx/.xltm (first worksheet).
    Handles UTF-8, UTF-16, and Latin1 encodings for text files.
    """
    if str(file_path.suffix or "").lower() in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        return _extract_artnr_from_excel(file_path)

    encoding = _detect_encoding(file_path)
    with file_path.open("r", encoding=encoding, newline="") as f:
        sample = f.read(4096)
        f.seek(0)

        delimiter = ";"
        scores = {
            ";": sample.count(";"),
            ",": sample.count(","),
            "\t": sample.count("\t"),
            "|": sample.count("|"),
        }
        delimiter = max(scores, key=scores.get) if sample else ";"

        reader = csv.reader(f, delimiter=delimiter)
        rows = [row for row in reader if any(str(c or "").strip() for c in row)]

    if not rows:
        return set()

    header = [str(c or "").strip().lower() for c in rows[0]]
    candidate_headers = {"artnr", "artikelnummer", "artikel_nr", "artikel-nr", "article", "article_no"}
    has_header = any(h in candidate_headers for h in header)
    idx = 0
    if has_header:
        for i, h in enumerate(header):
            if h in candidate_headers:
                idx = i
                break

    data_rows = rows[1:] if has_header else rows
    result = set()
    for row in data_rows:
        if idx < len(row):
            artnr = str(row[idx] or "").strip()
            if artnr:
                result.add(artnr)
    return result


def append_article_list_to_existing(article_list_path, existing_articles_path):
    """
    Add article_list.csv artnr values to existing articles csv (comma-separated, header: artnr).
    Returns number of new rows appended.
    """
    article_list_path = Path(article_list_path)
    existing_articles_path = Path(existing_articles_path)
    existing_articles_path.parent.mkdir(parents=True, exist_ok=True)

    existing_keys = _read_existing_article_keys(existing_articles_path)

    article_keys = []
    if article_list_path.exists():
        with article_list_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                key = str((row or {}).get("artnr", "") or "").strip()
                if key:
                    article_keys.append(key)

    to_add = [k for k in article_keys if k not in existing_keys]

    if not existing_articles_path.exists() or existing_articles_path.stat().st_size == 0:
        with existing_articles_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(["artnr"])

    if to_add:
        with existing_articles_path.open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=",")
            for key in to_add:
                writer.writerow([key])

    return len(to_add)


def update_existing_articles_from_ifas_upload(upload_path, existing_articles_path, article_list_path=None):
    """
    Overwrite existing_articles_{PROD|TEST}.csv with only the artnrs from the uploaded file.
    Returns summary dict.
    """
    upload_path = Path(upload_path)
    existing_articles_path = Path(existing_articles_path)

    uploaded_keys = sorted(_extract_artnr_from_file(upload_path))

    existing_articles_path.parent.mkdir(parents=True, exist_ok=True)
    with existing_articles_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(["artnr"])
        for key in uploaded_keys:
            writer.writerow([key])

    return {
        "uploaded_count": len(uploaded_keys),
        "added_count": len(uploaded_keys),
        "existing_total": len(uploaded_keys),
        "target_file": str(existing_articles_path),
    }


def _sanitize_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(value or ""))
    cleaned = cleaned.strip("_")
    return cleaned or "module"


def _normalize_key(value: str) -> str:
    return "".join(ch.lower() for ch in str(value or "") if ch.isalnum())


def _read_cache_rows(cache_csv_path: Path):
    if not cache_csv_path.exists():
        return [], []
    with cache_csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = list(reader)
        headers = list(reader.fieldnames or [])
    return rows, headers


def _build_referenz_lookup(template_wb):
    lookup = {}
    if "Referenz" not in template_wb.sheetnames:
        return lookup

    ws = template_wb["Referenz"]
    # Expected structure: col A = worksheet name, col B = db table name.
    for row in ws.iter_rows(min_row=1, max_col=2, values_only=True):
        sheet_name = str(row[0] or "").strip()
        db_name = str(row[1] or "").strip()
        if not sheet_name:
            continue
        lookup[_normalize_key(sheet_name)] = db_name
    return lookup


def _detect_header_row(first_7_rows, cache_headers):
    # Pick the row inside 1..7 with the highest overlap with cache CSV headers.
    cache_set = {_normalize_key(h) for h in cache_headers if str(h or "").strip()}
    best_row = 7
    best_score = -1

    for row_idx, row_vals in first_7_rows.items():
        template_headers = {_normalize_key(v) for v in row_vals if str(v or "").strip()}
        score = len(template_headers.intersection(cache_set))
        if score > best_score:
            best_score = score
            best_row = row_idx

    return best_row



def _copy_sheet_layout(template_ws, out_ws, first_rows_to_copy=7, safe_mode=True):
    # Copy only cell values from the first rows — no styles, no protection.
    # This avoids openpyxl IndexError caused by protection/style ID mismatches.
    max_col = template_ws.max_column
    for r in range(1, first_rows_to_copy + 1):
        for c in range(1, max_col + 1):
            src = template_ws.cell(row=r, column=c)
            out_ws.cell(row=r, column=c, value=src.value)

    return max_col


def create_import_excel_from_templates(
    template_path,
    cache_dir,
    active_sheet_names,
    output_path,
    default_column_width=14,
    safe_mode=True,
):
    """
    Build iFAS import workbook from template and cache files.
    - Copies first 7 rows and layout exactly from template sheets.
    - Matches cache columns to template headers found in first 7 rows.
    - Leaves unmatched template columns empty below row 7.
    - Keeps/updates hidden Referenz sheet with active sheet -> db table rows.
    - Forces all data cells to text format to preserve leading zeroes.
    """
    template_path = Path(template_path)
    cache_dir = Path(cache_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    wb_template = openpyxl.load_workbook(template_path)
    wb_out = openpyxl.Workbook()
    wb_out.remove(wb_out.active)

    # Build referenz_lookup as a list of (sheet_name, db_table) from the template Referenz sheet
    referenz_lookup = []
    if "Referenz" in wb_template.sheetnames:
        ws_ref_template = wb_template["Referenz"]
        for r in range(2, ws_ref_template.max_row + 1):
            sheet = str(ws_ref_template.cell(row=r, column=1).value or "").strip()
            db = str(ws_ref_template.cell(row=r, column=2).value or "").strip()
            if sheet:
                referenz_lookup.append((sheet, db))

    # Build a dict for fast lookup
    referenz_dict = {_normalize_key(sheet): db for sheet, db in referenz_lookup}

    # Process active sheets and collect their db table names
    active_referenz_rows = []
    for sheet_name in active_sheet_names:
        if sheet_name not in wb_template.sheetnames:
            print(f"[DEBUG] Sheet '{sheet_name}' not in template")
            continue

        cache_csv_path = cache_dir / f"{sheet_name}_cache.csv"
        cache_rows, cache_headers = _read_cache_rows(cache_csv_path)
        print(f"[DEBUG] Sheet: {sheet_name}, cache_rows: {len(cache_rows)}, cache_headers: {cache_headers}")
        if not cache_rows:
            raise ValueError(f"No entries in article list for module. Module already exists in iFAS {{TEST/PROD}} or no new articles to export for sheet '{sheet_name}'.")

        ws_template = wb_template[sheet_name]
        ws_out = wb_out.create_sheet(sheet_name)

        max_col = _copy_sheet_layout(ws_template, ws_out, first_rows_to_copy=7, safe_mode=safe_mode)
        print(f"[DEBUG] max_col={max_col} for sheet '{sheet_name}'")

        first_7 = {
            r: [ws_template.cell(row=r, column=c).value for c in range(1, max_col + 1)]
            for r in range(1, 8)
        }
        header_row_idx = _detect_header_row(first_7, cache_headers)
        print(f"[DEBUG] Detected header_row_idx={header_row_idx}")

        template_header_cells = [ws_template.cell(row=header_row_idx, column=c).value for c in range(1, max_col + 1)]
        print(f"[DEBUG] template_header_cells count={len(template_header_cells)}, sample={template_header_cells[:3]}")


        # Explicit mapping for headers that differ between cache and template
        header_aliases = {
            "zusatztextart 1": "Zusatztextart 1_x000d_\n(ISZTAId)",
            "zusatztextart 2": "Zusatztextart 2_x000d_\n(ISZTAId)",
            "sind zusatztexte rtf text?": "Sind Zusatztexte RTF Text? _x000d_\n(0 = nein, 1 = ja)",
        }
        cache_header_map = {}
        for h in cache_headers:
            norm_h = _normalize_key(h)
            # Use alias if present, else original
            if h in header_aliases:
                cache_header_map[_normalize_key(header_aliases[h])] = h
            else:
                cache_header_map[norm_h] = h

        data_start_row = 8
        for row_offset, cache_row in enumerate(cache_rows):
            excel_row = data_start_row + row_offset
            for col_idx, tpl_header in enumerate(template_header_cells, start=1):
                tpl_key = _normalize_key(tpl_header)
                if tpl_key:
                    cache_header = cache_header_map.get(tpl_key)
                    value = cache_row.get(cache_header, "") if cache_header else ""
                else:
                    value = ""
                try:
                    cell = ws_out.cell(row=excel_row, column=col_idx, value="" if value is None else str(value))
                    cell.number_format = "@"
                except Exception as e:
                    print(f"[DEBUG] Error setting cell({excel_row}, {col_idx}): {e}")

        for col_idx, tpl_header in enumerate(template_header_cells, start=1):
            tpl_key = _normalize_key(tpl_header)
            if not tpl_key:
                continue
            try:
                letter = get_column_letter(col_idx)
                for row in range(1, ws_out.max_row + 1):
                    cell = ws_out.cell(row=row, column=col_idx)
                    cell.number_format = "@"
            except Exception as e:
                print(f"[DEBUG] Error setting format for column {col_idx}: {e}")

        for col_idx, tpl_header in enumerate(template_header_cells, start=1):
            tpl_key = _normalize_key(tpl_header)
            if not tpl_key:
                continue
            letter = get_column_letter(col_idx)
            if ws_out.column_dimensions[letter].width is None:
                ws_out.column_dimensions[letter].width = default_column_width
            ws_out.column_dimensions[letter].width = max(ws_out.column_dimensions[letter].width or 0, default_column_width)

        # Add to referenz rows for output
        db_table = referenz_dict.get(_normalize_key(sheet_name), sheet_name)
        active_referenz_rows.append((sheet_name, db_table))

    # Create Referenz sheet from scratch: header + only active sheets
    ws_ref_out = wb_out.create_sheet("Referenz")
    ws_ref_out.cell(row=1, column=1, value="Worksheet").number_format = "@"
    ws_ref_out.cell(row=1, column=2, value="Tabelle").number_format = "@"
    for idx, (sheet, db) in enumerate(active_referenz_rows, start=2):
        ws_ref_out.cell(row=idx, column=1, value=sheet).number_format = "@"
        ws_ref_out.cell(row=idx, column=2, value=db).number_format = "@"

    try:
        print(f"[DEBUG] Saving workbook with {len(wb_out.sheetnames)} sheets: {wb_out.sheetnames}")
        for sheet_name in wb_out.sheetnames:
            ws = wb_out[sheet_name]
            print(f"[DEBUG] Sheet '{sheet_name}': max_row={ws.max_row}, max_col={ws.max_column}")
        wb_out.save(output_path)
        print(f"[DEBUG] Successfully saved Excel to {output_path}")
    except Exception as e:
        print(f"[ERROR] openpyxl failed to save Excel: {e}")
        import traceback
        traceback.print_exc()
        raise
    return output_path


def archive_module_export(module_artnr, excel_path, partlist_csv_path, partlist_tree_path, archive_dir):
    """
    Save artifacts under data/archive and create a zip named with the module.
    Returns: (archive_folder_path, zip_path)
    """
    module_name = _sanitize_name(module_artnr)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    archive_dir = Path(archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Instead of creating a folder, just zip the files directly and remove any temp folders
    excel_path = Path(excel_path)
    partlist_csv_path = Path(partlist_csv_path)
    partlist_tree_path = Path(partlist_tree_path)

    zip_path = archive_dir / f"{module_name}_{stamp}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Add Excel
        if excel_path.exists():
            zf.write(excel_path, arcname=f"{module_name}_iFAS_import.xlsx")
        # Add partlist CSV
        if partlist_csv_path.exists():
            zf.write(partlist_csv_path, arcname=f"partlist_{module_name}.csv")
        # Add partlist tree
        if partlist_tree_path.exists():
            zf.write(partlist_tree_path, arcname=f"partlist_tree_{module_name}.txt")

    # Optionally, remove any old archive folders for this module (cleanup)
    # for folder in archive_dir.glob(f"{module_name}_*"):
    #     if folder.is_dir():
    #         shutil.rmtree(folder, ignore_errors=True)

    return None, zip_path

def create_partlist_excel_from_template(
    partlist_csv_path: Path,
    template_xlsx_path: Path,
    output_xlsx_path: Path,
    first_rows_to_copy: int = 7
):
    """
    Generate an Excel file from partlist.csv using the first 7 rows of the template.
    Maps columns: stulinr, posnr, menge, artnr, artbez1.
    """
    import openpyxl
    from openpyxl.utils import get_column_letter

    wb = openpyxl.load_workbook(template_xlsx_path)
    ws_template = wb.active
    ws_out = wb.copy_worksheet(ws_template)
    ws_out.title = "Stückliste"

    # Remove all other sheets except the output
    for sheet in wb.sheetnames:
        if sheet != ws_out.title:
            std = wb[sheet]
            wb.remove(std)

    # Copy first N rows from template (including formatting)
    for r in range(1, first_rows_to_copy + 1):
        for c in range(1, ws_template.max_column + 1):
            ws_out.cell(row=r, column=c).value = ws_template.cell(row=r, column=c).value
            ws_out.cell(row=r, column=c)._style = ws_template.cell(row=r, column=c)._style

    # Read partlist.csv
    with open(partlist_csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=';')
        part_rows = list(reader)

    # Find where to start writing data (after template rows)
    start_row = first_rows_to_copy + 1

    # Map CSV columns to Excel columns (assume order: stulinr, posnr, menge, artnr, artbez1)
    for idx, row in enumerate(part_rows):
        ws_out.cell(row=start_row + idx, column=1).value = row.get('stulinr', '')
        ws_out.cell(row=start_row + idx, column=2).value = row.get('posnr', '')
        ws_out.cell(row=start_row + idx, column=3).value = row.get('menge', '')
        ws_out.cell(row=start_row + idx, column=4).value = row.get('artnr', '')
        ws_out.cell(row=start_row + idx, column=5).value = row.get('artbez1', '')

    wb.save(output_xlsx_path)
    return output_xlsx_path
