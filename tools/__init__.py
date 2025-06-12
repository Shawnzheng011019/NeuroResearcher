# Core tools that should always be available
from .search_tools import SearchTool, DuckDuckGoSearchTool, GoogleSearchTool
from .scraper_tools import WebScraperTool, ContentExtractorTool
from .llm_tools import LLMTool, OpenAITool, AnthropicTool
from .document_tools import DocumentProcessorTool, PDFGeneratorTool, DocxGeneratorTool, ContentDeduplicator

# Optional imports that may fail due to dependencies
try:
    from .rag_tools import DocumentChunker, StructuredDataProcessor, DataStreamProcessor
    RAG_TOOLS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: RAG tools not available: {e}")
    RAG_TOOLS_AVAILABLE = False

try:
    from .embedding_manager import EmbeddingManager, create_embedding_manager
    EMBEDDING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Embedding manager not available: {e}")
    EMBEDDING_AVAILABLE = False

try:
    from .milvus_manager import MilvusManager, MilvusRetriever
    MILVUS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Milvus manager not available: {e}")
    MILVUS_AVAILABLE = False

try:
    from .rag_document_processor import RAGDocumentProcessor, create_rag_processor
    RAG_PROCESSOR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: RAG document processor not available: {e}")
    RAG_PROCESSOR_AVAILABLE = False

try:
    from .rag_retriever import RAGRetriever, create_rag_retriever
    RAG_RETRIEVER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: RAG retriever not available: {e}")
    RAG_RETRIEVER_AVAILABLE = False

try:
    from .rag_manager import RAGManager
    RAG_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: RAG manager not available: {e}")
    RAG_MANAGER_AVAILABLE = False

from .text_chunking_strategies import create_chunking_strategy, SemanticChunkingStrategy, DocumentTypeChunkingStrategy, AdaptiveChunkingStrategy
from .summarization_tools import SummarizationTool, create_summarization_tool
from .long_text_processor import LongTextProcessor, create_long_text_processor

# Build __all__ dynamically based on what's available
__all__ = [
    "SearchTool",
    "DuckDuckGoSearchTool",
    "GoogleSearchTool",
    "WebScraperTool",
    "ContentExtractorTool",
    "LLMTool",
    "OpenAITool",
    "AnthropicTool",
    "DocumentProcessorTool",
    "PDFGeneratorTool",
    "DocxGeneratorTool",
    "ContentDeduplicator",
    "create_chunking_strategy",
    "SemanticChunkingStrategy",
    "DocumentTypeChunkingStrategy",
    "AdaptiveChunkingStrategy",
    "SummarizationTool",
    "create_summarization_tool",
    "LongTextProcessor",
    "create_long_text_processor"
]

# Add optional components if available
if RAG_TOOLS_AVAILABLE:
    __all__.extend(["DocumentChunker", "StructuredDataProcessor", "DataStreamProcessor"])

if EMBEDDING_AVAILABLE:
    __all__.extend(["EmbeddingManager", "create_embedding_manager"])

if MILVUS_AVAILABLE:
    __all__.extend(["MilvusManager", "MilvusRetriever"])

if RAG_PROCESSOR_AVAILABLE:
    __all__.extend(["RAGDocumentProcessor", "create_rag_processor"])

if RAG_RETRIEVER_AVAILABLE:
    __all__.extend(["RAGRetriever", "create_rag_retriever"])

if RAG_MANAGER_AVAILABLE:
    __all__.extend(["RAGManager"])
