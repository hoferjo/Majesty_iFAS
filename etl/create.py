# Article/Module creation logic for iFAS
import yaml
import csv
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

class FieldGroup:
	"""
	Represents a field and its group: input, derivative, default, or empty.
	"""
	def __init__(self, name: str, group: str, value: Any = None, editable: bool = True, options: Optional[List[Any]] = None, search_query: Optional[str] = None) -> None:
		self.name: str = name
		self.group: str = group  # 'input', 'derivative', 'default', 'empty'
		self.value: Any = value
		self.editable: bool = editable
		self.options: Optional[List[str]] = options
		self.search_query: Optional[str] = search_query

	def as_dict(self) -> Dict[str, Any]:
		result = {
			"name": self.name,
			"group": self.group,
			"value": self.value,
			"editable": self.editable,
		}
		if self.options is not None:
			result["options"] = self.options
		if self.search_query is not None:
			result["search_query"] = self.search_query
		return result

class ArticleTemplate:
	"""
	Represents a type/subtype template for articles or modules.
	"""
	def __init__(self, name: str, fields: List[FieldGroup]) -> None:
		self.name: str = name
		self.fields: List[FieldGroup] = fields

	def as_dict(self) -> Dict[str, Any]:
		return {
			"name": self.name,
			"fields": [f.as_dict() for f in self.fields],
		}

