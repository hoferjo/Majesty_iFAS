import csv
from datetime import datetime
from pathlib import Path
import os 
import re
import unicodedata
import yaml

BASE_DIR = Path(__file__).parent.parent
etl_dir = BASE_DIR / "etl"

# Debug flag for easy log removal
DEBUG = False
# Separate flag for timer output
TIMER = False

# Shared in-process caches survive across endpoint calls in the same worker.
_GLOBAL_TABLE_CACHE = {}
_GLOBAL_MAPPING_CACHE = {}
_GLOBAL_UNIT_CODE_MAP = None


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
bezeichnungsregeln_path = BASE_DIR / "config" / "templates" / "Bezeichnungsregeln.yaml"
din_normteile_path = BASE_DIR / "config" / "templates" / "DIN-Normteile.yaml"
steel_table_path = BASE_DIR / "config" / "materials" / "stahltabelle.csv"
validation_overrides_path = BASE_DIR / settings["paths"]["sheets_dir"] / "Artikelbezeichnungen_validation_overrides.csv"
article_sorting_schema_path = BASE_DIR / "config" / "article_sorting_schema.yaml"

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
    row = _get_row_cached(filename, rowname, key_column='artnr', delimiter=';')
    if row is not None:
        return row.get(columnname, f"Column '{columnname}' not found")
    if DEBUG:
        print(f"No match found for artnr={rowname}")
    return 0


def _load_table_index_cached(filename, key_column='artnr', delimiter=';', encoding='utf-8-sig'):
    path_obj = Path(filename)
    exists = path_obj.exists()
    cache_key = (
        'csv_index',
        str(path_obj.resolve() if exists else path_obj),
        key_column,
        delimiter,
        encoding,
        path_obj.stat().st_mtime if exists else None,
    )
    if cache_key in _GLOBAL_TABLE_CACHE:
        return _GLOBAL_TABLE_CACHE[cache_key]

    rows_by_key = {}
    if exists:
        with open(path_obj, mode='r', encoding=encoding) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            for row in reader:
                key_val = str((row or {}).get(key_column, '') or '').strip()
                if key_val:
                    rows_by_key[key_val] = row

    _GLOBAL_TABLE_CACHE[cache_key] = rows_by_key
    return rows_by_key


def _get_row_cached(filename, rowname, key_column='artnr', delimiter=';', encoding='utf-8-sig'):
    rows_by_key = _load_table_index_cached(
        filename,
        key_column=key_column,
        delimiter=delimiter,
        encoding=encoding,
    )
    row_key = str(rowname or '').strip()
    if not row_key:
        return None
    return rows_by_key.get(row_key)

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


def _normalize_rule_text(value):
    normalized = unicodedata.normalize('NFKD', str(value or ''))
    normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r'[^a-z0-9]+', '', normalized.lower())


def _join_nonempty(values, separator=', '):
    cleaned = []
    for value in values:
        text = str(value or '').strip()
        if text:
            cleaned.append(text.strip(' ,;'))
    return separator.join(cleaned)


def _clean_source_value(value):
    if value in (None, 0):
        return ''
    text = str(value).strip()
    return '' if text == '0' else text


def _group_value_to_text(value, separator=' / '):
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item or '').strip()]
        return separator.join(parts)
    return str(value or '').strip()


def _bezeichnungselemente_to_text(elements, separator=' | '):
    if not isinstance(elements, list):
        return ''
    parts = []
    for item in elements:
        if not isinstance(item, dict):
            continue
        name = str(item.get('name', '') or '').strip()
        value = str(item.get('value', '') or '').strip()
        if not name:
            continue
        if value:
            parts.append(f"{name}={value}")
        else:
            parts.append(name)
    return separator.join(parts)


def _normteil_spec_layers(normteil_match):
    if not isinstance(normteil_match, dict):
        return []
    path = normteil_match.get('path') or []
    if isinstance(path, list) and len(path) >= 2:
        return [str(item).strip() for item in path[1:] if str(item or '').strip()]
    fallback = normteil_match.get('primary_name') or normteil_match.get('display_name') or ''
    return [str(fallback).strip()] if str(fallback or '').strip() else []


def _expand_alias_variants(term):
    """Create lightweight variants so singular/plural and separators still match.

    Example: "U-Scheiben" -> "U Scheiben", "U_Scheiben", "U-Scheibe", "U Scheibe".
    """
    text = str(term or '').strip()
    if not text:
        return []

    variants = {text}

    # Separator variants
    variants.add(text.replace('-', ' '))
    variants.add(text.replace('-', '_'))
    variants.add(text.replace('_', ' '))
    variants.add(text.replace('_', '-'))

    # Simple singular/plural normalization for common German part names.
    candidates = list(variants)
    for candidate in candidates:
        lower = candidate.lower()
        if lower.endswith('en') and len(candidate) > 3:
            singular = candidate[:-1]  # scheiben -> scheibe
            variants.add(singular)
        if lower.endswith('e') and len(candidate) > 3:
            plural = candidate + 'n'  # scheibe -> scheiben
            variants.add(plural)

    return [item for item in variants if str(item or '').strip()]


def _load_yaml_cached(path):
    path_obj = Path(path)
    cache_key = ('yaml', str(path_obj.resolve()), path_obj.stat().st_mtime if path_obj.exists() else None)
    if cache_key in _GLOBAL_TABLE_CACHE:
        return _GLOBAL_TABLE_CACHE[cache_key]
    data = {}
    if path_obj.exists():
        try:
            data = load_yaml(path_obj)
        except yaml.YAMLError as exc:
            # Deactivate invalid optional rule tables to keep module generation stable.
            print(f"[WARN] Invalid YAML in {path_obj}. Rule table disabled. Error: {exc}")
            data = {}
        except OSError as exc:
            print(f"[WARN] Could not read YAML {path_obj}. Rule table disabled. Error: {exc}")
            data = {}
    _GLOBAL_TABLE_CACHE[cache_key] = data or {}
    return data or {}


def _load_steel_table_csv_cached(path):
    path_obj = Path(path)
    cache_key = ('steel_csv', str(path_obj.resolve()), path_obj.stat().st_mtime if path_obj.exists() else None)
    if cache_key in _GLOBAL_TABLE_CACHE:
        return _GLOBAL_TABLE_CACHE[cache_key]

    rows = []
    if path_obj.exists():
        try:
            with open(path_obj, mode='r', encoding='utf-8-sig', newline='') as handle:
                reader = csv.DictReader(handle, delimiter=';')
                rows = [{str(k or '').strip(): str(v or '').strip() for k, v in (row or {}).items()} for row in reader]
        except OSError as exc:
            print(f"[WARN] Could not read steel CSV {path_obj}. Steel table disabled. Error: {exc}")
            rows = []

    _GLOBAL_TABLE_CACHE[cache_key] = rows
    return rows


def _preload_config_cache():
    """Pre-load all configuration files needed for article grouping.
    
    Called at the beginning of bulk operations (process_module_structure) to ensure
    all config files are cached before processing many articles. This avoids repeated
    file I/O and ensures consistent configuration throughout the bulk operation.
    """
    if DEBUG:
        print("[DEBUG] Pre-loading configuration cache...")
    
    try:
        # Load all config files that getArticleGroup uses
        config_dir = BASE_DIR / 'config'
        
        # Core group/subgroup/specification configs
        _load_yaml_cached(config_dir / 'groups.yaml')
        _load_yaml_cached(config_dir / 'subgroup_features.yaml')
        _load_yaml_cached(config_dir / 'specification_features.yaml')
        _load_yaml_cached(config_dir / 'group_features.yaml')
        
        # DIN normteile data
        _load_yaml_cached(config_dir / 'templates' / 'DIN-Normteile.yaml')
        
        # Steel table
        steel_path = config_dir / 'materials' / 'stahltabelle.csv'
        _load_steel_table_csv_cached(steel_path)
        
        if DEBUG:
            print("[DEBUG] Config cache pre-loaded successfully.")
    except Exception as e:
        print(f"[WARN] Error pre-loading config cache: {e}")




def _get_article_description_parts(artnr):
    artnr = str(artnr or '').strip()
    artikel_row = _get_row_cached(artikelstamm_path, artnr, key_column='artnr', delimiter=';') or {}
    parts = {
        'artbez1': _clean_source_value(artikel_row.get('artbez1', '')),
        'artbez2': _clean_source_value(artikel_row.get('artbez2', '')),
        'artbez3': _clean_source_value(artikel_row.get('artbez3', '')),
        'artbezmem': _clean_source_value(artikel_row.get('artbezmem', '')),
    }
    blob = _join_nonempty(parts.values(), ' ')
    return parts, blob, _normalize_rule_text(blob)


def _get_validation_override_value(artnr, ziel_normalized):
    target_column = None
    if ziel_normalized in {'bezeichnung1', 'artikelbezeichnung1', 'bezeichnung1de'}:
        target_column = 'bezeichnung1_de'
    elif ziel_normalized in {'bezeichnung2', 'artikelbezeichnung2', 'bezeichnung2de'}:
        target_column = 'bezeichnung2_de'
    elif ziel_normalized in {'lieferant', 'artikelbezeichnunglieferant', 'bezeichnunglieferant'}:
        target_column = 'lieferant_bezeichnung'
    elif ziel_normalized in {'zusatz', 'artikelzusatzbezeichnung', 'artikelzusatzbezeichnunglieferant', 'zusatzbezeichnung'}:
        target_column = 'lieferant_zusatz'

    if not target_column:
        return ''

    row = _get_row_cached(validation_overrides_path, str(artnr or '').strip(), key_column='artnr', delimiter=';') or {}
    return str(row.get(target_column, '') or '').strip()


