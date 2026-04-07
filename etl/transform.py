
import csv
from datetime import datetime
from pathlib import Path
import yaml
BASE_DIR = Path(__file__).parent.parent
etl_dir = BASE_DIR / "etl"

# Debug flag for easy log removal
DEBUG = True


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
    
def is_existing_article(artnr, existing_articles_path):
    """
    Returns True if artnr is found in existingArticlesIFAS.csv, else False.
    """
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
        return f"{text1} {text2} {text3} {text4}"
    elif text1 and text2 and text3:
        return f"{text1} {text2} {text3}"
    elif text1 and text2:
        return f"{text1} {text2}"
    elif text1:
        return text1
    elif text2:
        return text2
    else:
        return ''


def getBezeichnung2(artnr):
    artbez2 = getEntryFromCSV(artikelstamm, artnr, 'artbez2')
    artbez3 = getEntryFromCSV(artikelstamm, artnr, 'artbez3')
    artbezmem= getEntryFromCSV(artikelstamm, artnr, 'artbezmem')
    return mergeTexts(artbez2, artbez3, artbezmem)


def API_import():
    import_date = "Import_via_API_" + datetime.now().strftime("%Y-%m-%d")
    return import_date

def getArtikelnummer(artnr):
    letzt_lief = getEntryFromCSV(artikelstamm, artnr, 'letzt_lief')
    return getEntryFromCSV(lieferanten_mapping, letzt_lief, 'artikelnummer')


def deriveWBZ(artnr):
    letzt_lief = getEntryFromCSV(artikelstamm, artnr, 'letzt_lief')
    wbz = getEntryFromCSV(lieferanten_mapping, letzt_lief, 'wbz')
    if wbz and wbz !='0' and wbz != 0:
        return wbz
    else:
        return '0'
    
def mapping_Bedingung_2o(Bedingung, outputIfTrue, outputElse, filename, artnr, columnname):
    status = getEntryFromCSV(filename, artnr, columnname)
    if status  == Bedingung:
        return outputIfTrue
    else:
        return outputElse
    
