import re
import logging
import zipfile
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

try:
    nltk.data.find('tokenizers/punkt')
except (LookupError, OSError, zipfile.BadZipFile):
    try:
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)
    except Exception as e:
        logger.warning(f"Failed to download NLTK data: {e}. Using fallback tokenization.")

# Fallback tokenization functions
def safe_sent_tokenize(text: str) -> List[str]:
    try:
        return sent_tokenize(text)
    except Exception:
        # Simple fallback sentence tokenization
        import re
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if s.strip()]

def safe_word_tokenize(text: str) -> List[str]:
    try:
        return word_tokenize(text)
    except Exception:
        # Simple fallback word tokenization
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        return words


@dataclass
class ChunkMetadata:
    chunk_id: str
    start_pos: int
    end_pos: int
    topic_keywords: List[str]
    semantic_score: float
    chunk_type: str
    parent_section: Optional[str] = None


class ChunkingStrategy(ABC):
    @abstractmethod
    async def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        pass


class SemanticChunkingStrategy(ChunkingStrategy):
    def __init__(self, max_chunk_size: int = 4000, overlap_size: int = 500):
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.sentence_patterns = [
            r'\n\n+',  # Paragraph breaks
            r'\n(?=[A-Z])',  # New sentences starting with capital
            r'\.(?=\s+[A-Z])',  # Sentence endings
            r'[.!?]+(?=\s)',  # Multiple punctuation
        ]
    
    async def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        sentences = safe_sent_tokenize(text)
        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_index = 0
        
        for i, sentence in enumerate(sentences):
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk) > self.max_chunk_size and current_chunk:
                # Create chunk from current content
                chunk_data = await self._create_chunk(
                    current_chunk, current_start, chunk_index, metadata
                )
                chunks.append(chunk_data)
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + " " + sentence
                current_start = self._find_text_position(text, sentence)
                chunk_index += 1
            else:
                current_chunk = potential_chunk
                if not current_chunk.strip():
                    current_start = self._find_text_position(text, sentence)
        
        # Add final chunk
        if current_chunk.strip():
            chunk_data = await self._create_chunk(
                current_chunk, current_start, chunk_index, metadata
            )
            chunks.append(chunk_data)
        
        return chunks
    
    async def _create_chunk(self, text: str, start_pos: int, index: int, 
                          metadata: Dict[str, Any]) -> Dict[str, Any]:
        keywords = self._extract_keywords(text)
        semantic_score = self._calculate_semantic_score(text)
        
        chunk_metadata = ChunkMetadata(
            chunk_id=f"{metadata.get('doc_id', 'unknown')}_{index}",
            start_pos=start_pos,
            end_pos=start_pos + len(text),
            topic_keywords=keywords,
            semantic_score=semantic_score,
            chunk_type="semantic",
            parent_section=metadata.get('section', None)
        )
        
        return {
            "content": text.strip(),
            "metadata": {
                **metadata,
                "chunk_metadata": chunk_metadata,
                "chunk_index": index,
                "keywords": keywords,
                "semantic_score": semantic_score
            }
        }
    
    def _get_overlap_text(self, text: str) -> str:
        words = text.split()
        if len(words) <= 50:
            return text
        return " ".join(words[-50:])
    
    def _find_text_position(self, full_text: str, target: str) -> int:
        return full_text.find(target.strip()[:50])
    
    def _extract_keywords(self, text: str) -> List[str]:
        words = safe_word_tokenize(text.lower())
        # Simple keyword extraction - can be enhanced with NLP libraries
        keywords = [word for word in words if len(word) > 4 and word.isalpha()]
        return list(set(keywords))[:10]
    
    def _calculate_semantic_score(self, text: str) -> float:
        # Simple semantic coherence score based on sentence structure
        sentences = safe_sent_tokenize(text)
        if len(sentences) < 2:
            return 1.0

        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        coherence_score = min(1.0, avg_sentence_length / 20.0)
        return coherence_score


