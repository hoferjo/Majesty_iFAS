# Article/Module creation logic for iFAS
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

class FieldGroup:
	"""
	Represents a field and its group: input, derivative, default, or empty.
	"""
	def __init__(self, name: str, group: str, value: Any = None, editable: bool = True):
		self.name = name
		self.group = group  # 'input', 'derivative', 'default', 'empty'
		self.value = value
		self.editable = editable

	def as_dict(self):
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
	def __init__(self, name: str, fields: List[FieldGroup]):
		self.name = name
		self.fields = fields

	def as_dict(self):
		return {
			"name": self.name,
			"fields": [f.as_dict() for f in self.fields],
		}

class ArticleCreator:
	"""
	Main logic for creating articles/modules with field grouping and templates.
	"""
	def __init__(self, config_dir: Path):
		self.config_dir = config_dir
		self.templates = self._load_templates()

	def _load_templates(self) -> Dict[str, ArticleTemplate]:
		templates = {}
		templates_path = self.config_dir / "article_templates.yaml"
		if templates_path.exists():
			with open(templates_path, "r", encoding="utf-8") as f:
				data = yaml.safe_load(f) or {}
			for name, fields in data.items():
				field_objs = [FieldGroup(**fld) for fld in fields]
				templates[name] = ArticleTemplate(name, field_objs)
		# Add built-in types if needed
		return templates

	def get_template(self, name: str) -> Optional[ArticleTemplate]:
		return self.templates.get(name)

	def list_templates(self) -> List[str]:
		return list(self.templates.keys())

	def create_article(self, template_name: str, input_data: Dict[str, Any], derivatives: Dict[str, Any] = None) -> Dict[str, Any]:
		"""
		Create an article/module dict, filling fields by input, derivative, default, or empty.
		"""
		template = self.get_template(template_name)
		if not template:
			raise ValueError(f"Template '{template_name}' not found.")
		result = {}
		for field in template.fields:
			if field.group == 'input' and field.name in input_data:
				result[field.name] = input_data[field.name]
			elif field.group == 'derivative' and derivatives and field.name in derivatives:
				result[field.name] = derivatives[field.name]
			elif field.group == 'default' and field.value is not None:
				result[field.name] = field.value
			else:
				result[field.name] = None
		return result

	def save_article_cache(self, article: Dict[str, Any], cache_path: Path):
		"""
		Save article/module to cache (CSV or YAML, compatible with transform flow).
		"""
		# For now, save as YAML for clarity; can be adapted to CSV as needed
		cache_path.parent.mkdir(parents=True, exist_ok=True)
		with open(cache_path, "w", encoding="utf-8") as f:
			yaml.safe_dump(article, f, allow_unicode=True)

	def add_template(self, name: str, fields: List[Dict[str, Any]]):
		"""
		Add a new template (type/subtype) from user input.
		"""
		self.templates[name] = ArticleTemplate(name, [FieldGroup(**fld) for fld in fields])
		self._save_templates()

	def _save_templates(self):
		templates_path = self.config_dir / "article_templates.yaml"
		data = {name: [f.as_dict() for f in tpl.fields] for name, tpl in self.templates.items()}
		with open(templates_path, "w", encoding="utf-8") as f:
			yaml.safe_dump(data, f, allow_unicode=True)

# Example usage (to be called from FastAPI endpoints):
# creator = ArticleCreator(Path("config"))
# creator.create_article("Verkaufsartikel", {"artnr": "1001"}, {"artbez1": "Derived Name"})
