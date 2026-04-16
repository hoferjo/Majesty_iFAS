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
	def __init__(self, name: str, group: str, value: Any = None, editable: bool = True) -> None:
		self.name: str = name
		self.group: str = group  # 'input', 'derivative', 'default', 'empty'
		self.value: Any = value
		self.editable: bool = editable

	def as_dict(self) -> Dict[str, Any]:
		return {
			"name": self.name,
			"group": self.group,
			"value": self.value,
			"editable": self.editable,
		}

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

	def get_template(self, name: str) -> Optional[ArticleTemplate]:
		"""
		Get a template by name.
		Args:
			name (str): Template name.
		Returns:
			Optional[ArticleTemplate]: The template or None if not found.
		"""
		return self.templates.get(name)

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
		derivatives: Optional[Dict[str, Any]] = None
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
