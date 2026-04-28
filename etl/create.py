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
	def __init__(self, name: str, group: str, value: Any = None, editable: bool = True, options: Optional[List[str]] = None, search_query: Optional[str] = None) -> None:
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

# Example usage (to be called from FastAPI endpoints):
# creator = ArticleCreator(Path("config"))
# article = creator.create_article("Verkaufsartikel", {"artnr": "1001"}, {"artbez1": "Derived Name"})
# creator.save_article_cache(article, Path("data/processed/cache/article.yaml"))
