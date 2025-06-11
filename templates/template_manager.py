import os
import yaml
import json
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TemplateFormat(str, Enum):
    YAML = "yaml"
    JSON = "json"


class CitationStyle(str, Enum):
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"
    HARVARD = "harvard"
    CUSTOM = "custom"


@dataclass
class SectionTemplate:
    name: str
    title: str
    order: int
    required: bool = True
    content_type: str = "paragraph"
    formatting: Dict[str, Any] = field(default_factory=dict)
    subsections: List['SectionTemplate'] = field(default_factory=list)


@dataclass
class CitationTemplate:
    style: CitationStyle
    format_string: str
    bibliography_format: str
    in_text_format: str
    url_format: str = "{title}. Retrieved from {url}"
    date_format: str = "%Y-%m-%d"


@dataclass
class DocumentTemplate:
    name: str
    description: str
    language: str = "en"
    sections: List[SectionTemplate] = field(default_factory=list)
    citation: Optional[CitationTemplate] = None
    formatting: Dict[str, Any] = field(default_factory=dict)
    metadata_fields: List[str] = field(default_factory=list)


class TemplateManager:
    def __init__(self, templates_dir: str = "./templates"):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(exist_ok=True)
        self.templates: Dict[str, DocumentTemplate] = {}
        self.default_template_name = "default"
        self._load_templates()
    
    def _load_templates(self):
        try:
            self._load_default_templates()
            self._load_custom_templates()
        except Exception as e:
            logger.error(f"Failed to load templates: {str(e)}")
            self._create_fallback_template()
    
    def _load_default_templates(self):
        default_template_path = self.templates_dir / "default_templates.yaml"
        if default_template_path.exists():
            with open(default_template_path, 'r', encoding='utf-8') as f:
                templates_data = yaml.safe_load(f)
                self._parse_templates_data(templates_data)
        else:
            self._create_default_template_file()
    
    def _load_custom_templates(self):
        for template_file in self.templates_dir.glob("*.yaml"):
            if template_file.name != "default_templates.yaml":
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = yaml.safe_load(f)
                        self._parse_template_data(template_data)
                except Exception as e:
                    logger.warning(f"Failed to load template {template_file}: {str(e)}")
        
        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                    self._parse_template_data(template_data)
            except Exception as e:
                logger.warning(f"Failed to load template {template_file}: {str(e)}")
    
    def _parse_templates_data(self, templates_data: Dict[str, Any]):
        for template_name, template_config in templates_data.get("templates", {}).items():
            try:
                template = self._create_template_from_config(template_name, template_config)
                self.templates[template_name] = template
            except Exception as e:
                logger.warning(f"Failed to parse template {template_name}: {str(e)}")
    
    def _parse_template_data(self, template_data: Dict[str, Any]):
        template_name = template_data.get("name", "unnamed")
        try:
            template = self._create_template_from_config(template_name, template_data)
            self.templates[template_name] = template
        except Exception as e:
            logger.warning(f"Failed to parse template {template_name}: {str(e)}")
    
    def _create_template_from_config(self, name: str, config: Dict[str, Any]) -> DocumentTemplate:
        sections = []
        for section_config in config.get("sections", []):
            section = self._create_section_from_config(section_config)
            sections.append(section)
        
        citation_config = config.get("citation", {})
        citation = None
        if citation_config:
            citation = CitationTemplate(
                style=CitationStyle(citation_config.get("style", "apa")),
                format_string=citation_config.get("format_string", ""),
                bibliography_format=citation_config.get("bibliography_format", ""),
                in_text_format=citation_config.get("in_text_format", ""),
                url_format=citation_config.get("url_format", "{title}. Retrieved from {url}"),
                date_format=citation_config.get("date_format", "%Y-%m-%d")
            )
        
        return DocumentTemplate(
            name=name,
            description=config.get("description", ""),
            language=config.get("language", "en"),
            sections=sections,
            citation=citation,
            formatting=config.get("formatting", {}),
            metadata_fields=config.get("metadata_fields", [])
        )
    
    def _create_section_from_config(self, config: Dict[str, Any]) -> SectionTemplate:
        subsections = []
        for subsection_config in config.get("subsections", []):
            subsection = self._create_section_from_config(subsection_config)
            subsections.append(subsection)
        
        return SectionTemplate(
            name=config["name"],
            title=config["title"],
            order=config.get("order", 0),
            required=config.get("required", True),
            content_type=config.get("content_type", "paragraph"),
            formatting=config.get("formatting", {}),
            subsections=subsections
        )
    
    def get_template(self, template_name: str) -> Optional[DocumentTemplate]:
        if template_name == "none" or template_name == "auto":
            return None  # Allow LLM to generate freely
        return self.templates.get(template_name)

    def get_default_template(self) -> DocumentTemplate:
        return self.templates.get(self.default_template_name) or self._create_fallback_template()

    def should_use_template(self, template_name: str) -> bool:
        """Check if a template should be applied or if LLM should generate freely"""
        return template_name not in ["none", "auto", ""] and template_name is not None
    
    def list_templates(self) -> List[str]:
        return list(self.templates.keys())
    
    def add_template(self, template: DocumentTemplate) -> bool:
        try:
            self.templates[template.name] = template
            return True
        except Exception as e:
            logger.error(f"Failed to add template {template.name}: {str(e)}")
            return False
    
    def save_template(self, template: DocumentTemplate, format_type: TemplateFormat = TemplateFormat.YAML) -> bool:
        try:
            template_data = self._template_to_dict(template)
            
            if format_type == TemplateFormat.YAML:
                file_path = self.templates_dir / f"{template.name}.yaml"
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(template_data, f, default_flow_style=False, allow_unicode=True)
            else:
                file_path = self.templates_dir / f"{template.name}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(template_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Template {template.name} saved to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save template {template.name}: {str(e)}")
            return False
    
    def _template_to_dict(self, template: DocumentTemplate) -> Dict[str, Any]:
        sections_data = []
        for section in template.sections:
            section_data = self._section_to_dict(section)
            sections_data.append(section_data)
        
        template_data = {
            "name": template.name,
            "description": template.description,
            "language": template.language,
            "sections": sections_data,
            "formatting": template.formatting,
            "metadata_fields": template.metadata_fields
        }
        
        if template.citation:
            template_data["citation"] = {
                "style": template.citation.style.value,
                "format_string": template.citation.format_string,
                "bibliography_format": template.citation.bibliography_format,
                "in_text_format": template.citation.in_text_format,
                "url_format": template.citation.url_format,
                "date_format": template.citation.date_format
            }
        
        return template_data
    
    def _section_to_dict(self, section: SectionTemplate) -> Dict[str, Any]:
        subsections_data = []
        for subsection in section.subsections:
            subsection_data = self._section_to_dict(subsection)
            subsections_data.append(subsection_data)
        
        return {
            "name": section.name,
            "title": section.title,
            "order": section.order,
            "required": section.required,
            "content_type": section.content_type,
            "formatting": section.formatting,
            "subsections": subsections_data
        }
    
    def _create_fallback_template(self) -> DocumentTemplate:
        sections = [
            SectionTemplate("introduction", "Introduction", 1),
            SectionTemplate("methodology", "Methodology", 2),
            SectionTemplate("results", "Results", 3),
            SectionTemplate("discussion", "Discussion", 4),
            SectionTemplate("conclusion", "Conclusion", 5)
        ]

        citation = CitationTemplate(
            style=CitationStyle.APA,
            format_string="{author} ({year}). {title}. {source}.",
            bibliography_format="{author} ({year}). {title}. {source}.",
            in_text_format="({author}, {year})"
        )

        template = DocumentTemplate(
            name="fallback",
            description="Fallback template when no other templates are available",
            sections=sections,
            citation=citation
        )

        self.templates["fallback"] = template
        return template

    def _create_default_template_file(self):
        default_templates = {
            "templates": {
                "default": {
                    "description": "Default research report template",
                    "language": "en",
                    "sections": [
                        {
                            "name": "abstract",
                            "title": "Abstract",
                            "order": 1,
                            "required": False,
                            "content_type": "summary"
                        },
                        {
                            "name": "introduction",
                            "title": "Introduction",
                            "order": 2,
                            "required": True,
                            "content_type": "paragraph"
                        },
                        {
                            "name": "methodology",
                            "title": "Methodology",
                            "order": 3,
                            "required": True,
                            "content_type": "paragraph"
                        },
                        {
                            "name": "findings",
                            "title": "Key Findings",
                            "order": 4,
                            "required": True,
                            "content_type": "list"
                        },
                        {
                            "name": "analysis",
                            "title": "Analysis",
                            "order": 5,
                            "required": True,
                            "content_type": "paragraph"
                        },
                        {
                            "name": "conclusion",
                            "title": "Conclusion",
                            "order": 6,
                            "required": True,
                            "content_type": "paragraph"
                        }
                    ],
                    "citation": {
                        "style": "apa",
                        "format_string": "{author} ({year}). {title}. {source}.",
                        "bibliography_format": "{author} ({year}). {title}. {source}.",
                        "in_text_format": "({author}, {year})",
                        "url_format": "{title}. Retrieved from {url}",
                        "date_format": "%Y-%m-%d"
                    },
                    "formatting": {
                        "title_style": "h1",
                        "section_style": "h2",
                        "subsection_style": "h3",
                        "paragraph_spacing": "double",
                        "citation_style": "numbered"
                    },
                    "metadata_fields": ["date", "author", "query", "sources", "cost"]
                },
                "academic": {
                    "description": "Academic research paper template",
                    "language": "en",
                    "sections": [
                        {
                            "name": "abstract",
                            "title": "Abstract",
                            "order": 1,
                            "required": True,
                            "content_type": "summary"
                        },
                        {
                            "name": "introduction",
                            "title": "Introduction",
                            "order": 2,
                            "required": True,
                            "content_type": "paragraph",
                            "subsections": [
                                {
                                    "name": "background",
                                    "title": "Background",
                                    "order": 1,
                                    "required": True,
                                    "content_type": "paragraph"
                                },
                                {
                                    "name": "objectives",
                                    "title": "Research Objectives",
                                    "order": 2,
                                    "required": True,
                                    "content_type": "list"
                                }
                            ]
                        },
                        {
                            "name": "literature_review",
                            "title": "Literature Review",
                            "order": 3,
                            "required": True,
                            "content_type": "paragraph"
                        },
                        {
                            "name": "methodology",
                            "title": "Methodology",
                            "order": 4,
                            "required": True,
                            "content_type": "paragraph"
                        },
                        {
                            "name": "results",
                            "title": "Results",
                            "order": 5,
                            "required": True,
                            "content_type": "mixed"
                        },
                        {
                            "name": "discussion",
                            "title": "Discussion",
                            "order": 6,
                            "required": True,
                            "content_type": "paragraph"
                        },
                        {
                            "name": "conclusion",
                            "title": "Conclusion",
                            "order": 7,
                            "required": True,
                            "content_type": "paragraph"
                        },
                        {
                            "name": "references",
                            "title": "References",
                            "order": 8,
                            "required": True,
                            "content_type": "bibliography"
                        }
                    ],
                    "citation": {
                        "style": "apa",
                        "format_string": "{author} ({year}). {title}. {journal}, {volume}({issue}), {pages}.",
                        "bibliography_format": "{author} ({year}). {title}. {journal}, {volume}({issue}), {pages}.",
                        "in_text_format": "({author}, {year})",
                        "url_format": "{author} ({year}). {title}. Retrieved from {url}",
                        "date_format": "%Y, %B %d"
                    }
                }
            }
        }

        default_template_path = self.templates_dir / "default_templates.yaml"
        with open(default_template_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_templates, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"Created default template file: {default_template_path}")
        self._parse_templates_data(default_templates)


def create_template_manager(templates_dir: str = "./templates") -> TemplateManager:
    return TemplateManager(templates_dir)
