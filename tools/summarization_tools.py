import asyncio
import logging
import hashlib
import json
from typing import Dict, List, Any, Optional, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import aiofiles
from pathlib import Path

from .llm_tools import LLMManager
from config import Config

logger = logging.getLogger(__name__)


@dataclass
class SummaryMetadata:
    original_length: int
    summary_length: int
    compression_ratio: float
    quality_score: float
    processing_time: float
    model_used: str
    timestamp: str
    chunk_ids: List[str]


class SummaryCache:
    def __init__(self, cache_dir: str = "./cache/summaries"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, text: str, summary_type: str, max_length: int) -> str:
        content = f"{text}_{summary_type}_{max_length}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get_cached_summary(self, text: str, summary_type: str, max_length: int) -> Optional[Dict[str, Any]]:
        cache_key = self._get_cache_key(text, summary_type, max_length)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                async with aiofiles.open(cache_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            except Exception as e:
                logger.warning(f"Failed to read cache file {cache_file}: {str(e)}")
        
        return None
    
    async def cache_summary(self, text: str, summary_type: str, max_length: int, 
                          summary_data: Dict[str, Any]) -> None:
        cache_key = self._get_cache_key(text, summary_type, max_length)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            async with aiofiles.open(cache_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(summary_data, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"Failed to cache summary: {str(e)}")


class SummaryStrategy(ABC):
    @abstractmethod
    async def summarize(self, text: str, max_length: int, context: Optional[str] = None) -> Dict[str, Any]:
        pass


class ExtractiveSummaryStrategy(SummaryStrategy):
    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager

    async def summarize(self, text: str, max_length: int, context: Optional[str] = None) -> Dict[str, Any]:
        start_time = datetime.now()

        system_prompt = """You are an expert at extractive summarization. Extract the most important sentences from the text to create a concise summary. Maintain the original wording and structure as much as possible."""

        context_info = f"\nContext: {context}" if context else ""

        prompt = f"""Please create an extractive summary of the following text. The summary should be approximately {max_length} characters long and should extract the most important sentences while maintaining their original form.{context_info}

Text to summarize:
{text}

Summary:"""

        try:
            summary = await self.llm_manager.generate_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                tool_type="fast"
            )

            processing_time = (datetime.now() - start_time).total_seconds()

            return {
                "summary": summary.strip(),
                "strategy": "extractive",
                "metadata": SummaryMetadata(
                    original_length=len(text),
                    summary_length=len(summary),
                    compression_ratio=len(summary) / len(text),
                    quality_score=self._calculate_quality_score(text, summary),
                    processing_time=processing_time,
                    model_used="fast_llm",
                    timestamp=datetime.now().isoformat(),
                    chunk_ids=[]
                )
            }

        except Exception as e:
            logger.error(f"Extractive summarization failed: {str(e)}")
            raise

    def _calculate_quality_score(self, original: str, summary: str) -> float:
        # Simple quality score based on compression ratio and content preservation
        if not original or not summary:
            return 0.0

        compression_ratio = len(summary) / len(original)

        # Ideal compression ratio is between 0.1 and 0.3
        if 0.1 <= compression_ratio <= 0.3:
            ratio_score = 1.0
        elif compression_ratio < 0.1:
            ratio_score = compression_ratio / 0.1
        else:
            ratio_score = max(0.0, 1.0 - (compression_ratio - 0.3) / 0.7)

        # Check for key information preservation (simple heuristic)
        original_words = set(original.lower().split())
        summary_words = set(summary.lower().split())

        if original_words:
            word_overlap = len(original_words.intersection(summary_words)) / len(original_words)
        else:
            word_overlap = 0.0

        # Combine scores
        quality_score = (ratio_score * 0.6) + (word_overlap * 0.4)

        return min(1.0, quality_score)


class AbstractiveSummaryStrategy(SummaryStrategy):
    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager

    async def summarize(self, text: str, max_length: int, context: Optional[str] = None) -> Dict[str, Any]:
        start_time = datetime.now()

        system_prompt = """You are an expert at abstractive summarization. Create a concise, coherent summary that captures the main ideas and key points of the text in your own words. Focus on the essential information and maintain logical flow."""

        context_info = f"\nContext: {context}" if context else ""

        prompt = f"""Please create an abstractive summary of the following text. The summary should be approximately {max_length} characters long and should capture the main ideas and key points in a coherent, well-structured manner.{context_info}

Text to summarize:
{text}

Summary:"""

        try:
            summary = await self.llm_manager.generate_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )

            processing_time = (datetime.now() - start_time).total_seconds()

            return {
                "summary": summary.strip(),
                "strategy": "abstractive",
                "metadata": SummaryMetadata(
                    original_length=len(text),
                    summary_length=len(summary),
                    compression_ratio=len(summary) / len(text),
                    quality_score=self._calculate_quality_score(text, summary),
                    processing_time=processing_time,
                    model_used="smart_llm",
                    timestamp=datetime.now().isoformat(),
                    chunk_ids=[]
                )
            }

        except Exception as e:
            logger.error(f"Abstractive summarization failed: {str(e)}")
            raise

    def _calculate_quality_score(self, original: str, summary: str) -> float:
        # Simple quality score based on compression ratio and content preservation
        if not original or not summary:
            return 0.0

        compression_ratio = len(summary) / len(original)

        # Ideal compression ratio is between 0.1 and 0.3
        if 0.1 <= compression_ratio <= 0.3:
            ratio_score = 1.0
        elif compression_ratio < 0.1:
            ratio_score = compression_ratio / 0.1
        else:
            ratio_score = max(0.0, 1.0 - (compression_ratio - 0.3) / 0.7)

        # Check for key information preservation (simple heuristic)
        original_words = set(original.lower().split())
        summary_words = set(summary.lower().split())

        if original_words:
            word_overlap = len(original_words.intersection(summary_words)) / len(original_words)
        else:
            word_overlap = 0.0

        # Combine scores
        quality_score = (ratio_score * 0.6) + (word_overlap * 0.4)

        return min(1.0, quality_score)