class DocumentTypeChunkingStrategy(ChunkingStrategy):
    def __init__(self, max_chunk_size: int = 4000):
        self.max_chunk_size = max_chunk_size
        self.strategies = {
            'academic': self._chunk_academic_paper,
            'technical': self._chunk_technical_doc,
            'narrative': self._chunk_narrative_text,
            'structured': self._chunk_structured_doc,
            'default': self._chunk_default
        }
    
    async def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        doc_type = self._detect_document_type(text, metadata)
        strategy = self.strategies.get(doc_type, self.strategies['default'])
        return await strategy(text, metadata)
    
    def _detect_document_type(self, text: str, metadata: Dict[str, Any]) -> str:
        # Simple document type detection
        if 'abstract' in text.lower()[:1000] and 'references' in text.lower():
            return 'academic'
        elif re.search(r'(class|function|def|import)', text):
            return 'technical'
        elif metadata.get('file_type') in ['csv', 'json', 'xml']:
            return 'structured'
        elif len(re.findall(r'[.!?]', text)) / len(text.split()) > 0.1:
            return 'narrative'
        return 'default'
    
    async def _chunk_academic_paper(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Split by academic sections
        sections = re.split(r'\n(?=(?:Abstract|Introduction|Method|Results|Discussion|Conclusion|References))', text)
        chunks = []
        
        for i, section in enumerate(sections):
            if len(section) > self.max_chunk_size:
                # Further split large sections
                sub_chunks = await self._split_large_section(section, metadata, i)
                chunks.extend(sub_chunks)
            else:
                chunk_data = {
                    "content": section.strip(),
                    "metadata": {
                        **metadata,
                        "chunk_index": i,
                        "section_type": self._identify_section_type(section),
                        "chunk_type": "academic_section"
                    }
                }
                chunks.append(chunk_data)
        
        return chunks
    
    async def _chunk_technical_doc(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Split by code blocks and documentation sections
        code_pattern = r'```[\s\S]*?```|`[^`]+`'
        parts = re.split(f'({code_pattern})', text)
        
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for part in parts:
            if re.match(code_pattern, part):
                # Code block - keep as separate chunk if large enough
                if len(part) > 100:
                    if current_chunk:
                        chunks.append(self._create_technical_chunk(current_chunk, chunk_index, metadata, "documentation"))
                        chunk_index += 1
                        current_chunk = ""
                    
                    chunks.append(self._create_technical_chunk(part, chunk_index, metadata, "code"))
                    chunk_index += 1
                else:
                    current_chunk += part
            else:
                current_chunk += part
                
                if len(current_chunk) > self.max_chunk_size:
                    chunks.append(self._create_technical_chunk(current_chunk, chunk_index, metadata, "documentation"))
                    chunk_index += 1
                    current_chunk = ""
        
        if current_chunk.strip():
            chunks.append(self._create_technical_chunk(current_chunk, chunk_index, metadata, "documentation"))
        
        return chunks
    
    async def _chunk_narrative_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Use semantic chunking for narrative text
        semantic_strategy = SemanticChunkingStrategy(self.max_chunk_size)
        return await semantic_strategy.chunk_text(text, metadata)
    
    async def _chunk_structured_doc(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Split by structural elements
        lines = text.split('\n')
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for line in lines:
            if len(current_chunk + line) > self.max_chunk_size and current_chunk:
                chunk_data = {
                    "content": current_chunk.strip(),
                    "metadata": {
                        **metadata,
                        "chunk_index": chunk_index,
                        "chunk_type": "structured_data"
                    }
                }
                chunks.append(chunk_data)
                chunk_index += 1
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'
        
        if current_chunk.strip():
            chunk_data = {
                "content": current_chunk.strip(),
                "metadata": {
                    **metadata,
                    "chunk_index": chunk_index,
                    "chunk_type": "structured_data"
                }
            }
            chunks.append(chunk_data)
        
        return chunks
    
    async def _chunk_default(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Use recursive character text splitter as fallback
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.max_chunk_size,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        
        chunks = splitter.split_text(text)
        result = []
        
        for i, chunk in enumerate(chunks):
            chunk_data = {
                "content": chunk,
                "metadata": {
                    **metadata,
                    "chunk_index": i,
                    "chunk_type": "default"
                }
            }
            result.append(chunk_data)
        
        return result
    
    async def _split_large_section(self, section: str, metadata: Dict[str, Any], base_index: int) -> List[Dict[str, Any]]:
        # Split large sections by paragraphs
        paragraphs = section.split('\n\n')
        chunks = []
        current_chunk = ""
        sub_index = 0
        
        for paragraph in paragraphs:
            if len(current_chunk + paragraph) > self.max_chunk_size and current_chunk:
                chunk_data = {
                    "content": current_chunk.strip(),
                    "metadata": {
                        **metadata,
                        "chunk_index": f"{base_index}_{sub_index}",
                        "section_type": self._identify_section_type(current_chunk),
                        "chunk_type": "academic_subsection"
                    }
                }
                chunks.append(chunk_data)
                sub_index += 1
                current_chunk = paragraph + '\n\n'
            else:
                current_chunk += paragraph + '\n\n'
        
        if current_chunk.strip():
            chunk_data = {
                "content": current_chunk.strip(),
                "metadata": {
                    **metadata,
                    "chunk_index": f"{base_index}_{sub_index}",
                    "section_type": self._identify_section_type(current_chunk),
                    "chunk_type": "academic_subsection"
                }
            }
            chunks.append(chunk_data)
        
        return chunks
    
    def _identify_section_type(self, text: str) -> str:
        text_lower = text.lower()
        if 'abstract' in text_lower[:100]:
            return 'abstract'
        elif 'introduction' in text_lower[:100]:
            return 'introduction'
        elif any(word in text_lower[:100] for word in ['method', 'methodology', 'approach']):
            return 'methodology'
        elif any(word in text_lower[:100] for word in ['result', 'finding', 'outcome']):
            return 'results'
        elif any(word in text_lower[:100] for word in ['discussion', 'analysis', 'interpretation']):
            return 'discussion'
        elif any(word in text_lower[:100] for word in ['conclusion', 'summary', 'final']):
            return 'conclusion'
        elif 'reference' in text_lower[:100]:
            return 'references'
        return 'content'
    
    def _create_technical_chunk(self, content: str, index: int, metadata: Dict[str, Any], chunk_type: str) -> Dict[str, Any]:
        return {
            "content": content.strip(),
            "metadata": {
                **metadata,
                "chunk_index": index,
                "chunk_type": f"technical_{chunk_type}",
                "content_type": chunk_type
            }
        }


class AdaptiveChunkingStrategy(ChunkingStrategy):
    def __init__(self, base_chunk_size: int = 4000, min_chunk_size: int = 1000, max_chunk_size: int = 8000):
        self.base_chunk_size = base_chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.semantic_strategy = SemanticChunkingStrategy()
        self.doc_type_strategy = DocumentTypeChunkingStrategy()
    
    async def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        text_length = len(text)
        complexity_score = self._calculate_text_complexity(text)
        
        # Adapt chunk size based on text characteristics
        adapted_chunk_size = self._adapt_chunk_size(text_length, complexity_score)
        
        # Choose strategy based on text characteristics
        if complexity_score > 0.7:
            self.semantic_strategy.max_chunk_size = adapted_chunk_size
            return await self.semantic_strategy.chunk_text(text, metadata)
        else:
            self.doc_type_strategy.max_chunk_size = adapted_chunk_size
            return await self.doc_type_strategy.chunk_text(text, metadata)
    
    def _calculate_text_complexity(self, text: str) -> float:
        sentences = safe_sent_tokenize(text)
        words = safe_word_tokenize(text)

        if not sentences or not words:
            return 0.0

        avg_sentence_length = len(words) / len(sentences)
        unique_words_ratio = len(set(words)) / len(words)
        punctuation_density = len([c for c in text if c in '.,;:!?']) / len(text)

        # Normalize and combine metrics
        complexity = (
            min(avg_sentence_length / 20, 1.0) * 0.4 +
            unique_words_ratio * 0.4 +
            min(punctuation_density * 10, 1.0) * 0.2
        )

        return complexity
    
    def _adapt_chunk_size(self, text_length: int, complexity: float) -> int:
        # Adjust chunk size based on text length and complexity
        if text_length < 5000:
            base_size = self.min_chunk_size
        elif text_length > 50000:
            base_size = self.max_chunk_size
        else:
            base_size = self.base_chunk_size
        
        # Adjust for complexity
        complexity_factor = 0.7 + (complexity * 0.6)  # Range: 0.7 to 1.3
        adapted_size = int(base_size * complexity_factor)
        
        return max(self.min_chunk_size, min(adapted_size, self.max_chunk_size))


def create_chunking_strategy(strategy_type: str = "adaptive", **kwargs) -> ChunkingStrategy:
    if strategy_type == "semantic":
        return SemanticChunkingStrategy(**kwargs)
    elif strategy_type == "document_type":
        return DocumentTypeChunkingStrategy(**kwargs)
    elif strategy_type == "adaptive":
        return AdaptiveChunkingStrategy(**kwargs)
    else:
        return AdaptiveChunkingStrategy(**kwargs)
