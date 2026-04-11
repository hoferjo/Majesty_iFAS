
import csv
from datetime import datetime
from pathlib import Path
import yaml
BASE_DIR = Path(__file__).parent.parent
etl_dir = BASE_DIR / "etl"

# Debug flag for easy log removal
DEBUG = True
# Separate flag for timer output
TIMER = True

# Shared in-process caches survive across endpoint calls in the same worker.
_GLOBAL_TABLE_CACHE = {}
_GLOBAL_MAPPING_CACHE = {}


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
artikelstamm = BASE_DIR / raw_dir / "artikelstamm" / artikelstamm_file
waren_artikelgruppe = BASE_DIR / settings["paths"]["waren_artikelgruppe_dir"] / settings["files"]["waren_artikelgruppe"]
lieferanten_mapping = BASE_DIR / settings["paths"]["lieferanten_mapping_dir"] / settings["files"]["lieferanten_mapping"]
if not lieferanten_mapping.exists():
    fallback_lieferanten_mapping = BASE_DIR / "config" / "lieferanten_mapping.csv"
    if fallback_lieferanten_mapping.exists():
        print(f"[WARN] Configured supplier mapping not found: {lieferanten_mapping}. Using fallback: {fallback_lieferanten_mapping}")
        lieferanten_mapping = fallback_lieferanten_mapping
stueckliste_path = BASE_DIR / settings["paths"]["stueckliste_dir"] / settings["files"]["stueckliste"]
existing_articles_path = BASE_DIR / settings["paths"]["existing_articles_dir"] / settings["files"]["existing_articles"]        