class HybridSummaryStrategy(SummaryStrategy):
    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager
        self.extractive_strategy = ExtractiveSummaryStrategy(llm_manager)
        self.abstractive_strategy = AbstractiveSummaryStrategy(llm_manager)
    
    async def summarize(self, text: str, max_length: int, context: Optional[str] = None) -> Dict[str, Any]:
        start_time = datetime.now()
        
        # First, create an extractive summary
        extractive_length = int(max_length * 1.5)  # Longer extractive summary
        extractive_result = await self.extractive_strategy.summarize(text, extractive_length, context)
        
        # Then, create an abstractive summary from the extractive summary
        abstractive_result = await self.abstractive_strategy.summarize(
            extractive_result["summary"], max_length, context
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "summary": abstractive_result["summary"],
            "strategy": "hybrid",
            "extractive_intermediate": extractive_result["summary"],
            "metadata": SummaryMetadata(
                original_length=len(text),
                summary_length=len(abstractive_result["summary"]),
                compression_ratio=len(abstractive_result["summary"]) / len(text),
                quality_score=max(
                    extractive_result["metadata"].quality_score,
                    abstractive_result["metadata"].quality_score
                ),
                processing_time=processing_time,
                model_used="hybrid",
                timestamp=datetime.now().isoformat(),
                chunk_ids=[]
            )
        }


class TopicAwareSummaryStrategy(SummaryStrategy):
    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager
    
    async def summarize(self, text: str, max_length: int, context: Optional[str] = None) -> Dict[str, Any]:
        start_time = datetime.now()
        
        # First, identify main topics
        topics = await self._identify_topics(text)
        
        # Create topic-aware summary
        system_prompt = """You are an expert at topic-aware summarization. Create a summary that covers all the main topics identified in the text while maintaining balance and coherence."""
        
        topics_info = f"\nMain topics identified: {', '.join(topics)}" if topics else ""
        context_info = f"\nContext: {context}" if context else ""
        
        prompt = f"""Please create a comprehensive summary of the following text. The summary should be approximately {max_length} characters long and should cover all the main topics while maintaining balance and coherence.{topics_info}{context_info}

Text to summarize:
{text}

Summary:"""
        
        try:
            summary = await self.llm_manager.generate_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "summary": summary.strip(),
                "strategy": "topic_aware",
                "topics": topics,
                "metadata": SummaryMetadata(
                    original_length=len(text),
                    summary_length=len(summary),
                    compression_ratio=len(summary) / len(text),
                    quality_score=self._calculate_quality_score(text, summary),
                    processing_time=processing_time,
                    model_used="smart_llm",
                    timestamp=datetime.now().isoformat(),
                    chunk_ids=[]
                )
            }
        
        except Exception as e:
            logger.error(f"Topic-aware summarization failed: {str(e)}")
            raise

    def _calculate_quality_score(self, original: str, summary: str) -> float:
        # Simple quality score based on compression ratio and content preservation
        if not original or not summary:
            return 0.0

        compression_ratio = len(summary) / len(original)

        # Ideal compression ratio is between 0.1 and 0.3
        if 0.1 <= compression_ratio <= 0.3:
            ratio_score = 1.0
        elif compression_ratio < 0.1:
            ratio_score = compression_ratio / 0.1
        else:
            ratio_score = max(0.0, 1.0 - (compression_ratio - 0.3) / 0.7)

        # Check for key information preservation (simple heuristic)
        original_words = set(original.lower().split())
        summary_words = set(summary.lower().split())

        if original_words:
            word_overlap = len(original_words.intersection(summary_words)) / len(original_words)
        else:
            word_overlap = 0.0

        # Combine scores
        quality_score = (ratio_score * 0.6) + (word_overlap * 0.4)

        return min(1.0, quality_score)

    async def _identify_topics(self, text: str) -> List[str]:
        system_prompt = "You are an expert at topic identification. Identify the main topics in the given text."
        
        prompt = f"""Please identify the main topics in the following text. Return only the topic names, separated by commas.

Text:
{text[:2000]}...

Main topics:"""
        
        try:
            response = await self.llm_manager.generate_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                tool_type="fast"
            )
            
            topics = [topic.strip() for topic in response.split(',')]
            return topics[:5]  # Limit to 5 main topics
        
        except Exception as e:
            logger.warning(f"Topic identification failed: {str(e)}")
            return []