class ArticleCreator:
	"""
	Main logic for creating articles/modules with field grouping and templates.
	"""

	def __init__(self, config_dir: Path) -> None:
		"""
		Initialize the ArticleCreator.
		Args:
			config_dir (Path): Path to the configuration directory.
		"""
		self.config_dir: Path = config_dir
		logging.basicConfig(level=logging.INFO)
		self.logger = logging.getLogger(__name__)
		self.templates: Dict[str, ArticleTemplate] = self._load_templates()
		self.struktur: Dict[str, Any] = self._load_struktur()
		self.group_defaults: Dict[str, Dict[str, Any]] = self._load_group_defaults()

	def _load_templates(self) -> Dict[str, ArticleTemplate]:
		"""
		Load article templates from YAML file.
		Returns:
			Dict[str, ArticleTemplate]: Loaded templates.
		"""
		templates: Dict[str, ArticleTemplate] = {}
		templates_path = self.config_dir / "article_templates.yaml"
		try:
			if templates_path.exists():
				with open(templates_path, "r", encoding="utf-8") as f:
					data = yaml.safe_load(f) or {}
				for name, fields in data.items():
					field_objs = [FieldGroup(**fld) for fld in fields]
					templates[name] = ArticleTemplate(name, field_objs)
				self.logger.info(f"Loaded {len(templates)} templates from {templates_path}.")
			else:
				self.logger.warning(f"Template file {templates_path} does not exist.")
		except Exception as e:
			self.logger.error(f"Error loading templates: {e}")
		# Add built-in types if needed
		return templates

	def _load_struktur(self) -> Dict[str, Any]:
		"""
		Load hierarchy structure from Struktur.yaml.
		Returns:
			Dict[str, Any]: Structure with classes and their hierarchies.
		"""
		struktur_path = self.config_dir / "Struktur.yaml"
		try:
			if struktur_path.exists():
				with open(struktur_path, "r", encoding="utf-8") as f:
					data = yaml.safe_load(f) or {}
				self.logger.info(f"Loaded structure from {struktur_path}.")
				return data
			else:
				self.logger.warning(f"Struktur file {struktur_path} does not exist.")
		except Exception as e:
			self.logger.error(f"Error loading structure: {e}")
		return {}

	def _load_group_defaults(self) -> Dict[str, Dict[str, Any]]:
		"""
		Load group-specific field defaults from create_defaults.yaml.
		Returns:
			Dict[str, Dict[str, Any]]: Group defaults for field overrides.
		"""
		defaults_path = self.config_dir / "create_defaults.yaml"
		try:
			if defaults_path.exists():
				with open(defaults_path, "r", encoding="utf-8") as f:
					data = yaml.safe_load(f) or {}
				self.logger.info(f"Loaded group defaults from {defaults_path}.")
				return data
			else:
				self.logger.info(f"No create_defaults.yaml found at {defaults_path}.")
		except Exception as e:
			self.logger.error(f"Error loading group defaults: {e}")
		return {}

	def get_template(self, name: str) -> Optional[ArticleTemplate]:
		"""
		Get a template by name. Falls back to 'fallback:mapping' if not found.
		Args:
			name (str): Template name.
		Returns:
			Optional[ArticleTemplate]: The template or fallback, or None if neither exists.
		"""
		if name in self.templates:
			return self.templates[name]
		# Fallback to 'fallback:mapping' if specific template not found
		if "fallback:mapping" in self.templates:
			return self.templates["fallback:mapping"]
		return None

	def get_classes(self) -> List[str]:
		"""
		Get list of top-level classes from structure.
		Returns:
			List[str]: Class names (e.g., ['Produkt', 'Service'])
		"""
		if "classes" in self.struktur:
			classes = self.struktur["classes"]
			if isinstance(classes, str):
				return [c.strip() for c in classes.split('\n') if c.strip()]
			elif isinstance(classes, list):
				return [c.strip() for c in classes if c and isinstance(c, str)]
		return []

	def get_groups_for_class(self, class_name: str) -> List[str]:
		"""
		Get article groups available for a given class.
		Args:
			class_name (str): Class name (e.g., 'Produkt', 'Service')
		Returns:
			List[str]: List of group names
		"""
		if class_name not in self.struktur:
			return []
		groups = self.struktur[class_name]
		if isinstance(groups, str):
			return [g.strip() for g in groups.split('\n') if g.strip()]
		elif isinstance(groups, list):
			return [g.strip() for g in groups if g and isinstance(g, str)]
		return []

	def get_types_for_group(self, group_name: str) -> List[str]:
		"""
		Get article types available for a given group.
		Args:
			group_name (str): Group name (e.g., 'Teileartikel')
		Returns:
			List[str]: List of type names
		"""
		if group_name not in self.struktur:
			return []
		types_data = self.struktur[group_name]
		if isinstance(types_data, str):
			return [t.strip() for t in types_data.split('\n') if t.strip()]
		elif isinstance(types_data, list):
			return [t.strip() for t in types_data if t and isinstance(t, str)]
		return []

	def get_allowed_children(self, parent_type: str) -> List[str]:
		"""
		Get allowed child types for a parent article type.
		Args:
			parent_type (str): Parent article type
		Returns:
			List[str]: List of allowed child types
		"""
		if parent_type not in self.struktur:
			return []
		children = self.struktur[parent_type]
		if isinstance(children, str):
			return [c.strip() for c in children.split('\n') if c.strip()]
		elif isinstance(children, list):
			return [c.strip() for c in children if c and isinstance(c, str)]
		return []

	def get_group_defaults(self, group_name: str) -> Dict[str, Any]:
		"""
		Get field defaults for a specific group.
		Args:
			group_name (str): Group name
		Returns:
			Dict[str, Any]: Default field values for the group
		"""
		return self.group_defaults.get(group_name, {})

	def merge_defaults(self, group_name: str, template: ArticleTemplate) -> ArticleTemplate:
		"""
		Merge group-specific defaults with template fields.
		Group defaults override template defaults.
		Args:
			group_name (str): Group name to get defaults from
			template (ArticleTemplate): Original template
		Returns:
			ArticleTemplate: New template with merged defaults
		"""
		group_defaults = self.get_group_defaults(group_name)
		if not group_defaults:
			return template

		existing_fields = {field.name: field for field in template.fields}
		merged_fields = []
		for field in template.fields:
			default_match = next((item for item in group_defaults if item.get("name") == field.name), None)
			if default_match is not None:
				merged_fields.append(FieldGroup(**default_match))
			else:
				merged_fields.append(field)

		for default_field in group_defaults:
			field_name = default_field.get("name")
			if field_name and field_name not in existing_fields:
				merged_fields.append(FieldGroup(**default_field))

		return ArticleTemplate(template.name, merged_fields)

	def list_templates(self) -> List[str]:
		"""
		List all available template names.
		Returns:
			List[str]: List of template names.
		"""
		return list(self.templates.keys())

	def create_article(
		self,
		template_name: str,
		input_data: Dict[str, Any],
		derivatives: Optional[Dict[str, Any]] = None,
		template: Optional[ArticleTemplate] = None,
	) -> Dict[str, Any]:
		"""
		Create an article/module dict, filling fields by input, derivative, default, or empty.
		Args:
			template_name (str): Name of the template to use.
			input_data (Dict[str, Any]): Input data for 'input' fields.
			derivatives (Optional[Dict[str, Any]]): Data for 'derivative' fields.
		Returns:
			Dict[str, Any]: The created article/module.
		Raises:
			ValueError: If template is not found or input validation fails.
		"""
		if template is None:
			template = self.get_template(template_name)
		if not template:
			self.logger.error(f"Template '{template_name}' not found.")
			raise ValueError(f"Template '{template_name}' not found.")
		# Validate input_data keys
		input_field_names = {f.name for f in template.fields if f.group == 'input'}
		missing_fields = input_field_names - set(input_data.keys())
		if missing_fields:
			self.logger.warning(f"Missing input fields: {missing_fields}")
		result: Dict[str, Any] = {}
		for field in template.fields:
			if field.group == 'input' and field.name in input_data:
				result[field.name] = input_data[field.name]
			elif field.group == 'derivative' and derivatives and field.name in derivatives:
				result[field.name] = derivatives[field.name]
			elif field.group == 'default' and field.value is not None:
				result[field.name] = field.value
			else:
				result[field.name] = None
		self.logger.info(f"Created article for template '{template_name}'.")
		return result

	def save_article_cache(self, article: Dict[str, Any], cache_path: Path) -> None:
		"""
		Save article/module to cache (YAML or CSV, compatible with transform flow).
		Args:
			article (Dict[str, Any]): The article/module data.
			cache_path (Path): Path to save the cache file.
		"""
		cache_path.parent.mkdir(parents=True, exist_ok=True)
		try:
			if cache_path.suffix.lower() == ".csv":
				with open(cache_path, "w", encoding="utf-8", newline="") as f:
					writer = csv.DictWriter(f, fieldnames=article.keys())
					writer.writeheader()
					writer.writerow(article)
				self.logger.info(f"Article saved as CSV to {cache_path}.")
			else:
				with open(cache_path, "w", encoding="utf-8") as f:
					yaml.safe_dump(article, f, allow_unicode=True)
				self.logger.info(f"Article saved as YAML to {cache_path}.")
		except Exception as e:
			self.logger.error(f"Error saving article cache: {e}")

	def add_template(self, name: str, fields: List[Dict[str, Any]]) -> None:
		"""
		Add a new template (type/subtype) from user input.
		Args:
			name (str): Template name.
			fields (List[Dict[str, Any]]): List of field definitions.
		"""
		self.templates[name] = ArticleTemplate(name, [FieldGroup(**fld) for fld in fields])
		self._save_templates()
		self.logger.info(f"Added new template '{name}'.")

	def _save_templates(self) -> None:
		"""
		Save all templates to the YAML file.
		"""
		templates_path = self.config_dir / "article_templates.yaml"
		data = {name: [f.as_dict() for f in tpl.fields] for name, tpl in self.templates.items()}
		try:
			with open(templates_path, "w", encoding="utf-8") as f:
				yaml.safe_dump(data, f, allow_unicode=True)
			self.logger.info(f"Templates saved to {templates_path}.")
		except Exception as e:
			self.logger.error(f"Error saving templates: {e}")