def isParent(artnr, stueckliste_path):
    try:
        if not check_utf8_file(stueckliste_path):
            print(f"[ERROR] Skipping isParent check for {artnr} due to stueckliste encoding.")
            return False
        with open(stueckliste_path, mode='r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
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
    if zeichnr and len(zeichnr) >= 3:
        code = zeichnr[:3]
        if len(zeichnr) >= 6:
            code2 = zeichnr[:3] + ' ' + zeichnr[3:6]
    if columnname == 'Artikelgruppe 2':
        return getEntryFromCSV(waren_artikelgruppe, code2, columnname)
    else:
        return getEntryFromCSV(waren_artikelgruppe, code, columnname)


def IstNichtAllgemeinNormteile(artnr):
    warengruppe = getGroup(waren_artikelgruppe, artnr, 'kürzel')
    artikelgruppe1 = getGroup(waren_artikelgruppe, artnr, 'Artikelgruppe1')
    if warengruppe == 'ALLG' and artikelgruppe1 == 'Normteile':
        return '0'
    else:
        return '1'

    
def build_sheet_cache_CSV(articlelist, active_sheets):

    import os
    import re
    # Helper to parse mapping_plan_{sheet}.csv and extract mapping entries
    def parse_mapping_csv(csv_path):
        mappings = []
        with open(csv_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                if not row.get('columnname'):
                    continue
                mappings.append({
                    'header': row['columnname'].strip(),
                    'function': row.get('function', '').strip(),
                    'argument': row.get('arguments', '').strip()
                })
        if DEBUG:
            print(f"[DEBUG] Parsed {len(mappings)} mappings from {csv_path}")
        return mappings

    # Function dispatcher for mapping functions
    def call_mapping_function(func, args, article, articlelist_headers=None):
        if DEBUG:
            print(f"[DEBUG] call_mapping_function: func={func}, args={args}, article artnr={article.get('artnr','')} ")
        # Direct from articlelist if no function/args and column exists
        if (not func and not args) or (func == '' and args == ''):
            if articlelist_headers and header in articlelist_headers:
                return article.get(header, '')
            return ''
        if func == '' and args == 'artnr':
            return article.get('artnr', '')
        elif func == 'defaultvalue':
            return args
        elif func == 'getEntryFromCSV':
            # args: filename, artnr, columnname
            arglist = [a.strip().strip("'") for a in args.split(',') if a.strip()]
            if len(arglist) == 3:
                filename = eval(arglist[0]) if arglist[0] in globals() else arglist[0]
                artnr_val = article.get(arglist[1], arglist[1])
                columnname = arglist[2].strip("'")
                return getEntryFromCSV(filename, artnr_val, columnname)
            else:
                return ''
        elif func == 'getGroup':
            # args: filename, artnr, columnname
            arglist = [a.strip().strip("'") for a in args.split(',') if a.strip()]
            if len(arglist) == 3:
                filename = eval(arglist[0]) if arglist[0] in globals() else arglist[0]
                artnr_val = article.get(arglist[1], arglist[1])
                columnname = arglist[2].strip("'")
                return getGroup(filename, artnr_val, columnname)
            else:
                return ''
        elif func == 'mapping_Bedingung_2o':
            # args: Bedingung, outputIfTrue, outputElse, filename, artnr, columnname
            arglist = [a.strip().strip("'") for a in args.split(',') if a.strip()]
            if len(arglist) >= 6:
                return mapping_Bedingung_2o(arglist[0], arglist[1], arglist[2], eval(arglist[3]) if arglist[3] in globals() else arglist[3], article.get(arglist[4], arglist[4]), arglist[5])
            else:
                return ''
        elif func == 'IstNichtAllgemeinNormteile':
            # args: artnr
            arglist = [a.strip().strip("'") for a in args.split(',') if a.strip()]
            if len(arglist) >= 1:
                return IstNichtAllgemeinNormteile(article.get(arglist[0], arglist[0]))
            else:
                return ''
        elif func == 'API_import':
            return API_import()
        elif func == 'deriveWBZ':
            # args: artnr
            arglist = [a.strip().strip("'") for a in args.split(',') if a.strip()]
            if len(arglist) >= 1:
                return deriveWBZ(article.get(arglist[0], arglist[0]))
            else:
                return ''
        # Add more function handlers as needed

    for sheet in active_sheets:
        mapping_csv = os.path.join('config', f'mapping_plan_{sheet}.csv')
        output_csv = os.path.join('data', 'processed', 'csv', 'cache', 'sheets', f'{sheet}_cache.csv')
        mappings = parse_mapping_csv(mapping_csv)

        # Read article list
        with open(articlelist, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            articles = list(reader)
            articlelist_headers = reader.fieldnames if reader.fieldnames else []
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
                    header = m['header']
                    func = m['function']
                    args = m['argument']
                    # Direct from articlelist if no function/args and column exists
                    row[header] = call_mapping_function(func, args, article, articlelist_headers=articlelist_headers)
                if DEBUG:
                    print(f"[DEBUG] Writing row {idx+1}/{len(articles)}: {row}")
                writer.writerow(row)


def process_module_structure(selected_artnr, artikelstamm_path, stueckliste_path, article_list_path, partlist_path, visited=None, artikel_map=None):

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

    # Overwrite article_list and partlist at the start of a new module generation (only on first call)
    if visited is None:
        visited = set()
        # Truncate/overwrite files with ; delimiter
        with open(article_list_path, 'w', encoding='utf-8') as f:
            f.write('artnr;artbez1;zeichnr\n')
        with open(partlist_path, 'w', encoding='utf-8') as f:
            f.write('stulinr;posnr;menge;artnr;artbez1\n')

    # Only load artikel_map once and pass through recursion
    if artikel_map is None:
        artikel_map = {}
        with open(artikelstamm_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                artikel_map[row.get('artnr', '').strip()] = row
        if DEBUG:
            print(f"[DEBUG] Loaded {len(artikel_map)} artikelstamm entries.")

    # Only load stueckliste_rows once and pass through recursion
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
        if DEBUG:
            print(f"[DEBUG] Loaded {len(process_module_structure.stueckliste_rows)} stueckliste rows.")
    stueckliste_rows = process_module_structure.stueckliste_rows

    def append_unique_article(artnr, artbez1, zeichnr):
        if DEBUG:
            print(f"[DEBUG] append_unique_article called with: artnr={artnr}, artbez1={artbez1}, zeichnr={zeichnr}")
        # Only add if not already present in article_list AND not in existingArticlesIFAS
        if is_existing_article(artnr, str(existing_articles_path)):
            if DEBUG:
                print(f"[DEBUG] Article {artnr} already in existingArticlesIFAS.csv, skipping.")
            return
        try:
            with open(article_list_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith(f"{artnr},"):
                        if DEBUG:
                            print(f"[DEBUG] Article {artnr} already in article_list, skipping.")
                        return
        except FileNotFoundError:
            if DEBUG:
                print(f"[DEBUG] article_list file not found, will create new.")
            pass
        try:
            with open(article_list_path, 'a', encoding='utf-8') as f:
                f.write(f"{artnr};{artbez1};{zeichnr}\n")
            if DEBUG:
                print(f"[DEBUG] Appended article: {artnr}; {artbez1}; {zeichnr}")
        except Exception as e:
            print(f"[ERROR] Failed to append article: {e}")


    # --- Tree output ---
    # Only open the tree file once at the top-level call
    tree_file_path = partlist_path.replace('.csv', '_tree.txt')
    if not hasattr(process_module_structure, '_tree_file') or visited is None or getattr(process_module_structure, '_tree_file', None) is None:
        setattr(process_module_structure, '_tree_file', open(tree_file_path, 'w', encoding='utf-8'))

    def append_partlist(stulinr, posnr, menge, artnr, artbez1, depth=0, is_last=False, prefix_stack=None, timer_start=None):
        t_stueck_start = time.time()
        with open(partlist_path, 'a', encoding='utf-8') as f:
            f.write(f"{stulinr};{posnr};{menge};{artnr};{artbez1}\n")
        if DEBUG:
            print(f"[DEBUG] Appended partlist: {stulinr}; {posnr}; {menge}; {artnr}; {artbez1}")
        # Write to tree file
        if prefix_stack is None:
            prefix_stack = []
        prefix = ''
        for is_last_parent in prefix_stack[:-1]:
            prefix += '    ' if is_last_parent else '¦   '
        if depth > 0:
            prefix += '+---'
        # Get zeichnr for this artnr
        zeichnr = artikel_map.get(artnr, {}).get('zeichnr', '')
        line = f"{prefix}{artnr}, {artbez1}, {zeichnr}"
        getattr(process_module_structure, '_tree_file').write(line + '\n')
        t_stueck_end = time.time()
        if DEBUG:
            print(f"[TIMER] Stückliste processing: {t_stueck_end - t_stueck_start:.3f}s for {stulinr}")
        if timer_start is not None and DEBUG:
            print(f"[TIMER] Total time for {stulinr}: {t_stueck_end - timer_start:.3f}s")

    # Helper to find children for a given parent
    def get_children(parent_artnr):
        return [row for row in stueckliste_rows if row.get('stulinr', '').strip() == parent_artnr]

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