class SummarizationTool:
    def __init__(self, config: Config):
        self.config = config
        self.llm_manager = LLMManager(config)
        self.cache = SummaryCache() if config.summary_cache_enabled else None
        
        self.strategies = {
            "extractive": ExtractiveSummaryStrategy(self.llm_manager),
            "abstractive": AbstractiveSummaryStrategy(self.llm_manager),
            "hybrid": HybridSummaryStrategy(self.llm_manager),
            "topic_aware": TopicAwareSummaryStrategy(self.llm_manager)
        }
    
    async def summarize_text(self, text: str, strategy: str = "hybrid", 
                           max_length: Optional[int] = None,
                           context: Optional[str] = None) -> Dict[str, Any]:
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        max_length = max_length or self.config.max_summary_length
        
        # Check cache first
        if self.cache:
            cached_result = await self.cache.get_cached_summary(text, strategy, max_length)
            if cached_result:
                logger.info("Using cached summary")
                return cached_result
        
        # Get strategy and summarize
        summary_strategy = self.strategies.get(strategy, self.strategies["hybrid"])
        result = await summary_strategy.summarize(text, max_length, context)
        
        # Cache result
        if self.cache:
            await self.cache.cache_summary(text, strategy, max_length, result)
        
        return result
    
    async def summarize_chunks(self, chunks: List[Dict[str, Any]], 
                             strategy: str = "hybrid",
                             max_length_per_chunk: Optional[int] = None) -> List[Dict[str, Any]]:
        max_length_per_chunk = max_length_per_chunk or self.config.max_summary_length
        
        # Process chunks in parallel with concurrency limit
        semaphore = asyncio.Semaphore(self.config.max_parallel_summaries)
        
        async def summarize_single_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                content = chunk.get("content", "")
                metadata = chunk.get("metadata", {})
                context = f"Document: {metadata.get('source', 'Unknown')}"
                
                try:
                    summary_result = await self.summarize_text(
                        content, strategy, max_length_per_chunk, context
                    )
                    
                    return {
                        "original_chunk": chunk,
                        "summary": summary_result["summary"],
                        "summary_metadata": summary_result["metadata"],
                        "strategy": strategy
                    }
                
                except Exception as e:
                    logger.error(f"Failed to summarize chunk: {str(e)}")
                    return {
                        "original_chunk": chunk,
                        "summary": content[:max_length_per_chunk],  # Fallback to truncation
                        "summary_metadata": None,
                        "strategy": "fallback",
                        "error": str(e)
                    }
        
        tasks = [summarize_single_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return successful results
        successful_results: List[Dict[str, Any]] = []
        for r in results:
            if not isinstance(r, Exception):
                successful_results.append(r)  # type: ignore

        if len(successful_results) < len(chunks):
            logger.warning(f"Only {len(successful_results)}/{len(chunks)} chunks were successfully summarized")

        return successful_results
    
    def _calculate_quality_score(self, original: str, summary: str) -> float:
        # Simple quality score based on compression ratio and content preservation
        if not original or not summary:
            return 0.0
        
        compression_ratio = len(summary) / len(original)
        
        # Ideal compression ratio is between 0.1 and 0.3
        if 0.1 <= compression_ratio <= 0.3:
            ratio_score = 1.0
        elif compression_ratio < 0.1:
            ratio_score = compression_ratio / 0.1
        else:
            ratio_score = max(0.0, 1.0 - (compression_ratio - 0.3) / 0.7)
        
        # Check for key information preservation (simple heuristic)
        original_words = set(original.lower().split())
        summary_words = set(summary.lower().split())
        
        if original_words:
            word_overlap = len(original_words.intersection(summary_words)) / len(original_words)
        else:
            word_overlap = 0.0
        
        # Combine scores
        quality_score = (ratio_score * 0.6) + (word_overlap * 0.4)
        
        return min(1.0, quality_score)


def create_summarization_tool(config: Config) -> SummarizationTool:
    return SummarizationTool(config)
