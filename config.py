"""Configuration module for GPT Researcher LangGraph implementation."""

from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ReportType(str, Enum):
    """Enumeration of available report types."""
    RESEARCH_REPORT = "research_report"
    RESOURCE_REPORT = "resource_report"
    OUTLINE_REPORT = "outline_report"
    CUSTOM_REPORT = "custom_report"
    SUBTOPIC_REPORT = "subtopic_report"
    DEEP_RESEARCH = "deep_research"


class ReportSource(str, Enum):
    WEB = "web"
    LOCAL = "local"
    HYBRID = "hybrid"


class Tone(str, Enum):
    OBJECTIVE = "objective"
    FORMAL = "formal"
    ANALYTICAL = "analytical"
    PERSUASIVE = "persuasive"
    INFORMATIVE = "informative"
    EXPLANATORY = "explanatory"
    DESCRIPTIVE = "descriptive"
    CRITICAL = "critical"
    COMPARATIVE = "comparative"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    AZURE = "azure"


class Config(BaseSettings):
    """Configuration settings for the GPT Researcher application."""

    # LLM Configuration
    llm_provider: LLMProvider = Field(default=LLMProvider.OPENAI, alias="LLM_PROVIDER")
    fast_llm_model: str = Field(default="gpt-4o-mini", alias="FAST_LLM_MODEL")
    smart_llm_model: str = Field(default="gpt-4o", alias="SMART_LLM_MODEL")
    strategic_llm_model: str = Field(default="gpt-4o", alias="STRATEGIC_LLM_MODEL")

    # API Keys
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")

    # Search Configuration
    search_api: str = Field(default="duckduckgo", alias="SEARCH_API")
    google_api_key_search: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    google_cx_id: Optional[str] = Field(default=None, alias="GOOGLE_CX_ID")
    bing_api_key: Optional[str] = Field(default=None, alias="BING_API_KEY")
    serpapi_api_key: Optional[str] = Field(default=None, alias="SERPAPI_API_KEY")
    # Research Configuration
    max_search_results_per_query: int = Field(default=8, alias="MAX_SEARCH_RESULTS_PER_QUERY")
    max_iterations: int = Field(default=3, alias="MAX_ITERATIONS")
    agent_role: Optional[str] = Field(default=None, alias="AGENT_ROLE")

    # Report Configuration
    max_subtopics: int = Field(default=5, alias="MAX_SUBTOPICS")
    report_format: str = Field(default="markdown", alias="REPORT_FORMAT")
    max_sections: int = Field(default=5, alias="MAX_SECTIONS")

    # Output Configuration
    output_path: str = Field(default="./outputs", alias="OUTPUT_PATH")

    # Browser Configuration
    selenium_web_browser: str = Field(default="chrome", alias="SELENIUM_WEB_BROWSER")
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        alias="USER_AGENT"
    )

    # Memory Configuration
    memory_backend: str = Field(default="local", alias="MEMORY_BACKEND")

    # Embedding Configuration
    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=1536, alias="EMBEDDING_DIMENSION")

    # Milvus Configuration
    milvus_host: str = Field(default="localhost", alias="MILVUS_HOST")
    milvus_port: int = Field(default=19530, alias="MILVUS_PORT")
    milvus_collection_name: str = Field(default="research_documents", alias="MILVUS_COLLECTION_NAME")
    milvus_user: Optional[str] = Field(default=None, alias="MILVUS_USER")
    milvus_password: Optional[str] = Field(default=None, alias="MILVUS_PASSWORD")

    # RAG Configuration
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    max_chunks_per_doc: int = Field(default=100, alias="MAX_CHUNKS_PER_DOC")
    similarity_threshold: float = Field(default=0.7, alias="SIMILARITY_THRESHOLD")
    top_k_retrieval: int = Field(default=10, alias="TOP_K_RETRIEVAL")

    # Document Processing Configuration
    doc_path: str = Field(default="./my-docs", alias="DOC_PATH")
    retriever: str = Field(default="web", alias="RETRIEVER")
    enable_ocr: bool = Field(default=False, alias="ENABLE_OCR")
    supported_formats: List[str] = Field(
        default_factory=lambda: ["pdf", "docx", "txt", "md", "csv", "xlsx", "json", "xml"],
        alias="SUPPORTED_FORMATS"
    )

    # Data Stream Configuration
    stream_batch_size: int = Field(default=100, alias="STREAM_BATCH_SIZE")
    stream_processing_interval: int = Field(default=60, alias="STREAM_PROCESSING_INTERVAL")

    # Long Text Processing Configuration
    long_text_threshold: int = Field(default=8000, alias="LONG_TEXT_THRESHOLD")
    max_chunk_size_for_summary: int = Field(default=4000, alias="MAX_CHUNK_SIZE_FOR_SUMMARY")
    summary_chunk_overlap: int = Field(default=500, alias="SUMMARY_CHUNK_OVERLAP")
    enable_semantic_chunking: bool = Field(default=True, alias="ENABLE_SEMANTIC_CHUNKING")
    max_summary_length: int = Field(default=1000, alias="MAX_SUMMARY_LENGTH")
    summary_temperature: float = Field(default=0.3, alias="SUMMARY_TEMPERATURE")
    enable_hierarchical_summary: bool = Field(default=True, alias="ENABLE_HIERARCHICAL_SUMMARY")
    max_parallel_summaries: int = Field(default=5, alias="MAX_PARALLEL_SUMMARIES")
    summary_cache_enabled: bool = Field(default=True, alias="SUMMARY_CACHE_ENABLED")
    summary_quality_threshold: float = Field(default=0.8, alias="SUMMARY_QUALITY_THRESHOLD")

    # Logging
    verbose: bool = Field(default=True, alias="VERBOSE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class TaskConfig(BaseModel):
    query: str
    report_type: ReportType = ReportType.RESEARCH_REPORT
    report_source: ReportSource = ReportSource.WEB
    tone: Tone = Tone.OBJECTIVE
    max_sections: int = 5
    publish_formats: Dict[str, bool] = Field(default_factory=lambda: {
        "markdown": True,
        "pdf": False,
        "docx": False
    })
    include_human_feedback: bool = False
    follow_guidelines: bool = False
    model: str = "gpt-4o"
    guidelines: List[str] = Field(default_factory=list)
    verbose: bool = True
    source_urls: Optional[List[str]] = None
    document_urls: Optional[List[str]] = None
    headers: Optional[Dict[str, str]] = None

    # Template and localization settings
    template_name: str = "none"  # "none" means no template, let LLM generate freely
    language: str = "en"
    custom_template_path: Optional[str] = None
    citation_style: str = "apa"


def get_config() -> Config:
    return Config()


def get_task_config(query: str, **kwargs) -> TaskConfig:
    return TaskConfig(query=query, **kwargs)