def _parse_bool_flag(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def _is_bezeichnungen_anpassen_enabled():
    path_obj = settings_path
    cache_key = ('feature_flag_bezeichnungen_anpassen', str(path_obj.resolve()), path_obj.stat().st_mtime if path_obj.exists() else None)
    if cache_key in _GLOBAL_TABLE_CACHE:
        return _GLOBAL_TABLE_CACHE[cache_key]

    enabled = False
    if path_obj.exists():
        try:
            current_settings = load_yaml(path_obj) or {}
            features = current_settings.get('features') or {}
            enabled = _parse_bool_flag(features.get('bezeichnungen_anpassen'), default=False)
        except Exception as exc:
            print(f"[WARN] Could not read bezeichnungen_anpassen from {path_obj}. Defaulting to disabled. Error: {exc}")
            enabled = False

    _GLOBAL_TABLE_CACHE[cache_key] = enabled
    return enabled


def _compose_bezeichnung_value_legacy(parts, ziel_normalized):
    artbez1 = parts.get('artbez1') or ''
    artbez2 = parts.get('artbez2') or ''
    artbez3 = parts.get('artbez3') or ''
    artbezmem = parts.get('artbezmem') or ''

    if ziel_normalized in {'bezeichnung1', 'artikelbezeichnung1', 'bezeichnung1de'}:
        return artbez1
    if ziel_normalized in {'bezeichnung2', 'artikelbezeichnung2', 'bezeichnung2de'}:
        return mergeTexts(artbez2, artbez3, artbezmem)
    if ziel_normalized in {'lieferant', 'artikelbezeichnunglieferant', 'bezeichnunglieferant'}:
        return mergeTexts(artbez1, artbez2, artbez3, artbezmem)
    if ziel_normalized in {'zusatz', 'artikelzusatzbezeichnung', 'artikelzusatzbezeichnunglieferant', 'zusatzbezeichnung'}:
        return mergeTexts(artbez2, artbez3, artbezmem)
    return ''


def _merge_parameter_options(inherited, local):
    merged = {str(k): list(v) for k, v in (inherited or {}).items()}
    for key, values in (local or {}).items():
        merged[str(key)] = list(values)
    return merged


def _extract_node_parameter_options(node):
    if not isinstance(node, dict):
        return {}

    blocked_keys = {
        'Aliases', 'aliases',
        'DIN nummer', 'DIN Nummer', 'DIN number', 'DIN Number',
        'Ausführungen',
    }
    params = {}
    for key, value in node.items():
        if key in blocked_keys:
            continue
        if isinstance(value, list):
            options = []
            for item in value:
                if item is None:
                    continue
                # preserve dict objects so YAML can specify option metadata (label, value, custom_input)
                if isinstance(item, dict):
                    options.append(item)
                    continue
                text = str(item or '').strip()
                if text:
                    options.append(text)
            if options:
                params[str(key)] = options
        elif isinstance(value, (str, int, float)):
            text = str(value).strip()
            if text:
                params[str(key)] = [text]
    return params


def _match_parameter_values(normalized_blob, parameter_options, sets_data=None):
    """Match parameter options against normalized article description.
    
    Handles special cases:
    - Material: Looks for coating keywords if exact match not found
    - DIN nummer: Scores matches by length for better DIN selection
    - Sets: Validates matched values against allowed combinations
    """
    matches = {}
    assigned_numbers = set()

    def _option_in_blob(norm_option):
        norm_option = _normalize_rule_text(norm_option)
        if not norm_option:
            return False
        blob_text = str(normalized_blob or '')
        return norm_option in blob_text

    def _score_option_match(key, opt_text, normalized_option):
        normalized_option = _normalize_rule_text(normalized_option)
        if not normalized_option:
            return -1

        blob_text = str(normalized_blob or '')
        positions = [match.start() for match in re.finditer(re.escape(normalized_option), blob_text)]
        if not positions:
            return -1

        score = len(normalized_option) * 10
        lower_key = str(key or '').strip().lower()

        # Length fields are usually written as M10x50, 10x50, or 50x10.
        # Prefer the part after the x separator over the diameter token after M.
        if lower_key in {'länge', 'laenge', 'length'}:
            for pos in positions:
                prefix = blob_text[max(0, pos - 1):pos]
                suffix = blob_text[pos + len(normalized_option):pos + len(normalized_option) + 1]
                if prefix == 'x':
                    score += 120
                if prefix == 'm':
                    score -= 80
                if suffix == 'x':
                    score += 40
                if re.fullmatch(r'\d+', normalized_option):
                    score += 5
        else:
            # General preference: later, more explicit matches win over earlier embedded tokens.
            score += max(positions)

        return score

    for key, options in (parameter_options or {}).items():
        best_value = ''
        best_score = -1
        
        # Special handling for Material: recognize coating descriptors
        if key == 'Material' and options:
            coating_keywords = {
                'verzinkt': ['Stahl feuerverzinkt', 'Stahl blau-verzinkt'],
                'blau': ['Stahl blau-verzinkt'],
                'blank': ['Stahl blank'],
                'promatverzinkt': ['Stahl promatverzinkt'],
                'inox': ['INOX', 'Edelstahl'],
                'edelstahl': ['Edelstahl', 'INOX'],
            }
            for keyword, material_options in coating_keywords.items():
                if keyword in normalized_blob:
                    # Check if any of the material options for this keyword are in options
                    for mat_option in material_options:
                        if mat_option in options:
                            # Multiple keywords: prefer more specific match
                            # "blau" + "verzinkt" should match "Stahl blau-verzinkt" over "Stahl feuerverzinkt"
                            matching_keywords = sum(1 for kw in coating_keywords.keys() 
                                                   if kw in normalized_blob and mat_option in coating_keywords[kw])
                            if matching_keywords > best_score:
                                best_score = matching_keywords
                                best_value = mat_option
        
        # Standard matching for other parameters or if Material match not found
        if not best_value:
            # Try to find a match that does not reuse numeric tokens already assigned
            def extract_digits(s):
                return set(re.findall(r"\\d+", str(s or '')))

            # First pass: prefer matches with no numeric overlap
            for option in options:
                opt_text = option.get('value') if isinstance(option, dict) and option.get('value') is not None else option
                normalized_option = _normalize_rule_text(opt_text)
                if not normalized_option:
                    continue
                if _option_in_blob(normalized_option):
                    digits = extract_digits(normalized_option)
                    if digits and digits & assigned_numbers:
                        # skip in first pass if digits overlap
                        continue
                    score = _score_option_match(key, opt_text, normalized_option)
                    if score > best_score:
                        best_score = score
                        best_value = str(opt_text).strip()
            # Second pass: allow reuse of digits if no non-overlapping match found
            if not best_value:
                for option in options:
                    opt_text = option.get('value') if isinstance(option, dict) and option.get('value') is not None else option
                    normalized_option = _normalize_rule_text(opt_text)
                    if not normalized_option:
                        continue
                    if _option_in_blob(normalized_option):
                        score = _score_option_match(key, opt_text, normalized_option)
                        if score > best_score:
                            best_score = score
                            best_value = str(opt_text).strip()
            # Mark digits from chosen value as assigned
            if best_value:
                assigned_numbers.update(extract_digits(_normalize_rule_text(best_value)))
        
        if best_value:
            matches[str(key)] = best_value
    
    # Validate matches against allowed sets if defined.
    # Sets should map together as a coherent tuple (e.g. DIN + Mx + diameters + thickness)
    # instead of mixing values from different rows.
    if sets_data and isinstance(sets_data, list) and len(sets_data) > 0:
        normalized_blob = str(normalized_blob or '')

        # Build normalized option lookup per parameter key.
        key_to_options = {}
        for key, opts in (parameter_options or {}).items():
            normalized_opts = set()
            for opt in (opts or []):
                opt_text = opt.get('value') if isinstance(opt, dict) and opt.get('value') is not None else opt
                norm = _normalize_rule_text(str(opt_text or ''))
                if norm:
                    normalized_opts.add(norm)
            key_to_options[str(key)] = normalized_opts

        def _locate(term):
            term = _normalize_rule_text(term)
            if not term:
                return -1
            return normalized_blob.find(term)

        def _map_set_to_keys(raw_set):
            # Map each value from a set row to a compatible parameter key by option membership.
            # One key can be used at most once.
            if not isinstance(raw_set, list):
                return None
            mapping = []
            used_keys = set()
            for raw_val in raw_set:
                val = str(raw_val or '').strip()
                norm_val = _normalize_rule_text(val)
                if not norm_val:
                    continue
                candidate_keys = []
                for key, opt_norms in key_to_options.items():
                    if key in used_keys:
                        continue
                    if norm_val in opt_norms:
                        candidate_keys.append(key)
                if not candidate_keys:
                    return None

                # Prefer semantically specific keys first to avoid ambiguous mapping.
                preferred_order = (
                    'DIN nummer', 'DIN Nummer', 'DIN number', 'DIN Number',
                    'Metrischer Nenndurchmesser', 'Innendurchmesser', 'Außendurchmesser', 'Dicke'
                )
                chosen_key = ''
                for pref in preferred_order:
                    if pref in candidate_keys:
                        chosen_key = pref
                        break
                if not chosen_key:
                    chosen_key = candidate_keys[0]

                used_keys.add(chosen_key)
                mapping.append((chosen_key, val, norm_val))
            return mapping

        def _score_set_mapping(mapping):
            if not mapping:
                return -1

            # Base evidence: values found in the article description.
            hits = 0
            hit_weight = 0
            positions = []
            hit_norm_values = set()
            for _, _, norm_val in mapping:
                pos = _locate(norm_val)
                if pos >= 0:
                    hits += 1
                    # Single-digit numeric values are noisy in concatenated blobs;
                    # include them as low-confidence by not adding length weight.
                    if not re.fullmatch(r"\d", norm_val):
                        hit_weight += len(norm_val)
                    positions.append((pos, norm_val))
                    hit_norm_values.add(norm_val)

            if hits == 0:
                return -1

            # Reward when values from the same set appear directly nearby (explicit pairing in text).
            positions.sort(key=lambda item: item[0])
            adjacency_hits = 0
            for idx in range(len(positions) - 1):
                current_pos, current_val = positions[idx]
                next_pos, _ = positions[idx + 1]
                # "Directly next to each other": allow compact separators, parentheses and symbols.
                distance = max(0, next_pos - current_pos - len(current_val))
                if distance <= 8:
                    adjacency_hits += 1

            # Reward consistency with already matched values.
            existing_consistency = 0
            for key, _, norm_val in mapping:
                existing_norm = _normalize_rule_text(matches.get(key, ''))
                if existing_norm and existing_norm == norm_val:
                    existing_consistency += 1

            return (hit_weight * 40) + (hits * 20) + (adjacency_hits * 15) + (existing_consistency * 10)

        mapped_sets = []
        for raw_set in sets_data:
            mapping = _map_set_to_keys(raw_set)
            if mapping:
                mapped_sets.append((mapping, _score_set_mapping(mapping)))

        # Select the strongest set based on actual text evidence and adjacency.
        best_mapping = None
        best_score = -1
        for mapping, score in mapped_sets:
            if score > best_score:
                best_score = score
                best_mapping = mapping

        # Enforce set mapping only when there is real evidence in the text.
        # If not, keep the independent matches as fallback.
        if best_mapping and best_score >= 80:
            for key, raw_val, _ in best_mapping:
                matches[key] = str(raw_val).strip()
    
    return matches


def _flatten_din_normteile(din_data):
    entries = []

    def walk(node, path, inherited_params):
        if not isinstance(node, dict):
            return

        local_params = _extract_node_parameter_options(node)
        parameter_options = _merge_parameter_options(inherited_params, local_params)

        aliases = node.get('Aliases') or node.get('aliases') or []
        din_number = node.get('DIN nummer') or node.get('DIN Nummer') or node.get('DIN number') or node.get('DIN Number')
        sets_data = node.get('Sets') or node.get('sets') or []
        children = {
            key: value for key, value in node.items()
            if key not in {'Aliases', 'aliases', 'DIN nummer', 'DIN Nummer', 'DIN number', 'DIN Number', 'Sets', 'sets'}
        }

        if aliases or din_number:
            display_name = path[-1] if path else ''
            if _normalize_rule_text(display_name) in {'vollgewinde', 'teilgewinde'} and len(path) >= 2:
                primary_name = path[-2]
            else:
                primary_name = display_name
            # Parent category (e.g., Unterlegscheiben) is often the desired grouping label.
            category_name = path[-2] if len(path) >= 2 else display_name

            din_terms = []
            if isinstance(din_number, list):
                din_terms = [str(item).strip() for item in din_number if str(item or '').strip()]
            elif str(din_number or '').strip():
                din_terms = [str(din_number).strip()]

            entry_parameter_options = dict(parameter_options or {})
            if din_terms and not entry_parameter_options.get('DIN nummer'):
                entry_parameter_options['DIN nummer'] = list(din_terms)

            raw_terms = [display_name, primary_name, category_name, *din_terms, *aliases]
            search_terms = []
            for raw_term in raw_terms:
                for variant in _expand_alias_variants(raw_term):
                    if variant and variant not in search_terms:
                        search_terms.append(variant)
            entries.append({
                'path': path,
                'display_name': display_name,
                'primary_name': primary_name,
                'category_name': category_name,
                'aliases': [str(alias) for alias in aliases if str(alias or '').strip()],
                'din_number': ', '.join(din_terms),
                'din_numbers': din_terms,
                'parameter_options': entry_parameter_options,
                'bezeichnungselemente': [str(x).strip() for x in (node.get('Bezeichnungselemente') or []) if str(x or '').strip()],
                'sets': sets_data,
                'search_terms': [str(term).strip() for term in search_terms if str(term or '').strip()],
            })

        for key, value in children.items():
            if isinstance(value, dict):
                walk(value, path + [key], parameter_options)

    for key, value in (din_data or {}).items():
        if isinstance(value, dict):
            walk(value, [key], {})

    return entries


def _flatten_steel_table(steel_rows):
    entries = []

    for row in (steel_rows or []):
        if not isinstance(row, dict):
            continue

        current_norm = row.get('EN', '') or row.get('EN ', '')
        old_norm = row.get('Markenname', '')
        din_17100 = row.get('Werkstoff', '')
        steel_group = row.get('Produktgruppe', '')
        entry_name = current_norm or din_17100 or old_norm
        if not str(entry_name or '').strip():
            continue

        search_terms = [entry_name, current_norm, old_norm, din_17100, steel_group]
        for value in row.values():
            text = str(value or '').strip()
            if text:
                search_terms.append(text)

        entries.append({
            'path': [entry_name],
            'entry_name': str(entry_name or '').strip(),
            'current_norm': str(current_norm or '').strip(),
            'old_norm': str(old_norm or '').strip(),
            'din_17100': str(din_17100 or '').strip(),
            'steel_group': str(steel_group or '').strip(),
            'search_terms': [str(term).strip() for term in search_terms if str(term or '').strip()],
        })

    return entries


def _find_best_match(normalized_blob, entries):
    best_entry = None
    best_score = -1
    for entry in entries:
        for term in entry.get('search_terms', []):
            normalized_term = _normalize_rule_text(term)
            if not normalized_term:
                continue
            if normalized_term in normalized_blob:
                score = len(normalized_term)
                if score > best_score:
                    best_score = score
                    best_entry = entry
    return best_entry


def _normalize_group_path(group_path):
    tokens = []
    if isinstance(group_path, dict):
        raw_values = [group_path.get('hauptgruppe'), group_path.get('untergruppe'), group_path.get('spezifikation')]
        for value in raw_values:
            if isinstance(value, list):
                tokens.extend([str(item).strip() for item in value if str(item or '').strip()])
            else:
                text = str(value or '').strip()
                if text:
                    tokens.append(text)
    elif isinstance(group_path, (list, tuple)):
        for value in group_path:
            text = str(value or '').strip()
            if text:
                tokens.append(text)
    else:
        text = str(group_path or '').strip()
        if text:
            tokens.append(text)
    return tokens


def _find_entry_by_group_path(entries, group_path):
    requested = [_normalize_rule_text(token) for token in _normalize_group_path(group_path)]
    requested = [token for token in requested if token]
    if not requested:
        return None

    best_entry = None
    best_score = -1
    for entry in entries or []:
        candidate_terms = []
        candidate_terms.extend([entry.get('display_name', ''), entry.get('primary_name', ''), entry.get('category_name', '')])
        candidate_terms.extend(entry.get('aliases') or [])
        candidate_terms.extend(entry.get('path') or [])
        normalized_candidates = {_normalize_rule_text(term) for term in candidate_terms if str(term or '').strip()}
        score = sum(1 for token in requested if token in normalized_candidates)
        if score > best_score:
            best_score = score
            best_entry = entry

    return best_entry if best_score > 0 else None


def _get_bezeichnungsregel_context(artnr, group_path=None):
    artnr = str(artnr or '').strip()
    group_tokens = tuple(_normalize_group_path(group_path))
    cache_key = ('bezeichnungsregel_context', artnr, group_tokens)
    if cache_key in _GLOBAL_TABLE_CACHE:
        return _GLOBAL_TABLE_CACHE[cache_key]

    parts, blob, normalized_blob = _get_article_description_parts(artnr)
    bezeichnungsregeln = _load_yaml_cached(bezeichnungsregeln_path)
    din_normteile = _load_yaml_cached(din_normteile_path)
    steel_table = _load_steel_table_csv_cached(steel_table_path)

    din_entries = _flatten_din_normteile(din_normteile)
    steel_entries = _flatten_steel_table(steel_table)

    steel_match = _find_best_match(normalized_blob, steel_entries)
    normteil_match = _find_best_match(normalized_blob, din_entries)
    if not normteil_match and group_tokens:
        normteil_match = _find_entry_by_group_path(din_entries, group_path)
    normteil_parameter_matches = _match_parameter_values(
        normalized_blob,
        (normteil_match or {}).get('parameter_options') or {},
        (normteil_match or {}).get('sets') or [],
    )

    top_group = 'Sonstige'
    subgroup = ''
    if steel_match:
        top_group = 'Rohmaterialien'
        subgroup = steel_match.get('entry_name', '')
    elif normteil_match:
        top_group = 'Normteile'
        subgroup = normteil_match.get('primary_name', '')
    else:
        laser_keywords = ['laserteil', 'laserteile', 'laserschneiden', 'laser', 'abkanten', 'schweiss', 'schweissen', 'schweißen']
        mech_keywords = ['mechanisch bearbeitet', 'mechanische bearbeitung', 'drehen', 'fräsen', 'fraesen', 'bohren']
        raw_keywords = ['rohmaterial', 'rundstahl', 'flachstahl', 'blech', 'profil', 'rohr', 'stahl', 'edelstahl', 'inox', 'aluminium']

        if any(keyword in normalized_blob for keyword in (_normalize_rule_text(item) for item in laser_keywords)):
            top_group = 'Laserteile'
        elif any(keyword in normalized_blob for keyword in (_normalize_rule_text(item) for item in mech_keywords)):
            top_group = 'Mechanisch bearbeitete Teile'
        elif any(keyword in normalized_blob for keyword in (_normalize_rule_text(item) for item in raw_keywords)):
            top_group = 'Rohmaterialien'

    context = {
        'artnr': artnr,
        'parts': parts,
        'blob': blob,
        'normalized_blob': normalized_blob,
        'bezeichnungsregeln': bezeichnungsregeln,
        'din_normteile': din_normteile,
        'steel_table': steel_table,
        'steel_match': steel_match,
        'normteil_match': normteil_match,
        'normteil_parameter_matches': normteil_parameter_matches,
        'group': top_group,
        'subgroup': subgroup,
    }
    _GLOBAL_TABLE_CACHE[cache_key] = context
    return context


def getBezeichnungselemente(artnr, group_path=None):
    """Return resolved Bezeichnungselemente for an article as list of {name, value}.

    Uses DIN normteil match and matched parameter values to fill the element values.
    For DIN nummer: picks the DIN number that appears in the article description.
    """
    try:
        context = _get_bezeichnungsregel_context(artnr, group_path=group_path)
        normteil_match = context.get('normteil_match') or {}
        param_matches = context.get('normteil_parameter_matches') or {}
        elems = []
        if not normteil_match:
            return []

        bezeichnungs = normteil_match.get('bezeichnungselemente') or []
        primary_name = normteil_match.get('primary_name') or normteil_match.get('display_name') or ''
        din_number = normteil_match.get('din_number') or ''

        for elem in (bezeichnungs or []):
            key = str(elem or '').strip()
            val = ''
            options = []
            if not key:
                continue
            low = key.lower()
            if low in {'name', 'bezeichnung', 'bezeichnungsname'}:
                val = primary_name
                options = [primary_name] if primary_name else []
            elif low in {'din nummer', 'dinnummer', 'din_number'}:
                din_options = normteil_match.get('din_numbers') or []
                if not isinstance(din_options, list):
                    din_options = [str(din_number).strip()] if str(din_number or '').strip() else []
                options = [str(item).strip() for item in din_options if str(item or '').strip()]
                
                # Pick the DIN number that appears in the article description
                normalized_blob = context.get('normalized_blob') or ''
                best_din = options[0] if options else din_number
                if normalized_blob and len(options) > 1:
                    # Check which DIN number actually appears in the article
                    for din_option in options:
                        normalized_din = _normalize_rule_text(din_option)
                        if normalized_din in normalized_blob:
                            best_din = din_option
                            break
                val = best_din
            elif key in param_matches:
                val = param_matches.get(key, '')
                options = list((normteil_match.get('parameter_options') or {}).get(key, []) or [])
            else:
                # Try to resolve from article parts (artbez fields)
                parts = context.get('parts') or {}
                val = parts.get(key) or ''
                options = list((normteil_match.get('parameter_options') or {}).get(key, []) or [])
            if val and val not in options:
                options = [val] + [opt for opt in options if str(opt or '').strip() != val]
            elems.append({'name': key, 'value': val or '', 'options': options})
        return elems
    except Exception:
        return []


def _build_sorting_schema_map():
    """
    Load and flatten the sorting schema into a searchable map.
    Returns a dict mapping (hauptgruppe, untergruppe) -> spezifikation list.
    Also returns the main schema dict for reference.
    """
    schema = _load_yaml_cached(article_sorting_schema_path)
    search_map = {}  # Maps (hauptgruppe, untergruppe) -> [spezifikationen]
    
    for hauptgruppe, untergruppen in (schema or {}).items():
        if not isinstance(untergruppen, dict):
            continue
        for untergruppe, spezifikationen in untergruppen.items():
            if not isinstance(spezifikationen, dict):
                continue
            spec_list = []
            for spezifikation in spezifikationen.keys():
                if spezifikation.lower() not in {'beschreibung'}:
                    spec_list.append(spezifikation)
            key = (str(hauptgruppe).strip(), str(untergruppe).strip())
            search_map[key] = spec_list
    
    return search_map, schema


def _load_stueckliste_children_count_cached():
    path_obj = Path(stuecklistenstamm_path)
    cache_key = ('stueckliste_children_count', str(path_obj.resolve()) if path_obj.exists() else str(path_obj), path_obj.stat().st_mtime if path_obj.exists() else None)
    if cache_key in _GLOBAL_TABLE_CACHE:
        return _GLOBAL_TABLE_CACHE[cache_key]

    children_count = {}
    if path_obj.exists():
        try:
            with open(path_obj, encoding='utf-8-sig') as f:
                lines = []
                for line in f:
                    if line.strip() == '':
                        continue
                    lines.append(line)
                    if len(lines) == 1:
                        break
                lines += f.readlines()
                reader = csv.DictReader(lines, delimiter=';')
                for row in reader:
                    parent_key = str((row or {}).get('stulinr', '') or '').strip()
                    if parent_key:
                        children_count[parent_key] = children_count.get(parent_key, 0) + 1
        except Exception as exc:
            if DEBUG:
                print(f"[DEBUG] Failed to build child-count cache: {exc}")
            children_count = {}

    _GLOBAL_TABLE_CACHE[cache_key] = children_count
    return children_count


def _is_normteil_article(normalized_blob, normteil_match):
    if normteil_match:
        return True
    # Keep a lightweight fallback for DIN-based data when the direct match does not fire.
    din_data = _load_yaml_cached(din_normteile_path)
    din_entries = _flatten_din_normteile(din_data)
    return bool(_find_best_match(normalized_blob, din_entries))


def _pick_named_group(group_tree, top_name, default_name=''):
    if not isinstance(group_tree, dict):
        return default_name
    if top_name in group_tree:
        return top_name
    for candidate in group_tree.keys():
        if _normalize_rule_text(candidate) == _normalize_rule_text(top_name):
            return candidate
    return default_name


def getArticleGroup(artnr):
    """
    Return the three-level group for an article: (hauptgruppe, untergruppe, spezifikation).
    Uses DIN/steel matching logic and the sorting schema to classify articles.
    Examples:
    - DIN norm screws: ('Normteile', 'Schrauben', '6-Kant-Schraube (DIN 933)')
    - Custom laser parts: ('Zeichnungsteile', 'Lasergeteile', 'Laserschneiden')
    - Purchased items: ('Kaufteile', 'Katalogteile', 'Standard')
    """
    try:
        artnr = str(artnr or '').strip()
        parts, blob, normalized_blob = _get_article_description_parts(artnr)
        row = _get_row_cached(artikelstamm_path, artnr, key_column='artnr', delimiter=';') or {}
        zeichnr = str(row.get('zeichnr') or '').strip()
        children_count = _load_stueckliste_children_count_cached().get(artnr, 0)

        groups_cfg = _load_yaml_cached(BASE_DIR / 'config' / 'groups.yaml') or {}
        subgroup_features = _load_yaml_cached(BASE_DIR / 'config' / 'subgroup_features.yaml') or {}
        specification_features = _load_yaml_cached(BASE_DIR / 'config' / 'specification_features.yaml') or {}

        # Main rule requested by the user.
        hauptgruppe = 'Produktionsteile' if children_count >= 1 else 'Einkaufsteile'
        hauptgruppe_tree = groups_cfg.get(hauptgruppe, {}) if isinstance(groups_cfg, dict) else {}
        if not isinstance(hauptgruppe_tree, dict):
            hauptgruppe_tree = {}

        # Business rule: production parts must not have subgroup/specification.
        if hauptgruppe == 'Produktionsteile':
            return (hauptgruppe, '', '')

        # Refine the subgroup with the DIN normteil list first, then drawing article, then config fallbacks.
        normteil_match = None
        din_data = _load_yaml_cached(din_normteile_path)
        din_entries = _flatten_din_normteile(din_data)
        normteil_match = _find_best_match(normalized_blob, din_entries)

        if _is_normteil_article(normalized_blob, normteil_match):
            normteil_data = normteil_match or _find_best_match(normalized_blob, din_entries) or {}
            subgroup = _pick_named_group(hauptgruppe_tree, 'Normteile', 'Normteile')
            if not subgroup:
                subgroup = 'Normteile'
            # Use the key path below the DIN root as a layered specification.
            spezifikation = _normteil_spec_layers(normteil_data)
            return (hauptgruppe, subgroup, spezifikation)

        if zeichnr:
            subgroup = _pick_named_group(hauptgruppe_tree, 'Zeichnungsteile', 'Zeichnungsteile')
            if not subgroup:
                subgroup = 'Zeichnungsteile'

            # Try to refine the specification via specification_features if this subgroup has rules.
            spec_group = specification_features.get(subgroup) or specification_features.get('Zeichnungsteile') or {}
            if isinstance(spec_group, dict):
                for spec_name, rule in spec_group.items():
                    tokens = []
                    if isinstance(rule, str):
                        tokens = [token.strip() for token in rule.split(',') if token.strip()]
                    elif isinstance(rule, list):
                        tokens = [str(token).strip() for token in rule if str(token or '').strip()]
                    for token in tokens:
                        if _normalize_rule_text(token) and _normalize_rule_text(token) in normalized_blob:
                            return (hauptgruppe, subgroup, spec_name)

            # For Zeichnungsteile, if no rule matched, default to one of the valid specs instead of zeichnr.
            # Try to get configured specs for this subgroup; if none match, use 'Listenteile' as catch-all.
            configured_specs = []
            if isinstance(groups_cfg, dict) and hauptgruppe in groups_cfg:
                zeichnungsteile_specs = hauptgruppe_tree.get(subgroup, {})
                if isinstance(zeichnungsteile_specs, dict):
                    configured_specs = list(zeichnungsteile_specs.keys())
            
            if configured_specs:
                return (hauptgruppe, subgroup, configured_specs[0] if configured_specs else 'Listenteile')
            else:
                # Fallback to the first available spec from specification_features
                available_specs = [s for s in spec_group.keys() if s]
                return (hauptgruppe, subgroup, available_specs[0] if available_specs else 'Listenteile')

        # Final fallback: use subgroup feature hints or the generic article state.
        if isinstance(subgroup_features, dict):
            for sub_name, condition in subgroup_features.items():
                cond = str(condition or '').strip().lower()
                if cond == 'rest':
                    return (hauptgruppe, _pick_named_group(hauptgruppe_tree, sub_name, sub_name) or sub_name, 'Standard')

        return (hauptgruppe, '', '')

    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] Error in getArticleGroup({artnr}): {e}")
        return ('', '', '')