def check_utf8_file(filepath):
    """
    Checks if a file is valid UTF-8. Returns True if valid, else prints an error and returns False.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for _ in f:
                pass
        return True
    except UnicodeDecodeError as e:
        print(f"[ERROR] File '{filepath}' is not valid UTF-8: {e}")
        return False
    
def is_existing_article(artnr, existing_articles_path=None):
    """
    Returns True if artnr is found in existingArticlesIFAS.csv, else False.
    """
    if not existing_articles_path:
        return False
    try:
        with open(existing_articles_path, 'r', encoding='utf-8') as f:
            next(f)  # skip header
            for line in f:
                if line.strip().split(',')[0] == artnr:
                    return True
    except FileNotFoundError:
        return False
    return False

def getEntryFromCSV(filename, rowname, columnname):
    with open(filename, mode='r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
#        print(f"CSV headers: {reader.fieldnames}") #debugging line to check headers
        found = False
        for row in reader:
#            print(f"Row: {row}") #debugging line to check row content
            if row.get('artnr') == rowname:
#                print(f"Match found for artnr={rowname}: {row}") # shows the row that matches the artnr
                found = True
                return row.get(columnname, f"Column '{columnname}' not found")
        if not found:
            print(f"No match found for artnr={rowname}")
    return 0

def addColumnToCSV(filename, columname, defaultvalue):
    with open(filename, mode='r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        fieldnames = reader.fieldnames
        if columname in fieldnames:
#            print(f"Column '{columname}' already exists in {filename}. No changes made.")
            return
        fieldnames.append(columname)
        rows = list(reader)


def mergeTexts(text1, text2, text3=None, text4=None):
    if text1 and text2 and text3 and text4:
        return f"{text1}, {text2}, {text3}, {text4}"
    elif text1 and text2 and text3:
        return f"{text1}, {text2}, {text3}"
    elif text1 and text2:
        return f"{text1}, {text2}"
    elif text1:
        return text1
    elif text2:
        return text2
    else:
        return ''

def getLieferantennummer(artnr):
    letzt_lief = getEntryFromCSV(artikelstamm, artnr, 'letzt_lief')
    # Use as string, no padding
    if letzt_lief is not None:
        letzt_lief = str(letzt_lief).strip()
    return getEntryFromCSV(lieferanten_mapping, letzt_lief, 'ifas_nummer')

def getBeschaffungsart(artnr):
    if isParent(artnr, stueckliste_path):
        return '1'  # Replace 'SomeValue' with the actual value you want to return
    return '6'  # Replace 'OtherValue' with the actual value you want to return

def getKontierungsgruppe(artnr):    
    letzt_lief = getEntryFromCSV(artikelstamm, artnr, 'letzt_lief')
    if letzt_lief == '92005':
        return 'Material Gruppe'
    return 'Material'

def getBezeichnung2(artnr):
    artbez2 = getEntryFromCSV(artikelstamm, artnr, 'artbez2')
    artbez3 = getEntryFromCSV(artikelstamm, artnr, 'artbez3')
    artbezmem= getEntryFromCSV(artikelstamm, artnr, 'artbezmem')
    return mergeTexts(artbez2, artbez3, artbezmem)


def API_import(first_parent_artnr=None):
    import_date = "Import_via_API_" + datetime.now().strftime("%Y-%m-%d")
    if first_parent_artnr:
        return f"{import_date}{first_parent_artnr}"
    return import_date

def getLieferantennummer(artnr):
    letzt_lief = getEntryFromCSV(artikelstamm, artnr, 'letzt_lief')
    return getEntryFromCSV(lieferanten_mapping, letzt_lief, 'ifas_nummer')


def deriveWBZ(artnr):
    letzt_lief = getEntryFromCSV(artikelstamm, artnr, 'letzt_lief')
    wbz = getEntryFromCSV(lieferanten_mapping, letzt_lief, 'wbz')
    if wbz and wbz !='0' and wbz != 0:
        return wbz
    else:
        return '0'
    
def mapping_Bedingung_2o(Bedingung, outputIfTrue, outputElse, filename, artnr, columnname):
    status = getEntryFromCSV(filename, artnr, columnname)
    # Treat None, '', and whitespace as empty
    status_clean = (status or '').strip()
    bedingung_clean = (Bedingung or '').strip()
    if bedingung_clean == '' and status_clean == '':
        return outputIfTrue
    if status_clean == bedingung_clean:
        return outputIfTrue
    return outputElse
    
def isParent(artnr, stueckliste_path):
    try:
        if not check_utf8_file(stueckliste_path):
            print(f"[ERROR] Skipping isParent check for {artnr} due to stueckliste encoding.")
            return False
        with open(stueckliste_path, mode='r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:
                if row.get('stulinr', '').strip() == artnr:
                    return True
    except Exception as e:
        print(f"Error in isParent: {e}")
    return False
    

def getGroup(filename, artnr, columnname):
    zeichnr = getEntryFromCSV(artikelstamm, artnr, 'zeichnr')
    code = ''
    code2 = ''
    zeichnr = str(zeichnr or '').strip()
    # Special handling: if zeichnr is empty
    if not zeichnr:
        if columnname in ('Warengruppe', 'Kürzel'):
            return 'ALLG'
        if columnname == 'Artikelgruppe 1':
            return ''
        return ''
    parts = [part for part in zeichnr.split() if part]
    if parts:
        code = parts[0]
        if len(parts) >= 2:
            code2 = f"{parts[0]} {parts[1]}"
    elif len(zeichnr) >= 3:
        compact = zeichnr.replace(' ', '')
        code = compact[:3]
        if len(compact) >= 6:
            code2 = f"{compact[:3]} {compact[3:6]}"

    lookup_value = code2 if columnname == 'Artikelgruppe 2' else code
    if not lookup_value:
        return ''

    with open(filename, mode='r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            if (row.get('Zeichnr') or '').strip() == lookup_value:
                val = row.get(columnname, '')
                # If the lookup result is empty, return empty string
                if not val or str(val).strip() == '':
                    return ''
                return val
    return ''


def IstNichtAllgemein(artnr):
    warengruppe = getGroup(waren_artikelgruppe, artnr, 'Kürzel')
    if warengruppe in ('ALLG', 'Allgemein'):
        return '0'
    else:
        return '1'
    

def IstNichtAllgemeinNormteile(artnr):
    warengruppe = getGroup(waren_artikelgruppe, artnr, 'Kürzel')
    artikelgruppe1 = getGroup(waren_artikelgruppe, artnr, 'Artikelgruppe 1')
    if warengruppe in ('ALLG', 'Allgemein') and artikelgruppe1 in ('001 | Normteile Jost', '001', 'Normteile'):
        return '0'
    else:
        return '1'

    
def build_sheet_cache_CSV(articlelist, active_sheets, articles=None, table_cache=None, mapping_cache=None):

    import os
    
    table_cache = table_cache if table_cache is not None else _GLOBAL_TABLE_CACHE
    mapping_cache = mapping_cache if mapping_cache is not None else _GLOBAL_MAPPING_CACHE

    def _load_table_by_column(filename, key_column):
        """Load CSV file and index by specified key column."""
        cache_key = (str(filename), key_column)
        if cache_key in table_cache:
            return table_cache[cache_key]

        rows_by_key = {}
        try:
            with open(filename, mode='r', encoding='utf-8-sig') as csvfile:
                # Detect delimiter: check if file is lieferanten_mapping (comma) or others (semicolon)
                delimiter = ';'
                if 'lieferanten' in str(filename).lower():
                    delimiter = ','
                
                reader = csv.DictReader(csvfile, delimiter=delimiter)
                for row in reader:
                    key_val = (row.get(key_column) or '').strip()
                    if key_val:
                        rows_by_key[key_val] = row
                
                if DEBUG and 'lieferanten' in str(filename).lower():
                    print(f"[DEBUG] _load_table_by_column: loaded {len(rows_by_key)} rows from {filename} using delimiter={delimiter}, key_column={key_column}")
                    sample_keys = list(rows_by_key.keys())[:5]
                    print(f"[DEBUG] Sample keys: {sample_keys}")
        except FileNotFoundError:
            rows_by_key = {}

        table_cache[cache_key] = rows_by_key
        return rows_by_key

    def get_entry_cached(filename, rowname, columnname, key_column='artnr'):
        """Lookup a value in a CSV file, indexed by key_column."""
        rows_by_key = _load_table_by_column(filename, key_column)
        row = rows_by_key.get(str(rowname))
        if not row:
            return 0
        return row.get(columnname, '')

    def get_group_cached(artnr, columnname):
        zeichnr = get_entry_cached(artikelstamm, artnr, 'zeichnr', key_column='artnr')
        zeichnr = str(zeichnr or '').strip()
        # Special handling: if zeichnr is empty
        if not zeichnr:
            if columnname in ('Warengruppe', 'Kürzel'):
                return 'ALLG'
            if columnname == 'Artikelgruppe 1':
                return ''  # No longer map to Normteile
            return ''
        code = ''
        code2 = ''
        parts = [part for part in zeichnr.split() if part]
        if parts:
            code = parts[0]
            if len(parts) >= 2:
                code2 = f"{parts[0]} {parts[1]}"
        else:
            compact = zeichnr.replace(' ', '')
            if len(compact) >= 3:
                code = compact[:3]
                if len(compact) >= 6:
                    code2 = f"{compact[:3]} {compact[3:6]}"

        # If code is still empty after parsing, treat as unmappable
        if not code:
            if columnname in ('Warengruppe', 'Kürzel'):
                return 'ALLG'
            if columnname == 'Artikelgruppe 1':
                return ''
            return ''

        # Lookup and ensure empty field in lookup returns empty string
        if columnname == 'Artikelgruppe 2':
            val = get_entry_cached(waren_artikelgruppe, code2, columnname, key_column='Zeichnr')
            if val and str(val).strip() != '':
                return val
            # fallback if lookup fails
            return 'ALLG' if columnname in ('Warengruppe', 'Kürzel') else ''
        val = get_entry_cached(waren_artikelgruppe, code, columnname, key_column='Zeichnr')
        if val and str(val).strip() != '':
            return val
        # fallback if lookup fails
        return 'ALLG' if columnname in ('Warengruppe', 'Kürzel') else ''

    def ist_nicht_allgemein_normteile_cached(artnr):
        warengruppe = get_group_cached(artnr, 'Kürzel')
        artikelgruppe1 = get_group_cached(artnr, 'Artikelgruppe 1')
        if warengruppe in ('ALLG', 'Allgemein') and artikelgruppe1 in ('001 | Normteile Jost', '001', 'Normteile'):
            return '0'
        return '1'

    def derive_wbz_cached(artnr):
        letzt_lief = get_entry_cached(artikelstamm, artnr, 'letzt_lief', key_column='artnr')
        if DEBUG:
            print(f"[DEBUG] derive_wbz_cached: artnr={artnr}, letzt_lief={letzt_lief}")
        wbz = get_entry_cached(lieferanten_mapping, letzt_lief, 'wbz', key_column='liefnr')
        if DEBUG:
            print(f"[DEBUG] derive_wbz_cached: wbz lookup result={wbz}")
        if wbz and wbz != '0' and wbz != 0:
            return wbz
        return '0'

    def mapping_bedingung_2o_cached(bedingung, output_if_true, output_else, filename, artnr, columnname):
        status = get_entry_cached(filename, artnr, columnname)
        status_clean = (status or '').strip()
        bedingung_clean = (bedingung or '').strip()
        if DEBUG and columnname == 'sperre':
            print(f"[DEBUG] mapping_bedingung_2o_cached: artnr={artnr}, filename={filename}, column={columnname}, status={status!r}, status_clean={status_clean!r}, bedingung={bedingung!r}, bedingung_clean={bedingung_clean!r}")
        if bedingung_clean == '' and status_clean == '':
            return output_if_true
        if status_clean == bedingung_clean:
            return output_if_true
        return output_else

    def _resolve_filename_token(token):
        return globals().get(token, token)

    def parse_mapping_csv(csv_path):
        mappings = []

        def _normalize_function_name(name):
            normalized = str(name or '').strip()
            aliases = {
                'derive_WBZ': 'deriveWBZ',
                'derive_wbz': 'deriveWBZ',
                'defaultValue': 'defaultvalue',
            }
            return aliases.get(normalized, normalized)

        csv_path_obj = Path(csv_path)
        cache_key = (str(csv_path_obj.resolve()), csv_path_obj.stat().st_mtime)
        if cache_key in mapping_cache:
            return mapping_cache[cache_key]

        with open(csv_path_obj, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                header = (row.get('columnname') or '').strip()
                if not header:
                    continue

                # Support legacy typo key "funtion" used in some mapping plans.
                raw_func = row.get('function')
                if raw_func is None:
                    raw_func = row.get('funtion')
                func = _normalize_function_name(raw_func)

                argument = (row.get('arguments') or '').strip()
                arglist = [a.strip().strip("'") for a in argument.split(',') if a and a.strip()]
                mappings.append({
                    'header': header,
                    'function': func,
                    'argument': argument,
                    'arglist': arglist,
                })
        if DEBUG:
            print(f"[DEBUG] Parsed {len(mappings)} mappings from {csv_path}")
        mapping_cache[cache_key] = mappings
        return mappings

    parent_articles = set(_load_table_by_column(stueckliste_path, 'stulinr').keys())

    def get_beschaffungsart_cached(artnr):
        return '1' if str(artnr or '').strip() in parent_articles else '6'

    def get_kontierungsgruppe_cached(artnr):
        letzt_lief = get_entry_cached(artikelstamm, artnr, 'letzt_lief', key_column='artnr')
        return 'Material Gruppe' if letzt_lief == '92005' else 'Material'

    # Function dispatcher for mapping functions
    def call_mapping_function(mapping, article, articlelist_headers=None):
        header = mapping['header']
        # If this article is a textartikel (from replacement), override certain fields
        textartikel_map = getattr(process_module_structure, '_textartikel_map', {})
        artnr_key = article.get('artnr', '').strip()
        if artnr_key in textartikel_map:
            override = textartikel_map[artnr_key]
            # Map header to override value if present
            if header in override:
                return override[header]
        func = mapping['function']
        args = mapping['argument']
        arglist = mapping['arglist']
        func = (func or '').strip()
        args = (args or '').strip()

        # Direct from articlelist if no function/args and column exists
        if (not func and not args) or (func == '' and args == ''):
            if articlelist_headers and header in articlelist_headers:
                return article.get(header, '')
            return ''

        if func == '' and args == 'artnr':
            return article.get('artnr', '')
        if func == 'defaultvalue':
            return args

        if func == 'getEntryFromCSV':
            # args: filename, artnr, columnname
            if len(arglist) == 3:
                filename = _resolve_filename_token(arglist[0])
                artnr_val = article.get(arglist[1], arglist[1])
                columnname = arglist[2]
                return get_entry_cached(filename, artnr_val, columnname)
            return ''

        if func == 'getBezeichnung2':
            # args: artnr
            if len(arglist) >= 1:
                artnr_val = article.get(arglist[0], arglist[0])
                artbez2 = get_entry_cached(artikelstamm, artnr_val, 'artbez2', key_column='artnr')
                artbez3 = get_entry_cached(artikelstamm, artnr_val, 'artbez3', key_column='artnr')
                artbezmem = get_entry_cached(artikelstamm, artnr_val, 'artbezmem', key_column='artnr')
                return mergeTexts(artbez2, artbez3, artbezmem)
            return ''

        if func == 'getLieferantennummer':
            # args: artnr
            if len(arglist) >= 1:
                artnr_val = article.get(arglist[-1], arglist[-1])
                letzt_lief = get_entry_cached(artikelstamm, artnr_val, 'letzt_lief', key_column='artnr')
                if letzt_lief is not None:
                    letzt_lief = str(letzt_lief).strip()
                if not letzt_lief or letzt_lief == 0:
                    return ''
                val = get_entry_cached(lieferanten_mapping, letzt_lief, 'ifas_nummer', key_column='liefnr')
                return '' if not val or val == 0 else val
            return ''

        if func == 'getBeschaffungsart':
            # args can be "artnr" or ",artnr"
            if len(arglist) >= 1:
                return get_beschaffungsart_cached(article.get(arglist[-1], arglist[-1]))
            return ''

        if func == 'getKontierungsgruppe':
            if len(arglist) >= 1:
                return get_kontierungsgruppe_cached(article.get(arglist[-1], arglist[-1]))
            return ''

        if func == 'getGroup':
            # args: filename, artnr, columnname
            if len(arglist) == 3:
                artnr_val = article.get(arglist[1], arglist[1])
                columnname = arglist[2]
                return get_group_cached(artnr_val, columnname)
            return ''

        if func == 'mapping_Bedingung_2o':
            # args: Bedingung, outputIfTrue, outputElse, filename, artnr, columnname
            if len(arglist) >= 6:
                resolved_filename = _resolve_filename_token(arglist[3])
                target_artnr = article.get(arglist[4], arglist[4])
                return mapping_bedingung_2o_cached(arglist[0], arglist[1], arglist[2], resolved_filename, target_artnr, arglist[5])
            return ''

        if func == 'IstNichtAllgemein':
            # args: artnr
            if len(arglist) >= 1:
                warengruppe = get_group_cached(article.get(arglist[0], arglist[0]), 'Kürzel')
                header = mapping['header'].lower()
                if header == "lagerbewertungsverfahren":
                    return '2' if warengruppe in ('ALLG', 'Allgemein') else '1'
                if header == "inventurart":
                    return '' if warengruppe in ('ALLG', 'Allgemein') else '1'
                return '0' if warengruppe in ('ALLG', 'Allgemein') else '1'
            return ''

        if func == 'IstNichtAllgemeinNormteile':
            # args: artnr
            if len(arglist) >= 1:
                return ist_nicht_allgemein_normteile_cached(article.get(arglist[0], arglist[0]))
            return ''

        if func == 'API_import':
            # For Freier Text 10, append the uppermost parent (root module artnr).
            header = mapping['header'].lower()
            root_module_artnr = None
            if header == 'freier text 10':
                root_module_artnr = article.get('root_module_artnr')
            return API_import(root_module_artnr)

        if func == 'deriveWBZ':
            # args: artnr
            if len(arglist) >= 1:
                return derive_wbz_cached(article.get(arglist[0], arglist[0]))
            return ''

        # Add more function handlers as needed
        return ''

    # Reuse provided in-memory article rows when available.
    if articles is None:
        with open(articlelist, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            articles = list(reader)
            articlelist_headers = set(reader.fieldnames or [])
    else:
        articlelist_headers = set(articles[0].keys()) if articles else set()

    # Try to determine the root module artnr (uppermost parent) from the first article or from filename.
    root_module_artnr = None
    if articles and 'stulinr' in articles[0]:
        root_module_artnr = articles[0]['stulinr']
    elif articles and 'root_module_artnr' in articles[0]:
        root_module_artnr = articles[0]['root_module_artnr']
    elif articles and 'artnr' in articles[0]:
        root_module_artnr = articles[0]['artnr']
    if not root_module_artnr and isinstance(articlelist, str):
        import re
        m = re.search(r'article_list_([\w\d]+)\\.csv', articlelist)
        if m:
            root_module_artnr = m.group(1)

    # Inject root_module_artnr into every article row for mapping use.
    if root_module_artnr:
        for a in articles:
            a['root_module_artnr'] = root_module_artnr

    # Determine if this is for blocked articles by filename
    is_blocked = False
    if isinstance(articlelist, str) and articlelist.endswith('blocked_articles.csv'):
        is_blocked = True

    for sheet in active_sheets:
        mapping_csv = os.path.join('config', f'mapping_plan_{sheet}.csv')
        if is_blocked:
            output_csv = os.path.join('data', 'processed', 'csv', 'cache', 'sheets', f'{sheet}_cache_blocked.csv')
        else:
            output_csv = os.path.join('data', 'processed', 'csv', 'cache', 'sheets', f'{sheet}_cache.csv')
        mappings = parse_mapping_csv(mapping_csv)

        if DEBUG:
            print(f"[DEBUG] Processing sheet: {sheet}, articles: {len(articles)}, output: {output_csv}")

        # Prepare output CSV
        fieldnames = [m['header'] for m in mappings]
        with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            for idx, article in enumerate(articles):
                row = {}
                for m in mappings:
                    row[m['header']] = call_mapping_function(m, article, articlelist_headers=articlelist_headers)
                writer.writerow(row)


def process_module_structure(
    selected_artnr,
    artikelstamm_path,
    stueckliste_path,
    article_list_path,
    partlist_path,
    visited=None,
    artikel_map=None,
    existing_articles_file=None,
    replacement_map=None,
    reset_files=False,
):

    import time
    step_start = time.time()
    """
    For a given selected_artnr, find all Stückliste entries where stulinr == selected_artnr.
    Write each found entry's artnr, artbez1, zeichnr to article_list.csv (if not already present).
    Write stulinr, posnr, menge, artnr, artbez1 to partlist.csv.
    If the artnr of a position is itself a parent, recurse.
    """
    # Check UTF-8 validity for input files
    if not check_utf8_file(artikelstamm_path):
        print(f"[ERROR] Skipping processing for {selected_artnr} due to artikelstamm encoding.")
        return
    if not check_utf8_file(stueckliste_path):
        print(f"[ERROR] Skipping processing for {selected_artnr} due to stueckliste encoding.")
        return

    # Always ensure visited is a set
    if visited is None:
        visited = set()
    # Overwrite article_list, partlist, and blocked_articles only if reset_files is True
    if reset_files:
        with open(article_list_path, 'w', encoding='utf-8') as f:
            f.write('artnr;artbez1;zeichnr\n')
        with open(partlist_path, 'w', encoding='utf-8') as f:
            f.write('stulinr;posnr;menge;artnr;artbez1\n')
        blocked_articles_path = str(article_list_path).replace('article_list', 'blocked_articles')
        # Always clear the blocked articles file (write header), even if there are no blocked articles in the new run
        with open(blocked_articles_path, 'w', encoding='utf-8') as f:
            f.write('artnr;artbez1;zeichnr\n')

    # Keep seen article numbers in memory to avoid scanning article_list.csv repeatedly.
    existing_articles_set = set()
    if existing_articles_file:
        try:
            with open(existing_articles_file, 'r', encoding='utf-8') as f:
                next(f, None)
                for line in f:
                    key = line.strip().split(',')[0].strip()
                    if key:
                        existing_articles_set.add(key)
        except FileNotFoundError:
            pass

    article_list_seen = set(existing_articles_set)
    replacement_map = replacement_map or {}

    # Only load artikel_map once and pass through recursion
    if artikel_map is None:
        artikel_map = {}
        with open(artikelstamm_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                artikel_map[row.get('artnr', '').strip()] = row
        if DEBUG:
            print(f"[DEBUG] Loaded {len(artikel_map)} artikelstamm entries.")

    # Only load stueckliste rows and parent->children map once and pass through recursion
    if not hasattr(process_module_structure, "stueckliste_rows") or visited is None:
        with open(stueckliste_path, encoding='utf-8-sig') as f:
            # Skip all leading empty lines to find the real header
            lines = []
            for line in f:
                if line.strip() == '':
                    continue
                lines.append(line)
                if len(lines) == 1:
                    break
            lines += f.readlines()
            reader = csv.DictReader(lines, delimiter=';')
            process_module_structure.stueckliste_rows = list(reader)
            children_map = {}
            for row in process_module_structure.stueckliste_rows:
                parent_key = row.get('stulinr', '').strip()
                if parent_key:
                    children_map.setdefault(parent_key, []).append(row)
            process_module_structure.stueckliste_children_map = children_map
        if DEBUG:
            print(f"[DEBUG] Loaded {len(process_module_structure.stueckliste_rows)} stueckliste rows.")
    stueckliste_rows = process_module_structure.stueckliste_rows
    stueckliste_children_map = getattr(process_module_structure, 'stueckliste_children_map', {})

    blocked_articles_path = str(article_list_path).replace('article_list', 'blocked_articles')

    def append_unique_article(artnr, artbez1, zeichnr):
        if DEBUG:
            print(f"[DEBUG] append_unique_article called with: artnr={artnr}, artbez1={artbez1}, zeichnr={zeichnr}")
        artnr_key = str(artnr or '').strip()
        repl_val = replacement_map.get(artnr_key, artnr_key)
        # Handle textartikel special case
        is_textartikel = False
        if isinstance(repl_val, dict) and repl_val.get("textartikel"):
            is_textartikel = True
            effective_artnr = artnr_key
        else:
            effective_artnr = str(repl_val or '').strip()
        if not artnr_key:
            return
        if effective_artnr in article_list_seen:
            if DEBUG:
                if existing_articles_file:
                    print(f"[DEBUG] Article {effective_artnr} already in existing articles file ({existing_articles_file}), skipping.")
                else:
                    print(f"[DEBUG] Article {effective_artnr} already in current article list set, skipping.")
            return
        try:
            effective_row = artikel_map.get(effective_artnr, {})
            effective_artbez1 = effective_row.get('artbez1', '') or artbez1
            effective_zeichnr = effective_row.get('zeichnr', '') or zeichnr
            # Check if blocked, unless textartikel override
            sperre = (effective_row.get('sperre', '') or '').strip()
            if sperre and sperre.upper() != 'FALSCH' and not is_textartikel:
                with open(blocked_articles_path, 'a', encoding='utf-8') as f:
                    f.write(f"{effective_artnr};{effective_artbez1};{effective_zeichnr}\n")
                if DEBUG:
                    print(f"[DEBUG] Blocked article: {effective_artnr}; {effective_artbez1}; {effective_zeichnr}")
                return
            with open(article_list_path, 'a', encoding='utf-8') as f:
                f.write(f"{effective_artnr};{effective_artbez1};{effective_zeichnr}\n")
            article_list_seen.add(effective_artnr)
            if DEBUG:
                print(f"[DEBUG] Appended article: {effective_artnr}; {effective_artbez1}; {effective_zeichnr}")
            # If textartikel, set mapping fields for later use
            if is_textartikel:
                if not hasattr(process_module_structure, '_textartikel_map'):
                    process_module_structure._textartikel_map = {}
                process_module_structure._textartikel_map[effective_artnr] = {
                    'istTextartikel': '1',
                    'produktionsartikel': '1',
                    'einkaufsartikel': '0',
                    'verkaufsartikel': '1',
                }
        except Exception as e:
            print(f"[ERROR] Failed to append article: {e}")


    # --- Tree output ---
    # Only open the tree file once at the top-level call
    tree_file_path = partlist_path.replace('.csv', '_tree.txt')
    if not hasattr(process_module_structure, '_tree_file') or visited is None or getattr(process_module_structure, '_tree_file', None) is None:
        setattr(process_module_structure, '_tree_file', open(tree_file_path, 'w', encoding='utf-8'))

    def append_partlist(stulinr, posnr, menge, artnr, artbez1, depth=0, is_last=False, prefix_stack=None, timer_start=None):
        t_stueck_start = time.time()
        artnr_key = str(artnr or '').strip()
        effective_artnr = str(replacement_map.get(artnr_key, artnr_key) or '').strip()
        effective_row = artikel_map.get(effective_artnr, {})
        effective_artbez1 = effective_row.get('artbez1', '') or artbez1
        # Check if blocked
        sperre = (effective_row.get('sperre', '') or '').strip()
        menge_out = menge
        if sperre and sperre.upper() != 'FALSCH':
            menge_out = f"{menge}BLOCKED"
        with open(partlist_path, 'a', encoding='utf-8') as f:
            f.write(f"{stulinr};{posnr};{menge_out};{effective_artnr};{effective_artbez1}\n")
        if DEBUG:
            print(f"[DEBUG] Appended partlist: {stulinr}; {posnr}; {menge_out}; {effective_artnr}; {effective_artbez1}")
        # Write to tree file
        if prefix_stack is None:
            prefix_stack = []
        prefix = ''
        for is_last_parent in prefix_stack[:-1]:
            prefix += '    ' if is_last_parent else '¦   '
        if depth > 0:
            prefix += '+---'
        # Get zeichnr for this artnr
        zeichnr = effective_row.get('zeichnr', '')
        if sperre and sperre.upper() != 'FALSCH':
            line = f"{prefix}BLOCKED {effective_artnr}, {effective_artbez1}, {zeichnr}"
        else:
            line = f"{prefix}{effective_artnr}, {effective_artbez1}, {zeichnr}"
        getattr(process_module_structure, '_tree_file').write(line + '\n')
        t_stueck_end = time.time()
        if TIMER:
            print(f"[TIMER] Stückliste processing: {t_stueck_end - t_stueck_start:.3f}s for {stulinr}")
        if timer_start is not None and TIMER:
            print(f"[TIMER] Total time for {stulinr}: {t_stueck_end - timer_start:.3f}s")

    # Helper to find children for a given parent
    def get_children(parent_artnr):
        return stueckliste_children_map.get(parent_artnr, [])

    def recurse_tree(current_artnr, depth=0, prefix_stack=None, timer_start=None):
        if prefix_stack is None:
            prefix_stack = []
        children = get_children(current_artnr)
        for idx, row in enumerate(children):
            artnr = row.get('artnr', '').strip()
            artbez1 = artikel_map.get(artnr, {}).get('artbez1', '')
            is_last = (idx == len(children) - 1)
            append_partlist(current_artnr, row.get('posnr', '').strip(), row.get('menge', '').strip(), artnr, artbez1, depth+1, is_last, prefix_stack + [is_last], timer_start)
            if artnr not in visited:
                visited.add(artnr)
                recurse_tree(artnr, depth+1, prefix_stack + [is_last], timer_start)

    # Write the root node and start tree recursion
    header_row = artikel_map.get(selected_artnr, {})
    header_artbez1 = header_row.get('artbez1', '')
    header_zeichnr = header_row.get('zeichnr', '')
    # Write root to tree
    if not hasattr(process_module_structure, '_tree_file') or visited is None or getattr(process_module_structure, '_tree_file', None) is None or getattr(process_module_structure, '_tree_file').tell() == 0:
        getattr(process_module_structure, '_tree_file').write(f"{selected_artnr}, {header_artbez1}, {header_zeichnr}\n")

    def recurse_all_articles(current_artnr, depth=0, prefix_stack=None, timer_start=None):
        # Add current article to article_list
        artbez1 = artikel_map.get(current_artnr, {}).get('artbez1', '')
        zeichnr = artikel_map.get(current_artnr, {}).get('zeichnr', '')
        append_unique_article(current_artnr, artbez1, zeichnr)
        # Tree output and partlist already handled in append_partlist
        children = get_children(current_artnr)
        for idx, row in enumerate(children):
            artnr = row.get('artnr', '').strip()
            posnr = row.get('posnr', '').strip()
            menge = row.get('menge', '').strip()
            artbez1_child = artikel_map.get(artnr, {}).get('artbez1', '')
            is_last = (idx == len(children) - 1)
            append_partlist(current_artnr, posnr, menge, artnr, artbez1_child, depth+1, is_last, prefix_stack + [is_last] if prefix_stack else [is_last], timer_start)
            if artnr not in visited:
                visited.add(artnr)
                recurse_all_articles(artnr, depth+1, (prefix_stack + [is_last]) if prefix_stack else [is_last], timer_start)

    if selected_artnr not in visited:
        visited.add(selected_artnr)
        if DEBUG:
            print(f"[DEBUG] Processing module structure for: {selected_artnr}")
        timer_start = time.time()
        recurse_all_articles(selected_artnr, 0, [], timer_start)
    # Close tree file if top-level
    if visited is not None and hasattr(process_module_structure, '_tree_file') and getattr(process_module_structure, '_tree_file', None):
        getattr(process_module_structure, '_tree_file').close()
        setattr(process_module_structure, '_tree_file', None)

    # After processing, generate sheet data if needed
    # Example: build_sheet_cache_CSV(article_list_path, ["Artikelstamm"])
    # Uncomment and adjust the following line as needed for your sheets:
    # build_sheet_cache_CSV(article_list_path, ["Artikelstamm"])