def create_from_drawingtree(tree_file_path: Union[str, Path], output_csv_path: Union[str, Path], folder_filter: Optional[str] = None) -> None:
	"""
	Parse a drawing tree file and extract a list of drawings to CSV.
	
	Args:
		tree_file_path (Union[str, Path]): Path to the tree file to read.
		output_csv_path (Union[str, Path]): Path to save the generated CSV file.
		folder_filter (Optional[str]): If provided, only include drawings from this folder (matches category or subcategory).
	
	The CSV will contain columns:
		- drawing_number: Extracted drawing number (e.g., "002 006 13a")
		- description: Description from filename (e.g., "Baugrp Gestell (Spontis)")
		- file_extension: File extension (e.g., "pdf", "stp")
		- file_name: Full filename
		- category: Top-level folder (e.g., "001 Normteile Jost AG")
		- subcategory: Second-level folder
		- folder_path: Full hierarchical path
	"""
	tree_file_path = Path(tree_file_path)
	output_csv_path = Path(output_csv_path)

	if not tree_file_path.exists():
		logging.error(f"Tree file not found: {tree_file_path}")
		raise FileNotFoundError(f"Tree file not found: {tree_file_path}")

	def _strip_tree_prefix(value: str) -> str:
		# Remove leading tree drawing characters copied from DOS tree output.
		import re
		return re.sub(r"^[\s│├└─+¦]+", "", value)

	def _index_weight(index_token: str) -> int:
		if not index_token or index_token == "-":
			return 0
		ch = index_token.lower()
		if len(ch) == 1 and "a" <= ch <= "z":
			return ord(ch) - ord("a") + 1
		return 0

	def _parse_drawing_stem(stem: str) -> Optional[Dict[str, str]]:
		# Parse: <digits and spaces><optional index letter or '-'><optional separator><description>
		if not stem:
			return None
		i = 0
		while i < len(stem) and (stem[i].isdigit() or stem[i] == " "):
			i += 1
		base_number = stem[:i].strip()
		if not base_number:
			return None

		index_token = "-"
		if i < len(stem) and (stem[i].isalpha() or stem[i] == "-"):
			index_token = stem[i].lower() if stem[i].isalpha() else "-"
			i += 1

		remainder = stem[i:].lstrip(" -")
		return {
			"base_number": base_number,
			"index": index_token,
			"description": remainder.strip(),
		}

	best_by_base: Dict[str, Any] = {}
	folder_stack: List[str] = []

	try:
		with open(tree_file_path, "r", encoding="utf-8", errors="ignore") as f:
			lines = f.readlines()

		for line in lines:
			if not line.strip():
				continue

			raw = line.rstrip("\n")

			# Folder lines are denoted by +--- in tree output.
			if "+---" in raw:
				prefix, tail = raw.split("+---", 1)
				folder_name = _strip_tree_prefix(tail).strip()
				if not folder_name:
					continue

				depth = prefix.count("│") + prefix.count("¦")
				if len(folder_stack) <= depth:
					folder_stack.extend([""] * (depth - len(folder_stack) + 1))
				folder_stack[depth] = folder_name
				folder_stack = folder_stack[: depth + 1]
				continue

			file_text = _strip_tree_prefix(raw).strip()
			if not file_text:
				continue

			low = file_text.lower()
			if "acad.err" in low or "t:." in low:
				continue

			# Only PDFs are relevant for the article list from tree.
			if not low.endswith(".pdf"):
				continue

			stem = file_text[:-4].strip()
			parsed = _parse_drawing_stem(stem)
			if not parsed:
				continue

			category = folder_stack[0] if len(folder_stack) > 0 else ""
			subcategory = folder_stack[1] if len(folder_stack) > 1 else ""
			folder_path = "/".join([p for p in folder_stack if p])

			if folder_filter:
				folder_filter_lower = folder_filter.lower()
				if not (
					folder_filter_lower in category.lower()
					or folder_filter_lower in subcategory.lower()
					or folder_filter_lower in folder_path.lower()
				):
					continue

			record = {
				"drawing_number": parsed["base_number"],
				"index": parsed["index"],
				"description": parsed["description"],
				"file_extension": "pdf",
				"file_name": file_text,
				"category": category,
				"subcategory": subcategory,
				"folder_path": folder_path,
			}

			key = parsed["base_number"]
			weight = _index_weight(parsed["index"])
			if key not in best_by_base or weight > best_by_base[key][0]:
				best_by_base[key] = (weight, record)

		final_drawings = [item[1] for item in best_by_base.values()]
		output_csv_path.parent.mkdir(parents=True, exist_ok=True)

		if final_drawings:
			fieldnames = ["drawing_number", "index", "description", "file_extension", "file_name", "category", "subcategory", "folder_path"]
			with open(output_csv_path, "w", encoding="utf-8", newline="") as csvfile:
				writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
				writer.writeheader()
				writer.writerows(final_drawings)
			logging.info(f"Extracted {len(final_drawings)} drawings from tree and saved to {output_csv_path}.")
		else:
			logging.warning(f"No drawings found in tree file {tree_file_path}.")

	except Exception as e:
		logging.error(f"Error processing drawing tree: {e}")
		raise