def _resolve_steel_material(context):
    match = context.get('steel_match') or {}
    if not match:
        return ''
    current_norm = match.get('current_norm') or ''
    din_17100 = match.get('din_17100') or ''
    steel_group = match.get('steel_group') or ''
    primary = current_norm or din_17100 or match.get('old_norm') or match.get('entry_name') or ''
    if primary and steel_group:
        return f"{primary} / {steel_group}"
    return primary or steel_group


def _compose_bezeichnung_value(context, ziel):
    ziel_normalized = _normalize_rule_text(ziel)
    description_targets = {
        'bezeichnung1', 'artikelbezeichnung1', 'bezeichnung1de',
        'bezeichnung2', 'artikelbezeichnung2', 'bezeichnung2de',
        'lieferant', 'artikelbezeichnunglieferant', 'bezeichnunglieferant',
        'zusatz', 'artikelzusatzbezeichnung', 'artikelzusatzbezeichnunglieferant', 'zusatzbezeichnung',
    }
    override_value = _get_validation_override_value(context.get('artnr', ''), ziel_normalized)
    if override_value:
        return override_value

    parts = context.get('parts') or {}
    if not _is_bezeichnungen_anpassen_enabled():
        if ziel_normalized in description_targets:
            return _compose_bezeichnung_value_legacy(parts, ziel_normalized)

    artbez1 = parts.get('artbez1') or ''
    artbez2 = parts.get('artbez2') or ''
    artbez3 = parts.get('artbez3') or ''
    artbezmem = parts.get('artbezmem') or ''
    group = context.get('group') or ''
    subgroup = context.get('subgroup') or ''
    normteil_match = context.get('normteil_match') or {}
    normteil_parameter_matches = context.get('normteil_parameter_matches') or {}
    normteil_parameter_text = _join_nonempty(normteil_parameter_matches.values(), ' ')
    steel_value = _resolve_steel_material(context)

    if ziel_normalized in {'bezeichnung1', 'artikelbezeichnung1', 'bezeichnung1de'}:
        if group == 'Normteile':
            if subgroup:
                return _join_nonempty([subgroup, artbez2, artbez3, normteil_parameter_text], ' ')
            return artbez1 or _join_nonempty([artbez2, artbez3, artbezmem], ' ')
        if group == 'Rohmaterialien' and steel_value:
            return artbez1 or steel_value
        return artbez1 or _join_nonempty([artbez2, artbez3, artbezmem], ' ')

    if ziel_normalized in {'bezeichnung2', 'artikelbezeichnung2', 'bezeichnung2de'}:
        if group == 'Normteile':
            din_number = normteil_match.get('din_number') or ''
            if din_number:
                return din_number
            return _join_nonempty([artbez2, artbez3, artbezmem], ', ')
        if group == 'Rohmaterialien' and steel_value:
            return _join_nonempty([steel_value, artbez2], ', ')
        return _join_nonempty([artbez2, artbez3, artbezmem], ', ')

    if ziel_normalized in {'lieferant', 'artikelbezeichnunglieferant', 'bezeichnunglieferant'}:
        if group == 'Normteile':
            base = _join_nonempty([subgroup or artbez1, artbez2, artbez3, normteil_parameter_text], ' ')
            din_number = normteil_match.get('din_number') or ''
            return _join_nonempty([base, din_number], ' ')
        if group == 'Rohmaterialien' and steel_value:
            return _join_nonempty([artbez1, steel_value, artbez2, artbez3], ' ')
        return _join_nonempty([artbez1, artbez2, artbez3, artbezmem], ' ')

    if ziel_normalized in {'zusatz', 'artikelzusatzbezeichnung', 'artikelzusatzbezeichnunglieferant', 'zusatzbezeichnung'}:
        if group == 'Normteile':
            return _join_nonempty([artbez3, artbezmem], ', ')
        if group == 'Rohmaterialien' and steel_value:
            return _join_nonempty([steel_value, artbez3, artbezmem], ', ')
        return _join_nonempty([artbez2, artbez3, artbezmem], ', ')

    if ziel_normalized == 'material':
        if steel_value:
            return steel_value
        if group == 'Normteile' and normteil_match.get('primary_name'):
            return normteil_match.get('primary_name')
        return ''

    return ''


