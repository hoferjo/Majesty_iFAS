
import csv
from datetime import datetime
from pathlib import Path
import yaml
import os 

BASE_DIR = Path(__file__).parent.parent
etl_dir = BASE_DIR / "etl"

# Debug flag for easy log removal
DEBUG = False
# Separate flag for timer output
TIMER = False

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


def get_path(file: str = None, mode: str = None, base: str = BASE_DIR):
    
    normalized_mode = str(mode or "").strip().lower()
    if normalized_mode.endswith("_mode"):
        normalized_mode = normalized_mode[:-5]

    file_key = file
    folder_key = f"{file}_dir"

    if file == "article list":
        folder_key = "article_list_dir"
        file_key = f"article_list_{normalized_mode}_mode"

    if file == "blocked articles":
        folder_key = "article_list_dir"
        file_key = f"blocked_articles_{normalized_mode}_mode"

    if file == "existing articles":
        if normalized_mode in {"", "none"}:
            return None
        folder_key = "existing_articles_dir"
        file_key = f"existing_articles_{normalized_mode}"

    if file == "partlist":
        folder_key = "partlist_dir"
        file_key = f"partlist_{normalized_mode}_mode"

    if file == "partlisttree":
        folder_key = "partlist_tree_dir"
        file_key = f"partlist_{normalized_mode}_mode_tree"

    if file in {"artikelstamm_import_template", "partlist_import_template"}:
        folder_key = "template_dir"
        file_key = file

    if file_key and folder_key:
        return base / settings["paths"][folder_key] / settings["files"][file_key]

    return os.error(f"Invalid file key: {file}. No matching path configuration found in settings.yaml.")


      

#raw paths

artikelstamm_path = get_path("artikelstamm")
stuecklistenstamm_path = get_path("stuecklistenstamm")
waren_artikelgruppe_path = get_path("waren_artikelgruppe")
lieferanten_mapping_path = get_path("lieferanten_mapping")

#processed paths
cache_dir_path = BASE_DIR / settings["paths"]["cache_dir"]
sheets_path = BASE_DIR / "config" / "sheets.csv"
active_sheets_path = BASE_DIR / "config" / "active_sheets.csv"
sheets_output_dir = BASE_DIR / settings["paths"]["sheets_dir"]

#template paths
template_dir = BASE_DIR / settings["paths"]["template_dir"]
artikelstamm_import_template_path = get_path("artikelstamm_import_template")
partlist_import_template_path = get_path("partlist_import_template")

#output_paths
output_dir = BASE_DIR / settings["paths"]["output_dir"]
artikelstamm_output_path = output_dir / settings["files"]["artikelstamm_output"]
partlist_output_path = output_dir / settings["files"]["partlist_output"]






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
    letzt_lief = getEntryFromCSV(artikelstamm_path, artnr, 'letzt_lief')
    # Use as string, no padding
    if letzt_lief is not None:
        letzt_lief = str(letzt_lief).strip()
    return getEntryFromCSV(lieferanten_mapping_path, letzt_lief, 'ifas_nummer')

def getBeschaffungsart(artnr):
    if isParent(artnr, stuecklistenstamm_path):
        return '1'  # Replace 'SomeValue' with the actual value you want to return
    return '6'  # Replace 'OtherValue' with the actual value you want to return

def getKontierungsgruppe(artnr):    
    letzt_lief = getEntryFromCSV(artikelstamm_path, artnr, 'letzt_lief')
    if letzt_lief == '92005':
        return 'Material Gruppe'
    return 'Material'

def getBezeichnung2(artnr):
    artbez2 = getEntryFromCSV(artikelstamm_path, artnr, 'artbez2')
    artbez3 = getEntryFromCSV(artikelstamm_path, artnr, 'artbez3')
    artbezmem= getEntryFromCSV(artikelstamm_path, artnr, 'artbezmem')
    return mergeTexts(artbez2, artbez3, artbezmem)


def API_import(first_parent_artnr=None):
    import_date = "Import_via_API_" + datetime.now().strftime("%Y-%m-%d")
    if first_parent_artnr:
        return f"{import_date}{first_parent_artnr}"
    return import_date

