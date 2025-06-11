import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class SupportedLanguage(str, Enum):
    ENGLISH = "en"
    CHINESE_SIMPLIFIED = "zh-cn"
    CHINESE_TRADITIONAL = "zh-tw"
    JAPANESE = "ja"
    KOREAN = "ko"


@dataclass
class LanguageConfig:
    code: str
    name: str
    native_name: str
    direction: str = "ltr"
    date_format: str = "%Y-%m-%d"
    number_format: str = "1,234.56"
    currency_symbol: str = "$"
    translations: Dict[str, str] = field(default_factory=dict)
    section_titles: Dict[str, str] = field(default_factory=dict)
    citation_formats: Dict[str, str] = field(default_factory=dict)


class LanguageManager:
    def __init__(self, localization_dir: str = "./localization"):
        self.localization_dir = Path(localization_dir)
        self.languages_dir = self.localization_dir / "languages"
        self.languages_dir.mkdir(parents=True, exist_ok=True)
        
        self.languages: Dict[str, LanguageConfig] = {}
        self.current_language = SupportedLanguage.ENGLISH
        self._load_languages()
    
    def _load_languages(self):
        try:
            self._create_default_language_files()
            self._load_language_files()
        except Exception as e:
            logger.error(f"Failed to load languages: {str(e)}")
            self._create_fallback_language()
    
    def _create_default_language_files(self):
        language_configs = {
            SupportedLanguage.ENGLISH: {
                "code": "en",
                "name": "English",
                "native_name": "English",
                "direction": "ltr",
                "date_format": "%Y-%m-%d",
                "number_format": "1,234.56",
                "currency_symbol": "$",
                "translations": {
                    "title": "Title",
                    "abstract": "Abstract",
                    "introduction": "Introduction",
                    "methodology": "Methodology",
                    "results": "Results",
                    "discussion": "Discussion",
                    "conclusion": "Conclusion",
                    "references": "References",
                    "table_of_contents": "Table of Contents",
                    "generated_on": "Generated on",
                    "page": "Page",
                    "source": "Source",
                    "sources": "Sources",
                    "author": "Author",
                    "date": "Date",
                    "retrieved_from": "Retrieved from",
                    "accessed_on": "Accessed on"
                },
                "section_titles": {
                    "abstract": "Abstract",
                    "introduction": "Introduction",
                    "background": "Background",
                    "objectives": "Research Objectives",
                    "literature_review": "Literature Review",
                    "methodology": "Methodology",
                    "findings": "Key Findings",
                    "results": "Results",
                    "analysis": "Analysis",
                    "discussion": "Discussion",
                    "conclusion": "Conclusion",
                    "references": "References",
                    "appendix": "Appendix"
                },
                "citation_formats": {
                    "apa": "{author} ({year}). {title}. {source}.",
                    "mla": "{author}. \"{title}.\" {source}, {year}.",
                    "chicago": "{author}. \"{title}.\" {source} ({year}).",
                    "ieee": "[{number}] {author}, \"{title},\" {source}, {year}.",
                    "harvard": "{author} {year}, '{title}', {source}."
                }
            },
            SupportedLanguage.CHINESE_SIMPLIFIED: {
                "code": "zh-cn",
                "name": "Chinese Simplified",
                "native_name": "简体中文",
                "direction": "ltr",
                "date_format": "%Y年%m月%d日",
                "number_format": "1,234.56",
                "currency_symbol": "¥",
                "translations": {
                    "title": "标题",
                    "abstract": "摘要",
                    "introduction": "引言",
                    "methodology": "方法论",
                    "results": "结果",
                    "discussion": "讨论",
                    "conclusion": "结论",
                    "references": "参考文献",
                    "table_of_contents": "目录",
                    "generated_on": "生成于",
                    "page": "页",
                    "source": "来源",
                    "sources": "来源",
                    "author": "作者",
                    "date": "日期",
                    "retrieved_from": "检索自",
                    "accessed_on": "访问于"
                },
                "section_titles": {
                    "abstract": "摘要",
                    "introduction": "引言",
                    "background": "背景",
                    "objectives": "研究目标",
                    "literature_review": "文献综述",
                    "methodology": "方法论",
                    "findings": "主要发现",
                    "results": "结果",
                    "analysis": "分析",
                    "discussion": "讨论",
                    "conclusion": "结论",
                    "references": "参考文献",
                    "appendix": "附录"
                },
                "citation_formats": {
                    "apa": "{author} ({year}). {title}. {source}.",
                    "mla": "{author}. \"{title}.\" {source}, {year}.",
                    "chicago": "{author}. \"{title}.\" {source} ({year}).",
                    "ieee": "[{number}] {author}, \"{title},\" {source}, {year}.",
                    "harvard": "{author} {year}, '{title}', {source}."
                }
            },
            SupportedLanguage.CHINESE_TRADITIONAL: {
                "code": "zh-tw",
                "name": "Chinese Traditional",
                "native_name": "繁體中文",
                "direction": "ltr",
                "date_format": "%Y年%m月%d日",
                "number_format": "1,234.56",
                "currency_symbol": "NT$",
                "translations": {
                    "title": "標題",
                    "abstract": "摘要",
                    "introduction": "引言",
                    "methodology": "方法論",
                    "results": "結果",
                    "discussion": "討論",
                    "conclusion": "結論",
                    "references": "參考文獻",
                    "table_of_contents": "目錄",
                    "generated_on": "生成於",
                    "page": "頁",
                    "source": "來源",
                    "sources": "來源",
                    "author": "作者",
                    "date": "日期",
                    "retrieved_from": "檢索自",
                    "accessed_on": "訪問於"
                },
                "section_titles": {
                    "abstract": "摘要",
                    "introduction": "引言",
                    "background": "背景",
                    "objectives": "研究目標",
                    "literature_review": "文獻綜述",
                    "methodology": "方法論",
                    "findings": "主要發現",
                    "results": "結果",
                    "analysis": "分析",
                    "discussion": "討論",
                    "conclusion": "結論",
                    "references": "參考文獻",
                    "appendix": "附錄"
                },
                "citation_formats": {
                    "apa": "{author} ({year}). {title}. {source}.",
                    "mla": "{author}. 「{title}」 {source}, {year}.",
                    "chicago": "{author}. 「{title}」 {source} ({year}).",
                    "ieee": "[{number}] {author}, 「{title}」 {source}, {year}.",
                    "harvard": "{author} {year}, '{title}', {source}."
                }
            },
            SupportedLanguage.JAPANESE: {
                "code": "ja",
                "name": "Japanese",
                "native_name": "日本語",
                "direction": "ltr",
                "date_format": "%Y年%m月%d日",
                "number_format": "1,234.56",
                "currency_symbol": "¥",
                "translations": {
                    "title": "タイトル",
                    "abstract": "要約",
                    "introduction": "序論",
                    "methodology": "方法論",
                    "results": "結果",
                    "discussion": "考察",
                    "conclusion": "結論",
                    "references": "参考文献",
                    "table_of_contents": "目次",
                    "generated_on": "生成日",
                    "page": "ページ",
                    "source": "出典",
                    "sources": "出典",
                    "author": "著者",
                    "date": "日付",
                    "retrieved_from": "取得元",
                    "accessed_on": "アクセス日"
                },
                "section_titles": {
                    "abstract": "要約",
                    "introduction": "序論",
                    "background": "背景",
                    "objectives": "研究目的",
                    "literature_review": "文献レビュー",
                    "methodology": "方法論",
                    "findings": "主な発見",
                    "results": "結果",
                    "analysis": "分析",
                    "discussion": "考察",
                    "conclusion": "結論",
                    "references": "参考文献",
                    "appendix": "付録"
                },
                "citation_formats": {
                    "apa": "{author} ({year}). {title}. {source}.",
                    "mla": "{author}. 「{title}」 {source}, {year}.",
                    "chicago": "{author}. 「{title}」 {source} ({year}).",
                    "ieee": "[{number}] {author}, 「{title}」 {source}, {year}.",
                    "harvard": "{author} {year}, '{title}', {source}."
                }
            },
            SupportedLanguage.KOREAN: {
                "code": "ko",
                "name": "Korean",
                "native_name": "한국어",
                "direction": "ltr",
                "date_format": "%Y년 %m월 %d일",
                "number_format": "1,234.56",
                "currency_symbol": "₩",
                "translations": {
                    "title": "제목",
                    "abstract": "초록",
                    "introduction": "서론",
                    "methodology": "방법론",
                    "results": "결과",
                    "discussion": "토론",
                    "conclusion": "결론",
                    "references": "참고문헌",
                    "table_of_contents": "목차",
                    "generated_on": "생성일",
                    "page": "페이지",
                    "source": "출처",
                    "sources": "출처",
                    "author": "저자",
                    "date": "날짜",
                    "retrieved_from": "검색 출처",
                    "accessed_on": "접근일"
                },
                "section_titles": {
                    "abstract": "초록",
                    "introduction": "서론",
                    "background": "배경",
                    "objectives": "연구 목적",
                    "literature_review": "문헌 검토",
                    "methodology": "방법론",
                    "findings": "주요 발견",
                    "results": "결과",
                    "analysis": "분석",
                    "discussion": "토론",
                    "conclusion": "결론",
                    "references": "참고문헌",
                    "appendix": "부록"
                },
                "citation_formats": {
                    "apa": "{author} ({year}). {title}. {source}.",
                    "mla": "{author}. \"{title}.\" {source}, {year}.",
                    "chicago": "{author}. \"{title}.\" {source} ({year}).",
                    "ieee": "[{number}] {author}, \"{title},\" {source}, {year}.",
                    "harvard": "{author} {year}, '{title}', {source}."
                }
            }
        }
        
        for lang_code, config in language_configs.items():
            file_path = self.languages_dir / f"{lang_code.value}.json"
            if not file_path.exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                logger.info(f"Created language file: {file_path}")
    
    def _load_language_files(self):
        for lang_file in self.languages_dir.glob("*.json"):
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    lang_data = json.load(f)
                    lang_config = LanguageConfig(**lang_data)
                    self.languages[lang_config.code] = lang_config
            except Exception as e:
                logger.warning(f"Failed to load language file {lang_file}: {str(e)}")
    
    def _create_fallback_language(self):
        fallback_config = LanguageConfig(
            code="en",
            name="English",
            native_name="English",
            translations={
                "title": "Title",
                "introduction": "Introduction",
                "conclusion": "Conclusion"
            }
        )
        self.languages["en"] = fallback_config
    
    def set_language(self, language_code: str) -> bool:
        if language_code in self.languages:
            self.current_language = SupportedLanguage(language_code)
            return True
        return False
    
    def get_current_language(self) -> LanguageConfig:
        return self.languages.get(self.current_language.value, self.languages.get("en"))
    
    def get_language(self, language_code: str) -> Optional[LanguageConfig]:
        return self.languages.get(language_code)
    
    def translate(self, key: str, language_code: Optional[str] = None) -> str:
        lang_code = language_code or self.current_language.value
        lang_config = self.languages.get(lang_code)
        
        if lang_config and key in lang_config.translations:
            return lang_config.translations[key]
        
        fallback_config = self.languages.get("en")
        if fallback_config and key in fallback_config.translations:
            return fallback_config.translations[key]
        
        return key.replace("_", " ").title()
    
    def get_section_title(self, section_name: str, language_code: Optional[str] = None) -> str:
        lang_code = language_code or self.current_language.value
        lang_config = self.languages.get(lang_code)
        
        if lang_config and section_name in lang_config.section_titles:
            return lang_config.section_titles[section_name]
        
        return self.translate(section_name, language_code)
    
    def get_citation_format(self, style: str, language_code: Optional[str] = None) -> str:
        lang_code = language_code or self.current_language.value
        lang_config = self.languages.get(lang_code)
        
        if lang_config and style in lang_config.citation_formats:
            return lang_config.citation_formats[style]
        
        fallback_config = self.languages.get("en")
        if fallback_config and style in fallback_config.citation_formats:
            return fallback_config.citation_formats[style]
        
        return "{author} ({year}). {title}. {source}."
    
    def list_supported_languages(self) -> List[Dict[str, str]]:
        return [
            {
                "code": config.code,
                "name": config.name,
                "native_name": config.native_name
            }
            for config in self.languages.values()
        ]


def create_language_manager(localization_dir: str = "./localization") -> LanguageManager:
    return LanguageManager(localization_dir)