def getBezeichnungNachRegeln(artnr, ziel):
    context = _get_bezeichnungsregel_context(artnr)
    return _compose_bezeichnung_value(context, ziel)

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


def getMaterialNachRegeln(artnr):
    context = _get_bezeichnungsregel_context(artnr)
    return _compose_bezeichnung_value(context, 'material')


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
    global _GLOBAL_UNIT_CODE_MAP
    if _GLOBAL_UNIT_CODE_MAP is None:
        mapping = load_yaml(BASE_DIR / "config" / "mapping_abbrevations.yaml") or {}
        _GLOBAL_UNIT_CODE_MAP = {
            str(k): str((v or {}).get("code", ""))
            for k, v in (mapping.get("units") or {}).items()
        }

    code = _GLOBAL_UNIT_CODE_MAP.get(str(abbrevation), "")
    if code:
        return code
    if DEBUG:
        print(f"Warning: No code found for abbrevation '{abbrevation}' in mapping_abbrevations.yaml")
    return ''


def getMasseinheit(artnr):
    masseinheit = getEntryFromCSV(artikelstamm_path, artnr, 'meinheit')
    if masseinheit and str(masseinheit).strip() != '':
        return getCodeFromAbbrevation(masseinheit)
    return ''


def _normalize_function_name(name):
    normalized = str(name or '').strip()
    aliases = {
        'derive_WBZ': 'deriveWBZ',
        'derive_wbz': 'deriveWBZ',
        'defaultValue': 'defaultvalue',
        'directCopy': 'direct_copy',
    }
    return aliases.get(normalized, normalized)