def getLieferantennummer(artnr):
    letzt_lief = getEntryFromCSV(artikelstamm_path, artnr, 'letzt_lief')
    return getEntryFromCSV(lieferanten_mapping_path, letzt_lief, 'ifas_nummer')


def deriveWBZ(artnr):
    letzt_lief = getEntryFromCSV(artikelstamm_path, artnr, 'letzt_lief')
    wbz = getEntryFromCSV(lieferanten_mapping_path, letzt_lief, 'wbz')
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
    
def isParent(artnr, stuecklistenstamm_path):
    try:
        if not check_utf8_file(stuecklistenstamm_path):
            print(f"[ERROR] Skipping isParent check for {artnr} due to stuecklistenstamm encoding.")
            return False
        with open(stuecklistenstamm_path, mode='r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:
                if row.get('stulinr', '').strip() == artnr:
                    return True
    except Exception as e:
        print(f"Error in isParent: {e}")
    return False
    

def getGroup(filename, artnr, columnname):
    zeichnr = getEntryFromCSV(artikelstamm_path, artnr, 'zeichnr')
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
    warengruppe = getGroup(waren_artikelgruppe_path, artnr, 'Kürzel')
    if warengruppe in ('ALLG', 'Allgemein'):
        return '0'
    else:
        return '1'
    

def IstNichtAllgemeinNormteile(artnr):
    warengruppe = getGroup(waren_artikelgruppe_path, artnr, 'Kürzel')
    artikelgruppe1 = getGroup(waren_artikelgruppe_path, artnr, 'Artikelgruppe 1')
    if warengruppe in ('ALLG', 'Allgemein') and artikelgruppe1 in ('001 | Normteile Jost', '001', 'Normteile'):
        return '0'
    else:
        return '1'

def getCodeFromAbbrevation(abbrevation):
    mapping = load_yaml(BASE_DIR / "config" / "mapping_abbrevations.yaml")
    code = mapping['units'][abbrevation]['code']
    if code:
        return code
    else:
        print(f"Warning: No code found for abbrevation '{abbrevation}' in mapping_abbrevations.yaml")
        return ''


def getMasseinheit(artnr):
    masseinheit = getEntryFromCSV(artikelstamm_path, artnr, 'meinheit')
    if masseinheit and str(masseinheit).strip() != '':
        return getCodeFromAbbrevation(masseinheit)
    return ''

def getNameOrNumber(stulinr,
                    StuLiSheet,
                    version:str = 1,
                    variante: str = "Standard-Variante",
                    auswahlvariante: str = "Standard-Auswahlvariante"):
    if StuLiSheet == "Version":
        return str(stulinr)+"-" + str(version)
    elif StuLiSheet == "Variante":
        return str(stulinr)+"-" + str(version) + "-" + str(variante)
    elif StuLiSheet == "Auswahlvariante":
        return str(stulinr)+"-" + str(version) + "--" + str(auswahlvariante)

def getStuLiOptions(stulinr, StuLiSheet, number: int = 1):
    return getStuLiOptions(stulinr, StuLiSheet, number)

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
        zeichnr = get_entry_cached(artikelstamm_path, artnr, 'zeichnr', key_column='artnr')
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
            val = get_entry_cached(waren_artikelgruppe_path, code2, columnname, key_column='Zeichnr')
            if val and str(val).strip() != '':
                return val
            # fallback if lookup fails
            return 'ALLG' if columnname in ('Warengruppe', 'Kürzel') else ''
        val = get_entry_cached(waren_artikelgruppe_path, code, columnname, key_column='Zeichnr')
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
        letzt_lief = get_entry_cached(artikelstamm_path, artnr, 'letzt_lief', key_column='artnr')
        if DEBUG:
            print(f"[DEBUG] derive_wbz_cached: artnr={artnr}, letzt_lief={letzt_lief}")
        wbz = get_entry_cached(lieferanten_mapping_path, letzt_lief, 'wbz', key_column='liefnr')
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
        # Hardcoded mapping for known path tokens
        path_mapping = {
            'artikelstamm': artikelstamm_path,
            'artikelstamm_path': artikelstamm_path,
            'stuecklistenstamm_path': stuecklistenstamm_path,
            'waren_artikelgruppe_path': waren_artikelgruppe_path,
            'lieferanten_mapping_path': lieferanten_mapping_path,
        }
        return path_mapping.get(token, token)

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

    parent_articles = set(_load_table_by_column(stuecklistenstamm_path, 'stulinr').keys())

    def get_beschaffungsart_cached(artnr):
        return '1' if str(artnr or '').strip() in parent_articles else '6'

    def get_kontierungsgruppe_cached(artnr):
        letzt_lief = get_entry_cached(artikelstamm_path, artnr, 'letzt_lief', key_column='artnr')
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
                artbez2 = get_entry_cached(artikelstamm_path, artnr_val, 'artbez2', key_column='artnr')
                artbez3 = get_entry_cached(artikelstamm_path, artnr_val, 'artbez3', key_column='artnr')
                artbezmem = get_entry_cached(artikelstamm_path, artnr_val, 'artbezmem', key_column='artnr')
                return mergeTexts(artbez2, artbez3, artbezmem)
            return ''

        if func == 'getLieferantennummer':
            # args: artnr
            if len(arglist) >= 1:
                artnr_val = article.get(arglist[-1], arglist[-1])
                letzt_lief = get_entry_cached(artikelstamm_path, artnr_val, 'letzt_lief', key_column='artnr')
                if letzt_lief is not None:
                    letzt_lief = str(letzt_lief).strip()
                if not letzt_lief or letzt_lief == 0:
                    return ''
                val = get_entry_cached(lieferanten_mapping_path, letzt_lief, 'ifas_nummer', key_column='liefnr')
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
        # Map sheet names to their category directories
        sheet_to_category = {
            # Article sheets
            'Artikelstamm': 'Article',
            'Artikel_Disposteuerung': 'Article', 
            'Artikel_Lieferantendaten': 'Article',
            # BOM sheets
            'Stücklisten': 'BOM',
            'Stücklistenvarianten': 'BOM',
            'Stücklistenversionen': 'BOM',
            'Stücklistenverwendung': 'BOM',
            'Stücklstenauswahlvarianten': 'BOM',
            'Stücklstenpositionen': 'BOM',
            # Workplan sheets
            'Arbeitspläne': 'Workplan',
            'Arbeitsplanpositionen': 'Workplan',
            'Arbeitsplanversionen': 'Workplan',
        }
        # Default to Article if not found
        category = sheet_to_category.get(sheet, 'Article')
        mapping_csv = os.path.join('config', 'sheet_mappings', category, f'mapping_plan_{sheet}.csv')
        if is_blocked:
            output_csv = sheets_output_dir / f'{sheet}_cache_blocked.csv'
        else:
            output_csv = sheets_output_dir / f'{sheet}_cache.csv'
        
        # Ensure output directory exists
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        
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
    stuecklistenstamm_path,
    article_list_path,
    partlist_path,
    visited=None,
    artikel_map=None,
    existing_articles_path=None,
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
    article_list_creation_mode_path = get_path("article list", mode="creation")
    # Check UTF-8 validity for input files
    if not check_utf8_file(artikelstamm_path):
        print(f"[ERROR] Skipping processing for {selected_artnr} due to artikelstamm encoding.")
        return
    if not check_utf8_file(stuecklistenstamm_path):
        print(f"[ERROR] Skipping processing for {selected_artnr} due to stuecklistenstamm encoding.")
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

        # Also clear all <sheet>_cache_blocked.csv files for all active sheets
        active_sheets_path = BASE_DIR / "config" / "active_sheets.csv"
        if active_sheets_path.exists():
            import csv
            with open(active_sheets_path, encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=';')
                for row in reader:
                    for sheet in row:
                        sheet = sheet.strip()
                        if sheet:
                            sheet_blocked_path = sheets_output_dir / f"{sheet}_cache_blocked.csv"
                            sheet_blocked_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(sheet_blocked_path, 'w', encoding='utf-8-sig', newline='') as blocked_f:
                                blocked_f.write('artnr;artbez1;zeichnr\n')

    # Keep seen article numbers in memory to avoid scanning article_list.csv repeatedly.
    existing_articles_set = set()
    if existing_articles_path:
        try:
            with open(existing_articles_path, 'r', encoding='utf-8') as f:
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
        # Load Majesty/iFAS articles
        if Path(artikelstamm_path).exists():
            with open(artikelstamm_path, encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    artikel_map[row.get('artnr', '').strip()] = row
        # Load creation cache articles (if any)
        creation_cache_dir = BASE_DIR / "data" / "processed" / "csv" / "cache"
        
        if article_list_creation_mode_path.exists():
            with open(article_list_creation_mode_path, encoding='utf-8-sig') as f:
                next(f, None)
                for line in f:
                    parts = line.strip().split(';')
                    if len(parts) >= 3:
                        artnr_c, artbez1_c, zeichnr_c = parts[:3]
                        if artnr_c and artnr_c not in artikel_map:
                            artikel_map[artnr_c] = {'artnr': artnr_c, 'artbez1': artbez1_c, 'zeichnr': zeichnr_c}
        if DEBUG:
            print(f"[DEBUG] Loaded {len(artikel_map)} artikelstamm + creation cache entries.")

    # Only load stueckliste rows and parent->children map once and pass through recursion
    if not hasattr(process_module_structure, "stueckliste_rows") or visited is None:
        with open(stuecklistenstamm_path, encoding='utf-8-sig') as f:
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
        # Handle Angebotsartikel special case (was textartikel)
        is_angebotsartikel = False
        if isinstance(repl_val, dict) and (repl_val.get("Angebotsartikel") or repl_val.get("angebotsartikel")):
            is_angebotsartikel = True
            effective_artnr = artnr_key
        else:
            effective_artnr = str(repl_val or '').strip()
        if not artnr_key:
            return
        if effective_artnr in article_list_seen:
            if DEBUG:
                if existing_articles_path:
                    print(f"[DEBUG] Article {effective_artnr} already in existing articles file ({existing_articles_path}), skipping.")
                else:
                    print(f"[DEBUG] Article {effective_artnr} already in current article list set, skipping.")
            return
        try:
            effective_row = artikel_map.get(effective_artnr, {})
            effective_artbez1 = effective_row.get('artbez1', '') or artbez1
            effective_zeichnr = effective_row.get('zeichnr', '') or zeichnr
            # Check if blocked, unless Angebotsartikel override
            sperre = (effective_row.get('sperre', '') or '').strip()
            if sperre and sperre.upper() != 'FALSCH' and not is_angebotsartikel:
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
            # If Angebotsartikel, set only the two mapping fields for later use
            if is_angebotsartikel:
                if not hasattr(process_module_structure, '_angebotsartikel_map'):
                    process_module_structure._angebotsartikel_map = {}
                process_module_structure._angebotsartikel_map[effective_artnr] = {
                    'Gerätetoptionsarikel': '1',
                    'Freigabe nur für Angebote/Preisanfragen': '1',
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
        # If article does not exist in Majesty/iFAS or creation cache, create it using template/defaults
        art_row = artikel_map.get(current_artnr, None)
        artbez1 = art_row.get('artbez1', '') if art_row else ''
        zeichnr = art_row.get('zeichnr', '') if art_row else ''
        if not art_row:
            # Try to create the article using template/defaults
            # Import here to avoid circular import
            try:
                from etl.create import ArticleCreator
                config_dir = BASE_DIR / "config"
                creator = ArticleCreator(config_dir)
                # Use the first template as fallback
                tpl_names = creator.list_templates()
                tpl_name = tpl_names[0] if tpl_names else None
                input_data = {"artnr": current_artnr, "artbez1": f"Auto {current_artnr}", "zeichnr": f"Auto {current_artnr}"}
                if tpl_name:
                    article = creator.create_article(tpl_name, input_data)
                    # Save to cache (CSV for compatibility)
                    cache_path = BASE_DIR / "data" / "processed" / "csv" / "cache" / f"{tpl_name}_{current_artnr}.csv"
                    creator.save_article_cache(article, cache_path)
                    # Also append to article_list_creation_mode.csv
                    write_header = not article_list_creation_mode_path.exists() or article_list_creation_mode_path.stat().st_size == 0
                    with open(article_list_creation_mode_path, "a", encoding="utf-8") as f:
                        if write_header:
                            f.write("artnr;artbez1;zeichnr\n")
                        f.write(f"{current_artnr};Auto {current_artnr};Auto {current_artnr}\n")
                    artikel_map[current_artnr] = {'artnr': current_artnr, 'artbez1': f"Auto {current_artnr}", 'zeichnr': f"Auto {current_artnr}"}
                    artbez1 = f"Auto {current_artnr}"
                    zeichnr = f"Auto {current_artnr}"
            except Exception as e:
                print(f"[ERROR] Could not auto-create article {current_artnr}: {e}")
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


def build_bom_sheet_cache(partlist_csv_path, article_list_csv_path=None, base_dir=None):
    """
    Generate BOM sheet data from partlist.csv:
    1. Stücklisten: one row per unique stulinr
    2. Stücklistenversionen: version numbers for each stückliste
    3. Stücklistenpositionen: one row per partlist line
    4. Stücklistenvarianten: variants for each version
    5. Auswahlvarianten: selection variants for each version
    
    Existing entries are not overwritten to support incremental builds.
    """
    if base_dir is None:
        base_dir = BASE_DIR
    
    sheets_output_dir = base_dir / "data" / "processed" / "cache" / "sheets"
    sheets_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load mappings for each BOM sheet
    bom_category = "BOM"
    mappings = {}
    sheet_names = [
        'Stücklisten',
        'Stücklistenversionen',
        'Stücklistenpositionen',
        'Stücklistenvarianten',
        'Stücklstenauswahlvarianten'
    ]
    
    for sheet_name in sheet_names:
        mapping_path = base_dir / "config" / "sheet_mappings" / bom_category / f"mapping_plan_{sheet_name}.csv"
        if mapping_path.exists():
            with open(mapping_path, encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                mappings[sheet_name] = list(reader)
    
    # Load partlist data
    partlist_data = []
    if Path(partlist_csv_path).exists():
        with open(partlist_csv_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            partlist_data = list(reader)
    
    # Load article list for lookups
    article_map = {}
    if article_list_csv_path and Path(article_list_csv_path).exists():
        with open(article_list_csv_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                article_map[row.get('artnr', '').strip()] = row
    
    # --- 1. Build Stücklisten (unique stulinr) ---
    stuecklisten_path = sheets_output_dir / "Stücklisten_cache.csv"
    stuecklisten_set = set()
    if stuecklisten_path.exists():
        with open(stuecklisten_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                stuecklisten_set.add(row.get('Stücklistennummer', '').strip())
    
    # Collect unique stulinr from partlist
    unique_stulinr = set()
    for row in partlist_data:
        stulinr = row.get('stulinr', '').strip()
        if stulinr:
            unique_stulinr.add(stulinr)
    
    # Write new Stücklisten entries
    with open(stuecklisten_path, 'a' if stuecklisten_path.exists() else 'w', encoding='utf-8-sig', newline='') as f:
        if stuecklisten_path.stat().st_size == 0:
            # Write header
            fieldnames = [m['columnname'].strip() for m in (mappings.get('Stücklisten', []))]
            f.write(';'.join(fieldnames) + '\n')
        
        for stulinr in unique_stulinr:
            if stulinr not in stuecklisten_set:
                # Create Stücklisten row based on mapping
                row_data = {}
                for mapping in mappings.get('Stücklisten', []):
                    col = mapping['columnname'].strip()
                    func = (mapping.get('function') or '').strip()
                    arg = (mapping.get('arguments') or '').strip()
                    
                    if col == 'Stücklistennummer':
                        row_data[col] = stulinr
                    elif func == 'defaultvalue':
                        row_data[col] = arg
                    else:
                        row_data[col] = ''
                
                f.write(';'.join(row_data.get(col, '') for col in [m['columnname'].strip() for m in mappings.get('Stücklisten', [])]) + '\n')
                stuecklisten_set.add(stulinr)
    
    # --- 2. Build Stücklistenversionen ---
    stuecklisten_versionen_path = sheets_output_dir / "Stücklistenversionen_cache.csv"
    versionen_set = set()
    if stuecklisten_versionen_path.exists():
        with open(stuecklisten_versionen_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                key = (row.get('Stücklistennummer', '').strip(), row.get('Versionsnummer', '').strip())
                versionen_set.add(key)
    
    # Create version entries (1 per stulinr for now)
    with open(stuecklisten_versionen_path, 'a' if stuecklisten_versionen_path.exists() else 'w', encoding='utf-8-sig', newline='') as f:
        if stuecklisten_versionen_path.stat().st_size == 0:
            fieldnames = [m['columnname'].strip() for m in (mappings.get('Stücklistenversionen', []))]
            f.write(';'.join(fieldnames) + '\n')
        
        for stulinr in unique_stulinr:
            version_num = '1'  # Start with version 1
            if (stulinr, version_num) not in versionen_set:
                row_data = {}
                for mapping in mappings.get('Stücklistenversionen', []):
                    col = mapping['columnname'].strip()
                    func = (mapping.get('function') or '').strip()
                    arg = (mapping.get('arguments') or '').strip()
                    
                    if col == 'Stücklistennummer':
                        row_data[col] = stulinr
                    elif col == 'Versionsnummer':
                        row_data[col] = version_num
                    elif func == 'defaultvalue':
                        row_data[col] = arg
                    else:
                        row_data[col] = ''
                
                f.write(';'.join(row_data.get(col, '') for col in [m['columnname'].strip() for m in mappings.get('Stücklistenversionen', [])]) + '\n')
                versionen_set.add((stulinr, version_num))
    
    # --- 3. Build Stücklistenpositionen ---
    stuecklisten_positionen_path = sheets_output_dir / "Stücklistenpositionen_cache.csv"
    positionen_set = set()
    if stuecklisten_positionen_path.exists():
        with open(stuecklisten_positionen_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                key = (row.get('Stücklistennummer', '').strip(), row.get('Versionsnummer', '').strip())
                positionen_set.add(key)
    
    # For each partlist line, create position entry
    with open(stuecklisten_positionen_path, 'a' if stuecklisten_positionen_path.exists() else 'w', encoding='utf-8-sig', newline='') as f:
        if stuecklisten_positionen_path.stat().st_size == 0:
            fieldnames = [m['columnname'].strip() for m in (mappings.get('Stücklistenpositionen', []))]
            f.write(';'.join(fieldnames) + '\n')
        
        for idx, prow in enumerate(partlist_data):
            stulinr = prow.get('stulinr', '').strip()
            version_num = '1'
            posnr = prow.get('posnr', '').strip()
            menge = prow.get('menge', '').strip()
            artnr = prow.get('artnr', '').strip()
            
            key = (stulinr, version_num, posnr)
            # Only add if not already present (based on stulinr+version, not full key for first run)
            if (stulinr, version_num) not in positionen_set or idx == 0:
                row_data = {}
                for mapping in mappings.get('Stücklistenpositionen', []):
                    col = mapping['columnname'].strip()
                    func = (mapping.get('function') or '').strip()
                    arg = (mapping.get('arguments') or '').strip()
                    
                    if col == 'Stücklistennummer':
                        row_data[col] = stulinr
                    elif col == 'Versionsnummer':
                        row_data[col] = version_num
                    elif col == 'Positionsnummer' or col == 'StuecklistePositionsNr':
                        row_data[col] = posnr
                    elif col == 'Artikelnummer':
                        row_data[col] = artnr
                    elif col == 'Menge':
                        row_data[col] = menge
                    elif func == 'defaultvalue':
                        row_data[col] = arg
                    else:
                        row_data[col] = ''
                
                f.write(';'.join(row_data.get(col, '') for col in [m['columnname'].strip() for m in mappings.get('Stücklistenpositionen', [])]) + '\n')
    
    # --- 4. Build Stücklistenvarianten ---
    stuecklisten_varianten_path = sheets_output_dir / "Stücklistenvarianten_cache.csv"
    varianten_set = set()
    if stuecklisten_varianten_path.exists():
        with open(stuecklisten_varianten_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                key = (row.get('Stücklistennummer', '').strip(), row.get('Versionsnummer', '').strip())
                varianten_set.add(key)
    
    with open(stuecklisten_varianten_path, 'a' if stuecklisten_varianten_path.exists() else 'w', encoding='utf-8-sig', newline='') as f:
        if stuecklisten_varianten_path.stat().st_size == 0:
            fieldnames = [m['columnname'].strip() for m in (mappings.get('Stücklistenvarianten', []))]
            f.write(';'.join(fieldnames) + '\n')
        
        for stulinr in unique_stulinr:
            version_num = '1'
            if (stulinr, version_num) not in varianten_set:
                row_data = {}
                for mapping in mappings.get('Stücklistenvarianten', []):
                    col = mapping['columnname'].strip()
                    func = (mapping.get('function') or '').strip()
                    arg = (mapping.get('arguments') or '').strip()
                    
                    if col == 'Stücklistennummer':
                        row_data[col] = stulinr
                    elif col == 'Versionsnummer':
                        row_data[col] = version_num
                    elif func == 'defaultvalue':
                        row_data[col] = arg
                    elif func == 'date':
                        row_data[col] = datetime.now().strftime('%d.%m.%Y') if arg == 'today' else arg
                    else:
                        row_data[col] = ''
                
                f.write(';'.join(row_data.get(col, '') for col in [m['columnname'].strip() for m in mappings.get('Stücklistenvarianten', [])]) + '\n')
                varianten_set.add((stulinr, version_num))
    
    # --- 5. Build Auswahlvarianten ---
    auswahlvarianten_path = sheets_output_dir / "Auswahlvarianten_cache.csv"
    auswahlvarianten_set = set()
    if auswahlvarianten_path.exists():
        with open(auswahlvarianten_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                key = (row.get('Versionsnummer', '').strip(), row.get('Variantennummer', '').strip())
                auswahlvarianten_set.add(key)
    
    with open(auswahlvarianten_path, 'a' if auswahlvarianten_path.exists() else 'w', encoding='utf-8-sig', newline='') as f:
        if auswahlvarianten_path.stat().st_size == 0:
            fieldnames = [m['columnname'].strip() for m in (mappings.get('Stücklstenauswahlvarianten', []))]
            f.write(';'.join(fieldnames) + '\n')
        
        for stulinr in unique_stulinr:
            version_num = '1'
            variant_num = '1'
            if (version_num, variant_num) not in auswahlvarianten_set:
                row_data = {}
                for mapping in mappings.get('Stücklstenauswahlvarianten', []):
                    col = mapping['columnname'].strip()
                    func = (mapping.get('function') or '').strip()
                    arg = (mapping.get('arguments') or '').strip()
                    
                    if col == 'Versionsnummer':
                        row_data[col] = version_num
                    elif col == 'Variantennummer':
                        row_data[col] = variant_num
                    elif func == 'defaultvalue':
                        row_data[col] = arg
                    else:
                        row_data[col] = ''
                
                f.write(';'.join(row_data.get(col, '') for col in [m['columnname'].strip() for m in mappings.get('Stücklstenauswahlvarianten', [])]) + '\n')
                auswahlvarianten_set.add((version_num, variant_num))
    
    if DEBUG:
        print(f"[DEBUG] Generated BOM sheets: {len(unique_stulinr)} stücklisten, {len(versionen_set)} versionen, {len(partlist_data)} positionen")
    
    return {
        'status': 'ok',
        'stuecklisten_count': len(unique_stulinr),
        'versionen_count': len(versionen_set),
        'positionen_count': len(partlist_data),
    }