# Example usage (to be called from FastAPI endpoints):
# creator = ArticleCreator(Path("config"))
# article = creator.create_article("Verkaufsartikel", {"artnr": "1001"}, {"artbez1": "Derived Name"})
# creator.save_article_cache(article, Path("data/processed/cache/article.yaml"))
#
def add_unique_artnr(tree_csv_path: Union[str, Path], out_unique_csv: Union[str, Path], existing_mode: str = "PROD") -> int:
	"""
	For each drawing in `tree_csv_path` that is not already present in existing articles,
	determine an `artnr` from the artikelstamm `zeichnr` mapping; if not available,
	use generate_article_number() from Nummer_vergeben.py to find the next free number.

	Writes `drawing_number;index;artnr` rows to `out_unique_csv` and returns number written.
	"""
	from etl.Nummer_vergeben import generate_article_number
	
	tree_csv_path = Path(tree_csv_path)
	out_unique_csv = Path(out_unique_csv)
	base = Path(__file__).resolve().parent.parent
	
	# load tree rows (auto-detect delimiter)
	if not tree_csv_path.exists():
		raise FileNotFoundError(f"Tree CSV not found: {tree_csv_path}")

	def _detect_delim(path: Path) -> str:
		with open(path, "r", encoding="utf-8-sig") as f:
			first = f.readline()
			if ";" in first:
				return ";"
			if "," in first:
				return ","
			return ";"

	delim = _detect_delim(tree_csv_path)
	rows = []
	with open(tree_csv_path, "r", encoding="utf-8-sig") as f:
		reader = csv.DictReader(f, delimiter=delim)
		for r in reader:
			rows.append(r)

	# load existing zeichnr from PROD and TEST (to skip already-present drawings)
	existing_zeich = set()
	for mode in ["PROD", "TEST"]:
		existing_path = base / "data" / "processed" / "cache" / "existing" / f"existingArticles{mode}.csv"
		if existing_path.exists():
			# try comma first (existing articles use comma), then semicolon
			for d in (",", ";"):
				try:
					with open(existing_path, "r", encoding="utf-8-sig") as f:
						reader = csv.DictReader(f, delimiter=d)
						for r in reader:
							zn = (r.get("zeichnr") or r.get("zeichnungsnummer") or "").strip()
							if zn:
								existing_zeich.add(zn)
					break
				except Exception:
					continue

	# find and load artikelstamm file (latest majesty file)
	artikelstamm_dir = base / "data" / "raw" / "artikelstamm"
	artikelstamm_file = None
	if artikelstamm_dir.exists():
		cand = sorted(artikelstamm_dir.glob("artikelstamm_majesty_*.csv"), reverse=True)
		if cand:
			artikelstamm_file = cand[0]

	# load artikelstamm mapping zeichnr -> artnr
	zeich_to_art = {}
	if artikelstamm_file and artikelstamm_file.exists():
		with open(artikelstamm_file, "r", encoding="utf-8-sig") as f:
			reader = csv.DictReader(f, delimiter=';')
			for r in reader:
				artnr = (r.get("artnr") or "").strip()
				zn = (r.get("zeichnr") or "").strip()
				if zn and artnr:
					zeich_to_art[zn] = artnr

	# load nummernvergabe mapping for prefix -> XX.YY prefix conversion
	nr_map = {}
	nr_path = base / "config" / "nummernvergabe.csv"
	if nr_path.exists():
		with open(nr_path, "r", encoding="utf-8-sig") as f:
			reader = csv.reader(f, delimiter=';')
			for r in reader:
				if not r:
					continue
				key = str(r[0]).strip()
				val = str(r[1]).strip() if len(r) > 1 else ""
				if key:
					nr_map[key] = val

	# helper to extract 3-digit prefix from drawing number
	import re
	def _drawing_prefix(drawing: str) -> str:
		m = re.search(r"(\d{3})", drawing)
		return m.group(1) if m else ""

	def _choose_mapping(prefix: str) -> Optional[str]:
		if not prefix:
			return None
		# exact match first
		if prefix in nr_map:
			return nr_map[prefix]
		# try keys that start with prefix or vice versa
		for k, v in nr_map.items():
			if k.startswith(prefix) or prefix.startswith(k):
				return v
		return None

	# process rows
	out_unique_csv.parent.mkdir(parents=True, exist_ok=True)
	written = 0
	with open(out_unique_csv, "w", encoding="utf-8", newline="") as outf:
		writer = csv.DictWriter(outf, fieldnames=["artnr", "zeichnr", "zeichindex", "description"], delimiter=';')
		writer.writeheader()
		for r in rows:
			drawing = (r.get("drawing_number") or r.get("drawing") or "").strip()
			index = (r.get("index") or "-").strip()
			description = (r.get("description") or "").strip()
			if not drawing:
				continue
			
			# skip if already present in PROD or TEST
			if drawing in existing_zeich:
				continue

			# try artikelstamm lookup first
			art = zeich_to_art.get(drawing)
			if art:
				writer.writerow({"artnr": art, "zeichnr": drawing, "zeichindex": index, "description": description})
				written += 1
				continue

			# generate new number using Nummer_vergeben logic
			prefix = _drawing_prefix(drawing)
			map_pref = _choose_mapping(prefix)
			if map_pref:
				try:
					new_art = generate_article_number(base, map_pref)
					writer.writerow({"artnr": new_art, "zeichnr": drawing, "zeichindex": index, "description": description})
					written += 1
					continue
				except Exception:
					pass

			# fallback: write empty artnr (user can review)
			writer.writerow({"artnr": "", "zeichnr": drawing, "zeichindex": index, "description": description})
			written += 1

	return written

# create_from_drawingtree(
#     Path("data/raw/drawings_tree/tree_Eigenprodukte_Jost_Artikel.txt"),
#     Path("data/processed/article_list_creation_mode.csv")
# )