def _normalize_mapping_name(name):
    import unicodedata
    normalized = unicodedata.normalize('NFKD', str(name or ''))
    normalized = ''.join(ch for ch in normalized if ch.isalnum()).lower()
    return normalized


def _resolve_filename_token(token):
    path_mapping = {
        'artikelstamm': artikelstamm_path,
        'artikelstamm_path': artikelstamm_path,
        'stuecklistenstamm_path': stuecklistenstamm_path,
        'waren_artikelgruppe_path': waren_artikelgruppe_path,
        'lieferanten_mapping_path': lieferanten_mapping_path,
    }
    return path_mapping.get(token, token)


def _find_mapping_file(base_dir, category, sheet_name):
    bom_dir = Path(base_dir) / 'config' / 'sheet_mappings' / category
    if not bom_dir.exists():
        return None
    exact = bom_dir / f"mapping_plan_{sheet_name}.csv"
    if exact.exists():
        return exact

    target_norm = _normalize_mapping_name(sheet_name)
    candidates = []
    for path in bom_dir.glob('mapping_plan_*.csv'):
        candidate_name = path.stem.replace('mapping_plan_', '')
        candidate_norm = _normalize_mapping_name(candidate_name)
        if candidate_norm == target_norm:
            return path
        candidates.append((candidate_norm, path))

    import difflib
    candidate_norms = [norm for norm, _ in candidates]
    close = difflib.get_close_matches(target_norm, candidate_norms, n=1, cutoff=0.6)
    if close:
        for norm, path in candidates:
            if norm == close[0]:
                return path
    return None


def _parse_mapping_csv(csv_path):
    mappings = []
    if not csv_path:
        return mappings
    with open(csv_path, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            columnname = (row.get('columnname') or '').strip()
            if not columnname:
                continue
            raw_func = row.get('function') or row.get('funtion')
            func = _normalize_function_name(raw_func)
            argument = (row.get('arguments') or '').strip()
            arglist = []
            if argument:
                for token in argument.split(','):
                    token = token.strip()
                    if (token.startswith("'") and token.endswith("'")) or (token.startswith('"') and token.endswith('"')):
                        token = token[1:-1]
                    arglist.append(token)
            mappings.append({
                'columnname': columnname,
                'function': func,
                'argument': argument,
                'arglist': arglist,
            })
    return mappings


def _normalize_posnr_4(value):
    pos = str(value or '').strip()
    if not pos:
        return ''
    if pos.isdigit():
        return pos.zfill(4)
    return pos


def _evaluate_bom_mapping(mapping, context):
    func = (mapping.get('function') or '').strip()
    arglist = mapping.get('arglist', [])
    partlist_row = context.get('partlist_row') or {}

    def _resolve_arg(token):
        if token in {'artnr', 'stulinr', 'posnr', 'menge'} and token in partlist_row:
            return partlist_row.get(token, '')
        return context.get(token, token)

    if not func:
        if arglist:
            return str(_resolve_arg(arglist[0]) or '')
        return ''

    if func == 'defaultvalue':
        return mapping.get('argument', '')

    if func == 'direct_copy':
        if arglist:
            return str(_resolve_arg(arglist[0]) or '')
        return ''

    if func == 'getEntryFromCSV':
        if len(arglist) >= 3:
            filename = _resolve_filename_token(arglist[0])
            row_key = str(_resolve_arg(arglist[1]) or '')
            cached_lookup = context.get('_get_entry_cached')
            if callable(cached_lookup):
                return cached_lookup(filename, row_key, arglist[2])
            return getEntryFromCSV(filename, row_key, arglist[2])
        return ''

    if func == 'getBezeichnung2':
        if arglist:
            artnr_val = str(_resolve_arg(arglist[0]) or '')
            cached_lookup = context.get('_get_entry_cached')
            if callable(cached_lookup):
                artbez2 = cached_lookup(artikelstamm_path, artnr_val, 'artbez2')
                artbez3 = cached_lookup(artikelstamm_path, artnr_val, 'artbez3')
                artbezmem = cached_lookup(artikelstamm_path, artnr_val, 'artbezmem')
                return mergeTexts(artbez2, artbez3, artbezmem)
            return getBezeichnung2(artnr_val)
        return ''

    if func == 'getMasseinheit':
        if arglist:
            artnr_val = str(_resolve_arg(arglist[0]) or '')
            cached_lookup = context.get('_get_entry_cached')
            if callable(cached_lookup):
                masseinheit = cached_lookup(artikelstamm_path, artnr_val, 'meinheit')
                masseinheit = str(masseinheit or '').strip()
                if masseinheit:
                    return getCodeFromAbbrevation(masseinheit)
                return ''
            return getMasseinheit(artnr_val)
        return ''

    if func == 'API_import':
        return API_import(context.get('root_module_artnr'))

    if func == 'getNameOrNumber':
        if len(arglist) >= 2:
            mode = arglist[0]
            number_suffix = '1'
            version = '1'
            name_suffix = 'Standard'
            stulinr_val = _resolve_arg(arglist[1])
            sheet_type = arglist[2] if len(arglist) >= 3 else ''
            return getNameOrNumber(stulinr_val, sheet_type, mode, name_suffix, number_suffix, version)
        return ''

    if func == 'getFromPartlist':
        if len(arglist) >= 3:
            field_name = arglist[2]
            row = context.get('partlist_row')
            if row and field_name in row:
                value = str(row.get(field_name, '') or '')
                if str(field_name).strip().lower() == 'posnr':
                    return _normalize_posnr_4(value)
                return value
            for prow in context.get('partlist_data', []):
                if prow.get('stulinr', '').strip() == str(context.get('stulinr', '')).strip() and prow.get('artnr', '').strip() == str(context.get('artnr', '')).strip():
                    value = str(prow.get(field_name, '') or '')
                    if str(field_name).strip().lower() == 'posnr':
                        return _normalize_posnr_4(value)
                    return value
        return ''

    if func == 'getMenge':
        row = context.get('partlist_row')
        if row is not None:
            return str(row.get('menge', '') or '')
        return ''

    if func == 'date':
        if arglist and arglist[0].lower() == 'today':
            return datetime.now().strftime('%d.%m.%Y')
        return arglist[0] if arglist else ''

    return ''


def getNameOrNumber(stulinr,
                    StuLiSheet,
                    NameOrNumber : str = "number",
                    name_suffix : str = "Standard",
                    number_suffix : str = "1",
                    version : str = "1"
                    ):
    
    if StuLiSheet == "Version":
        return str(stulinr)+"-" + str(version)
    elif StuLiSheet == "Variante":
        if NameOrNumber == "name":
            return str(stulinr)+"-" + str(version) + "-" + str(name_suffix) +"-Variante"
        else:
            return str(stulinr)+"-" + str(version) + "-" + str(number_suffix)
    elif StuLiSheet == "Auswahlvariante":
        if NameOrNumber == "name":
            return str(stulinr)+"-" + str(version) + "--" + str(name_suffix) +"-Auswahlvariante"
        else:
            return str(stulinr)+"-" + str(version) + "--" + str(number_suffix)

def getStuLiOptions(NameOrNumber, stulinr, StuLiSheet, number: int = 1):
    if NameOrNumber == "name":
        return getNameOrNumber(stulinr, StuLiSheet)
    elif NameOrNumber == "number":
        return getNameOrNumber(stulinr, StuLiSheet, version=number)

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
                # Support multiple header names used across mapping files ('columnname', 'column')
                header = (row.get('columnname') or row.get('column') or row.get('column_name') or '').strip()
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

        def _is_artikelnummer_header(name):
            import unicodedata
            normalized = unicodedata.normalize('NFKD', str(name or ''))
            normalized = ''.join(ch for ch in normalized if ch.isalnum()).lower()
            return normalized == 'artikelnummer'

        def _export_artikelnummer_value():
            artikelnummer_value = str(article.get('artikelnummer', '') or '').strip()
            if artikelnummer_value:
                return artikelnummer_value
            return str(article.get('artnr', '') or '').strip()

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
                if _is_artikelnummer_header(header):
                    return _export_artikelnummer_value()
                return article.get(header, '')
            return ''

        if func == '' and args == 'artnr':
            if _is_artikelnummer_header(header):
                return _export_artikelnummer_value()
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

        if func == 'getBezeichnungNachRegeln':
            # args: artnr, ziel
            if len(arglist) >= 2:
                artnr_val = article.get(arglist[0], arglist[0])
                return getBezeichnungNachRegeln(artnr_val, arglist[1])
            return ''

        if func == 'getMaterialNachRegeln':
            # args: artnr
            if len(arglist) >= 1:
                artnr_val = article.get(arglist[0], arglist[0])
                return getMaterialNachRegeln(artnr_val)
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

    # Determine if this is for blocked articles by filename.
    # Supports both legacy "blocked_articles.csv" and mode-specific
    # names like "blocked_articles_module_mode.csv".
    is_blocked = False
    if isinstance(articlelist, (str, Path)):
        articlelist_name = Path(str(articlelist)).name.lower()
        if 'blocked_articles' in articlelist_name:
            is_blocked = True

    for sheet in active_sheets:
        # Map sheet names to their category directories
        sheet_to_category = {
            # Article sheets
            'Artikelstamm': 'Article',
            'ArtikelDisposteuerung': 'Article', 
            'ArtikelLieferantendaten': 'Article',
            'DMSDocuments': 'Docs',
            # BOM sheets
            'Stücklisten': 'BOM',
            'Stücklistenvarianten': 'BOM',
            'Stücklistenversionen': 'BOM',
            'Stücklistenverwendung': 'BOM',
            'Stücklstenauswahlvarianten': 'BOM',
            'Stücklistenpositionen': 'BOM',
            # Workplan sheets
            'Arbeitspläne': 'Workplan',
            'Arbeitsplanpositionen': 'Workplan',
            'Arbeitsplanversionen': 'Workplan',
        }
        # Default to Article if not found
        category = sheet_to_category.get(sheet, 'Article')
        # Try to resolve mapping file flexibly (handles underscores, pluralization, and legacy names)
        mapping_path = _find_mapping_file(BASE_DIR, category, sheet)
        # Special-case Docs mappings which sometimes use a different filename pattern (e.g. mapping_DMSDocuments.csv)
        if mapping_path is None and category == 'Docs':
            docs_dir = Path(BASE_DIR) / 'config' / 'sheet_mappings' / 'Docs'
            if docs_dir.exists():
                for p in docs_dir.glob('*.csv'):
                    if 'dms' in p.stem.lower():
                        mapping_path = p
                        break

        if mapping_path is None:
            if DEBUG:
                print(f"[DEBUG] No mapping plan found for sheet '{sheet}' in category '{category}' (checked sheet name and normalized candidates). Skipping sheet.")
            # Skip sheets without mapping definitions
            continue
        mapping_csv = str(mapping_path)
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
                # --- Custom filtering for ArtikelLieferantendaten ---
                if sheet in ("ArtikelLieferantendaten", "Artikel_Lieferantendaten"):
                    beschaffungsart = str(article.get("beschaffungsart", "")).strip()
                    if not beschaffungsart:
                        artnr_for_filter = str(article.get('artnr', '') or '').strip()
                        if artnr_for_filter:
                            beschaffungsart = str(get_beschaffungsart_cached(artnr_for_filter)).strip()
                    if beschaffungsart not in ("Einkauf", "6"):
                        continue  # Skip this article for Lieferantendaten

                # --- Custom mapping for ArtikelDisposteuerung.wiederbeschaffungszeit ---
                if sheet in ("ArtikelDisposteuerung", "Artikel_Disposteuerung"):
                    beschaffungsart = str(article.get("beschaffungsart", "")).strip()
                    if beschaffungsart in ("1", "Produktion"):
                        # Find the mapping for wiederbeschaffungszeit and set to empty
                        for m in mappings:
                            if m['header'] == "wiederbeschaffungszeit":
                                article["wiederbeschaffungszeit"] = ""
                                break

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
    mode=None,
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
    # Pre-load all config files into cache for this bulk operation
    _preload_config_cache()
    
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

    workplan_suggest_paths = [
        BASE_DIR / "data" / "processed" / "cache" / "workplan" / "workplan_suggest-L.csv",
        BASE_DIR / "data" / "processed" / "workplan" / "workplan_suggest-L.csv",
    ]

    def _init_workplan_suggest(reset: bool = False):
        for path in workplan_suggest_paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            if reset or not path.exists() or path.stat().st_size == 0:
                with open(path, 'w', encoding='utf-8-sig', newline='') as f:
                    f.write('artnr\n')

    def _load_workplan_suggest_seen():
        seen = set()
        primary = workplan_suggest_paths[0]
        if not primary.exists():
            return seen
        with open(primary, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f, delimiter=';')
            if reader.fieldnames and len(reader.fieldnames) == 1 and reader.fieldnames[0].strip().lower() == 'artnr':
                for row in reader:
                    key = str((row or {}).get('artnr', '') or '').strip()
                    if key:
                        seen.add(key)
            else:
                f.seek(0)
                next(f, None)
                for line in f:
                    key = str(line or '').strip().split(';')[0]
                    if key:
                        seen.add(key)
        return seen

    _init_workplan_suggest(reset=bool(reset_files))
    workplan_suggest_seen = _load_workplan_suggest_seen()

    expected_article_list_header = 'artnr;artbez1;zeichnr;hauptgruppe;untergruppe;spezifikation;bezeichnungselemente;artikelnummer\n'

    def _ensure_article_list_header(path):
        file_path = Path(path)
        if not file_path.exists() or file_path.stat().st_size == 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(expected_article_list_header)
            return
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        if not lines:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(expected_article_list_header)
            return
        current_header = str(lines[0] or '').strip().lower()
        if 'bezeichnungselemente' in current_header:
            return
        lines[0] = expected_article_list_header
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    def _append_workplan_suggest(base_artnr):
        key = str(base_artnr or '').strip()
        if not key or key in workplan_suggest_seen:
            return
        for path in workplan_suggest_paths:
            with open(path, 'a', encoding='utf-8-sig', newline='') as f:
                f.write(f"{key}\n")
        workplan_suggest_seen.add(key)
    # Overwrite article_list, partlist, and blocked_articles only if reset_files is True
    if reset_files:
        with open(article_list_path, 'w', encoding='utf-8') as f:
            f.write(expected_article_list_header)
        with open(partlist_path, 'w', encoding='utf-8') as f:
            f.write('stulinr;posnr;menge;artnr;artbez1\n')
        blocked_articles_path = str(article_list_path).replace('article_list', 'blocked_articles')
        # Always clear the blocked articles file (write header), even if there are no blocked articles in the new run
        with open(blocked_articles_path, 'w', encoding='utf-8') as f:
            f.write('artnr;artbez1;zeichnr\n')

        # Also clear all <sheet>_cache_blocked.csv files for all active sheets
        active_sheets_path = BASE_DIR / "config" / "active_sheets.csv"
        if active_sheets_path.exists():
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
    else:
        _ensure_article_list_header(article_list_path)

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
    artikelnummer_overrides = {}
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
            artikelnummer_out = str(artikelnummer_overrides.get(artnr_key) or artikelnummer_overrides.get(effective_artnr) or '').strip()
            # determine group for this article and write as fourth, fifth, sixth columns
            hauptgruppe, untergruppe, spezifikation = getArticleGroup(effective_artnr)
            spezifikation_text = _group_value_to_text(spezifikation)
            bezeichnungselemente_text = _bezeichnungselemente_to_text(getBezeichnungselemente(effective_artnr))
            with open(article_list_path, 'a', encoding='utf-8') as f:
                f.write(f"{effective_artnr};{effective_artbez1};{effective_zeichnr};{hauptgruppe};{untergruppe};{spezifikation_text};{bezeichnungselemente_text};{artikelnummer_out}\n")
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
    # Always use the configured partlisttree path for the tree file (matches backend download)
    
    tree_file_path = get_path("partlisttree", mode)
    if not hasattr(process_module_structure, '_tree_file') or visited is None or getattr(process_module_structure, '_tree_file', None) is None:
        Path(tree_file_path).parent.mkdir(parents=True, exist_ok=True)
        setattr(process_module_structure, '_tree_file', open(tree_file_path, 'w', encoding='utf-8'))


    # --- Partlist existing checker ---
    # Load existing partlists (stulinr) from processed cache (all envs)
    existing_partlists = set()
    existing_dir = BASE_DIR / "data" / "processed" / "cache" / "existing"
    if existing_dir.exists():
        for f in existing_dir.glob("partlists_*.csv"):
            with open(f, encoding="utf-8") as ef:
                for line in ef:
                    val = line.strip().split(';')[0]
                    if val:
                        existing_partlists.add(val)

    # Track stulinr written in this run to avoid duplicates within the same run
    written_partlists = set()

    def append_partlist(stulinr, posnr, menge, artnr, artbez1, depth=0, is_last=False, prefix_stack=None, timer_start=None, replacement_info=None, nur_verkaufsartikel=False, output_artnr=None):
        t_stueck_start = time.time()
        artnr_key = str(artnr or '').strip()
        mapped_artnr = str(replacement_map.get(artnr_key, artnr_key) or '').strip()
        effective_artnr = str(output_artnr or mapped_artnr or artnr_key).strip()
        effective_row = artikel_map.get(effective_artnr, {}) or artikel_map.get(artnr_key, {})
        effective_artbez1 = effective_row.get('artbez1', '') or artbez1
        # Check if blocked
        sperre = (effective_row.get('sperre', '') or '').strip()
        menge_out = menge
        stulinr_key = str(stulinr or '').strip()
        # Check for existing partlist
        is_existing = stulinr_key in existing_partlists
        # Mark blocked
        if sperre and sperre.upper() != 'FALSCH':
            menge_out = f"{menge}BLOCKED"

        # Compose row
        row = f"{stulinr};{posnr};{menge_out};{effective_artnr};{effective_artbez1}"
        if is_existing:
            row += ";Existing"
        if replacement_info:
            row += f";replacing {replacement_info}"
        if nur_verkaufsartikel:
            row += ";Nur Verkaufsartikel"

        # Write to partlist_duplicates if existing, else to partlist.csv
        if is_existing:
            # Write only to partlist_duplicates_{mode}_mde.csv
            mode = 'module' # default, can be improved to detect actual mode
            partlist_duplicates_path = str(partlist_path).replace("partlist.csv", f"partlist_duplicates_{mode}_mde.csv")
            if not Path(partlist_duplicates_path).exists():
                with open(partlist_duplicates_path, 'w', encoding='utf-8') as f:
                    f.write('stulinr;posnr;menge;artnr;artbez1;Mark\n')

            with open(partlist_duplicates_path, 'a', encoding='utf-8') as f:
                f.write(row + "\n")
        else:
            with open(partlist_path, 'a', encoding='utf-8') as f:
                f.write(row + "\n")
        written_partlists.add(stulinr_key)
        if DEBUG:
            print(f"[DEBUG] Appended partlist: {row}")
        # Write to tree file (always)
        if prefix_stack is None:
            prefix_stack = []
        prefix = ''
        for is_last_parent in prefix_stack[:-1]:
            prefix += '    ' if is_last_parent else '¦   '
        if depth > 0:
            prefix += '+---'
        # Get zeichnr for this artnr
        zeichnr = effective_row.get('zeichnr', '')
        tree_line = prefix
        if sperre and sperre.upper() != 'FALSCH':
            tree_line += f"BLOCKED {effective_artnr}, {effective_artbez1}, {zeichnr}"
        else:
            tree_line += f"{effective_artnr}, {effective_artbez1}, {zeichnr}"
        if is_existing:
            tree_line += " ;Existing"
        if replacement_info:
            tree_line += f" ;replacing {replacement_info}"
        if nur_verkaufsartikel:
            tree_line += ";Nur Verkaufsartikel"
        getattr(process_module_structure, '_tree_file').write(tree_line + '\n')
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
            # Replacement and Nur Verkaufsartikel logic can be injected here if needed
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
                            f.write("artnr;artbez1;zeichnr;hauptgruppe;untergruppe;spezifikation;bezeichnungselemente;artikelnummer\n")
                        # compute groups for auto-created entry
                        hg, ug, spec = getArticleGroup(current_artnr)
                        spec_text = _group_value_to_text(spec)
                        bez_elems_text = _bezeichnungselemente_to_text(getBezeichnungselemente(current_artnr))
                        f.write(f"{current_artnr};Auto {current_artnr};Auto {current_artnr};{hg};{ug};{spec_text};{bez_elems_text};\n")
                    artikel_map[current_artnr] = {'artnr': current_artnr, 'artbez1': f"Auto {current_artnr}", 'zeichnr': f"Auto {current_artnr}"}
                    artbez1 = f"Auto {current_artnr}"
                    zeichnr = f"Auto {current_artnr}"
            except Exception as e:
                print(f"[ERROR] Could not auto-create article {current_artnr}: {e}")
        append_unique_article(current_artnr, artbez1, zeichnr)
        # Tree output and partlist already handled in append_partlist
        children = get_children(current_artnr)

        # Normalize parent->child -L rows for partlist/tree output.
        # If current parent is X and a child is X-L, write X to partlist/tree and keep X-L in article_list.
        parent_artnr = str(current_artnr or '').strip()
        parent_l_artnr = f"{parent_artnr}-L" if parent_artnr else ''

        normalized_children = []
        for row in children:
            child_artnr = str((row or {}).get('artnr', '') or '').strip()
            output_artnr = child_artnr
            if parent_l_artnr and child_artnr == parent_l_artnr:
                output_artnr = parent_artnr
                artikelnummer_overrides[child_artnr] = output_artnr
                _append_workplan_suggest(output_artnr)
            normalized_children.append((row, child_artnr, output_artnr))

        for idx, (row, source_artnr, output_artnr) in enumerate(normalized_children):
            # Always append to partlist_tree, even if child is a -L variant and would be normalized to its parent
            posnr = row.get('posnr', '').strip()
            menge = row.get('menge', '').strip()
            artbez1_child = artikel_map.get(source_artnr, {}).get('artbez1', '')
            is_last = (idx == len(normalized_children) - 1)
            append_partlist(
                current_artnr,
                posnr,
                menge,
                source_artnr,
                artbez1_child,
                depth + 1,
                is_last,
                prefix_stack + [is_last] if prefix_stack else [is_last],
                timer_start,
                output_artnr=output_artnr,
            )
            if source_artnr not in visited:
                visited.add(source_artnr)
                recurse_all_articles(source_artnr, depth + 1, (prefix_stack + [is_last]) if prefix_stack else [is_last], timer_start)

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

    bom_category = "BOM"
    sheet_names = [
        'Stücklisten',
        'Stücklistenversionen',
        'Stücklistenpositionen',
        'Stücklistenvarianten',
        'Stücklstenauswahlvarianten',
    ]

    table_cache = {}

    def _load_table_by_column(filename, key_column):
        file_path = str(Path(filename))
        cache_key = (file_path, key_column)
        if cache_key in table_cache:
            return table_cache[cache_key]

        rows_by_key = {}
        try:
            with open(file_path, mode='r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                for r in reader:
                    key = str((r or {}).get(key_column, '') or '').strip()
                    if key:
                        rows_by_key[key] = r
        except FileNotFoundError:
            rows_by_key = {}

        table_cache[cache_key] = rows_by_key
        return rows_by_key

    def _infer_key_column(filename):
        try:
            if Path(filename).resolve() == Path(lieferanten_mapping_path).resolve():
                return 'liefnr'
        except Exception:
            pass
        return 'artnr'

    def _get_entry_cached(filename, rowname, columnname):
        key_column = _infer_key_column(filename)
        rows_by_key = _load_table_by_column(filename, key_column)
        row = rows_by_key.get(str(rowname or '').strip())
        if not row:
            return 0
        return row.get(columnname, '')

    # Initialize sets and lists for version tracking and rows
    versionen_set = set()
    stuecklisten_versionen_rows = []
    mappings = {}
    for sheet_name in sheet_names:
        mapping_path = _find_mapping_file(base_dir, bom_category, sheet_name)
        if mapping_path is None:
            if DEBUG:
                print(f"[DEBUG] BOM mapping file not found for {sheet_name}")
        mappings[sheet_name] = _parse_mapping_csv(mapping_path)
    partlist_data = []
    if Path(partlist_csv_path).exists():
        with open(partlist_csv_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            partlist_data = list(reader)

    article_map = {}
    if article_list_csv_path and Path(article_list_csv_path).exists():
        with open(article_list_csv_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                article_map[row.get('artnr', '').strip()] = row

    # Build unique stulinr list from partlist data
    unique_stulinr = []
    stuecklisten_set = set()
    for row in partlist_data:
        stulinr = row.get('stulinr', '').strip()
        if stulinr and stulinr not in stuecklisten_set:
            unique_stulinr.append(stulinr)
            stuecklisten_set.add(stulinr)

    def write_sheet(sheet_name, rows):
        if not mappings.get(sheet_name):
            return
        output_paths = [sheets_output_dir / f"{sheet_name}_cache.csv"]
        sheet_aliases = {
            'Stücklistenvarianten': ['StuecklisteVarianten'],
            'Stücklstenauswahlvarianten': ['StuecklisteAuswahlVarianten'],
        }
        for alias_name in sheet_aliases.get(sheet_name, []):
            alias_path = sheets_output_dir / f"{alias_name}_cache.csv"
            if alias_path not in output_paths:
                output_paths.append(alias_path)
        fieldnames = [m['columnname'] for m in mappings.get(sheet_name, [])]
        for output_path in output_paths:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
                writer.writeheader()
                for row in rows:
                    writer.writerow({col: row.get(col, '') for col in fieldnames})

    # --- Build Stücklisten ---
    stuecklisten_rows = []
    for stulinr in unique_stulinr:
        context = {
            'sheet_name': 'Stücklisten',
            'stulinr': stulinr,
            'root_module_artnr': unique_stulinr[0] if unique_stulinr else None,
            '_get_entry_cached': _get_entry_cached,
        }
        row = {}
        for mapping in mappings.get('Stücklisten', []):
            col = mapping['columnname']
            row[col] = _evaluate_bom_mapping(mapping, context)
        stuecklisten_rows.append(row)
    write_sheet('Stücklisten', stuecklisten_rows)

    # --- Build Stücklistenversionen ---
    for stulinr in unique_stulinr:
        version_num = '1'
        key = (stulinr, version_num)
        if key in versionen_set:
            continue
        context = {
            'sheet_name': 'Stücklistenversionen',
            'stulinr': stulinr,
            'version_num': version_num,
            'root_module_artnr': unique_stulinr[0] if unique_stulinr else None,
            '_get_entry_cached': _get_entry_cached,
        }
        row = {}
        for mapping in mappings.get('Stücklistenversionen', []):
            func = (mapping.get('function') or '').strip()
            arglist = mapping.get('arglist', [])
            if not func and arglist and arglist[0] in ('artnr', 'stulinr', 'posnr', 'menge'):
                row[mapping['columnname']] = context.get(arglist[0], '')
            else:
                row[mapping['columnname']] = _evaluate_bom_mapping(mapping, context)
        stuecklisten_versionen_rows.append(row)
        versionen_set.add(key)
    write_sheet('Stücklistenversionen', stuecklisten_versionen_rows)

    # --- Build Stücklistenpositionen ---
    stuecklisten_positionen_rows = []
    existing_positions = set()
    for prow in partlist_data:
        stulinr = prow.get('stulinr', '').strip()
        version_num = '1'
        normalized_posnr = _normalize_posnr_4(prow.get('posnr', '').strip())
        key = (stulinr, version_num, normalized_posnr)
        if key in existing_positions:
            continue
        existing_positions.add(key)
        context = {
            'sheet_name': 'Stücklistenpositionen',
            'stulinr': stulinr,
            'version_num': version_num,
            'artnr': prow.get('artnr', '').strip(),
            'posnr': normalized_posnr,
            'menge': prow.get('menge', '').strip(),
            'partlist_row': prow,
            'partlist_data': partlist_data,
            'root_module_artnr': unique_stulinr[0] if unique_stulinr else None,
            '_get_entry_cached': _get_entry_cached,
        }
        row = {}
        for mapping in mappings.get('Stücklistenpositionen', []):
            col = mapping['columnname']
            value = _evaluate_bom_mapping(mapping, context)
            if value == '' and col in {'Stücklistennummer', 'Versionsnummer', 'Positionsnummer', 'Artikelnummer', 'Menge'}:
                if col == 'Stücklistennummer':
                    value = stulinr
                elif col == 'Versionsnummer':
                    value = version_num
                elif col == 'Positionsnummer':
                    value = normalized_posnr
                elif col == 'Artikelnummer':
                    value = prow.get('artnr', '').strip()
                elif col == 'Menge':
                    value = prow.get('menge', '').strip()
            if col in {'StuecklistePositionsNr', 'Positionsnummer'}:
                value = _normalize_posnr_4(value)
            row[col] = value
        stuecklisten_positionen_rows.append(row)
    write_sheet('Stücklistenpositionen', stuecklisten_positionen_rows)

    # --- Build Stücklistenvarianten ---
    stuecklisten_varianten_rows = []
    varianten_set = set()
    for stulinr in unique_stulinr:
        version_num = '1'
        key = (stulinr, version_num)
        if key in varianten_set:
            continue
        context = {
            'sheet_name': 'Stücklistenvarianten',
            'stulinr': stulinr,
            'version_num': version_num,
            'root_module_artnr': unique_stulinr[0] if unique_stulinr else None,
            '_get_entry_cached': _get_entry_cached,
        }
        row = {}
        for mapping in mappings.get('Stücklistenvarianten', []):
            col = mapping['columnname']
            row[col] = _evaluate_bom_mapping(mapping, context)
        stuecklisten_varianten_rows.append(row)
        varianten_set.add(key)
    write_sheet('Stücklistenvarianten', stuecklisten_varianten_rows)

    # --- Build Auswahlvarianten ---
    auswahlvarianten_rows = []
    auswahlvarianten_set = set()
    for stulinr in unique_stulinr:
        version_num = '1'
        variant_num = '1'
        key = (stulinr, version_num, variant_num)
        if key in auswahlvarianten_set:
            continue
        context = {
            'sheet_name': 'Stücklstenauswahlvarianten',
            'stulinr': stulinr,
            'version_num': version_num,
            'variant_num': variant_num,
            'root_module_artnr': unique_stulinr[0] if unique_stulinr else None,
            '_get_entry_cached': _get_entry_cached,
        }
        row = {}
        for mapping in mappings.get('Stücklstenauswahlvarianten', []):
            col = mapping['columnname']
            row[col] = _evaluate_bom_mapping(mapping, context)
        auswahlvarianten_rows.append(row)
        auswahlvarianten_set.add(key)
    write_sheet('Stücklstenauswahlvarianten', auswahlvarianten_rows)

    if DEBUG:
        print(f"[DEBUG] Generated BOM sheets: {len(unique_stulinr)} stücklisten, {len(versionen_set)} versionen, {len(partlist_data)} positionen")

    return {
        'status': 'ok',
        'stuecklisten_count': len(unique_stulinr),
        'versionen_count': len(versionen_set),
        'positionen_count': len(partlist_data),
    }

def getDocPath(zeichnungsnummer, zeichnungsindex=None, tree_path=None):
    """
    Search for a file in the Drawings tree that matches the exact zeichnungsnummer and (if given) zeichnungsindex.
    Returns (full_path, filename) if found, else (None, None).
    """
    import re
    if not tree_path:
        tree_path = BASE_DIR / "data" / "raw" / "Drawings_tree" / "tree_Eigenprodukte_Jost_Artikel.txt"
    zeichnungsnummer = str(zeichnungsnummer).strip()
    zeichnungsindex = str(zeichnungsindex).strip() if zeichnungsindex else None
    found_path = None
    found_filename = None

    def _normalize_code_part(value):
        # Normalize drawing code tokens for strict equality checks.
        if not value:
            return ""
        value = str(value).strip()
        if value in {"-", "--"}:
            return ""
        value = re.sub(r"\s+", " ", value)
        value = value.rstrip("-").strip()
        return value

    expected_code = _normalize_code_part(zeichnungsnummer)
    if zeichnungsindex and _normalize_code_part(zeichnungsindex):
        expected_code = _normalize_code_part(f"{expected_code} {zeichnungsindex}")

    def _read_text_with_fallback(path):
        raw = Path(path).read_bytes()
        encodings = ["utf-8-sig", "utf-8", "cp1252", "cp850", "latin1"]
        for encoding in encodings:
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("latin1", errors="replace")

    tree_text = _read_text_with_fallback(tree_path)
    current_dir = []
    for line in tree_text.splitlines():
        line = line.rstrip("\r\n")
        if not line.strip() or line.strip().startswith("Auflistung"):
            continue

        # Directory line: preserve only the real ancestor chain for this depth.
        dir_match = re.match(r"^(.*?)(\+---)(.*)$", line)
        if dir_match:
            prefix = dir_match.group(1)
            item_name = dir_match.group(3).strip()
            depth = len(prefix) // 4
            if item_name:
                current_dir = current_dir[:depth]
                current_dir.append(item_name)
            continue

        # File line: use the current directory stack built from the tree.
        filename = re.sub(r"^[^\w]+", "", line).strip()
        if not filename.lower().endswith(".pdf"):
            continue
        # Extract drawing code from the beginning of filename (before description)
        # and compare strictly with expected drawing number(+index).
        doc_code_match = re.match(r"^\s*([0-9A-Za-z]+(?:\s+[0-9A-Za-z]+)*)\s*-?", filename)
        if not doc_code_match:
            continue
        doc_code = _normalize_code_part(doc_code_match.group(1))
        if doc_code != expected_code:
            continue
        path_parts = [p for p in current_dir if p]
        full_path = os.path.join(*path_parts, filename) if path_parts else filename
        found_path = full_path
        found_filename = filename
        break
    return found_path, found_filename


def build_docs_download_cache_csv(article_list_path=None, output_csv_path=None, articles=None):
    """
    Build DMSDocuments cache CSV for download flows.
    Output columns follow the Docs mapping convention and are written as semicolon-separated UTF-8 CSV.
    Returns {'output_path': str, 'rows_written': int}.
    """
    if output_csv_path is None:
        output_csv_path = sheets_output_dir / "DMSDocuments.csv"
    else:
        output_csv_path = Path(output_csv_path)

    if articles is None:
        if not article_list_path:
            raise ValueError("article_list_path is required when articles are not provided")
        with open(article_list_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=';')
            articles = list(reader)

    fieldnames = [
        "Artikelnummer",
        "Identifikation",
        "DMSDocId",
        "Bezeichnung",
        "Kategorie",
        "Dokumenten Speicherort",
        "Gleiches Dokument ersetzen",
        "Als Verknüpfung importieren",
        "Organisationseinheit",
    ]

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    seen = set()
    rows_written = 0
    with open(output_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()

        for article in (articles or []):
            artnr = str(article.get("artnr", "") or "").strip()
            zeichnr = str(
                article.get("zeichnr")
                or article.get("zeichnungsnummer")
                or article.get("zeichr")
                or ""
            ).strip()
            zeichindex = str(
                article.get("zeichnungsindex")
                or article.get("zeichindex")
                or article.get("zeichnrindex")
                or ""
            ).strip()
            if zeichindex in {"-", "--"}:
                zeichindex = ""

            if not artnr or not zeichnr:
                continue

            doc_path, doc_filename = getDocPath(zeichnr, zeichindex)
            if not doc_path and not doc_filename:
                continue

            # Prefer a clean filename stem for the Bezeichnung column.
            doc_label = str(doc_filename or "").strip()
            if doc_label.lower().endswith(".pdf"):
                doc_label = doc_label[:-4].rstrip()
            if not doc_label:
                doc_label = str(article.get("description") or article.get("artbez1") or "").strip()


            # Identifikation must always be empty
            identifier = ""

            dedupe_key = (artnr, str(doc_filename or "").strip(), str(doc_path or "").strip())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            # Use the tree-derived relative path directly; getDocPath now returns the correct ancestor chain.
            base_doc_path = "T:/01 Jost AG/05 Produktion/11 Eigenprodukte Jost/"
            relative_doc_path = str(doc_path or "").replace("\\", "/").strip("/")
            if relative_doc_path:
                full_doc_path = base_doc_path.rstrip("/") + "/" + relative_doc_path
            else:
                full_doc_path = base_doc_path.rstrip("/")
            full_doc_path = full_doc_path.replace("\\", "/").replace("//", "/")

            writer.writerow({
                "Artikelnummer": artnr,
                "Identifikation": identifier,
                "DMSDocId": "",
                "Bezeichnung": doc_label,
                "Kategorie": "11",
                "Dokumenten Speicherort": full_doc_path,
                "Gleiches Dokument ersetzen": "0",
                "Als Verknüpfung importieren": "1",
                "Organisationseinheit": "JOS",
            })
            rows_written += 1

    return {
        "output_path": str(output_csv_path),
        "rows_written": rows_written,
    }

