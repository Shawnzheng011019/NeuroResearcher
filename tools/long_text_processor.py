import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

from .text_chunking_strategies import create_chunking_strategy, ChunkingStrategy
from .summarization_tools import SummarizationTool, create_summarization_tool
from .llm_tools import LLMManager
from config import Config

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    original_text: str
    chunks: List[Dict[str, Any]]
    chunk_summaries: List[Dict[str, Any]]
    hierarchical_summary: Dict[str, Any]
    final_summary: str
    processing_metadata: Dict[str, Any]


class HierarchicalSummarizer:
    def __init__(self, llm_manager: LLMManager, config: Config):
        self.llm_manager = llm_manager
        self.config = config
    
    async def create_hierarchical_summary(self, chunk_summaries: List[Dict[str, Any]], 
                                        original_context: Optional[str] = None) -> Dict[str, Any]:
        if not chunk_summaries:
            return {"summary": "", "levels": [], "metadata": {}}
        
        start_time = datetime.now()
        
        # Level 1: Group chunk summaries by topic/section
        grouped_summaries = await self._group_summaries_by_topic(chunk_summaries)
        
        # Level 2: Create intermediate summaries for each group
        intermediate_summaries = await self._create_intermediate_summaries(grouped_summaries, original_context)
        
        # Level 3: Create final unified summary
        final_summary = await self._create_final_summary(intermediate_summaries, original_context)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "summary": final_summary,
            "levels": {
                "chunk_summaries": chunk_summaries,
                "grouped_summaries": grouped_summaries,
                "intermediate_summaries": intermediate_summaries
            },
            "metadata": {
                "total_chunks": len(chunk_summaries),
                "topic_groups": len(grouped_summaries),
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    async def _group_summaries_by_topic(self, chunk_summaries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        # Simple topic grouping based on keywords and content similarity
        groups = {}
        
        for summary_data in chunk_summaries:
            summary = summary_data.get("summary", "")
            metadata = summary_data.get("summary_metadata")
            
            # Extract topic from metadata or content
            topic = "general"
            if metadata and hasattr(metadata, 'chunk_ids'):
                # Use section information if available
                original_chunk = summary_data.get("original_chunk", {})
                chunk_metadata = original_chunk.get("metadata", {})
                topic = chunk_metadata.get("section_type", "general")
            
            # Group by topic
            if topic not in groups:
                groups[topic] = []
            groups[topic].append(summary_data)
        
        return groups
    
    async def _create_intermediate_summaries(self, grouped_summaries: Dict[str, List[Dict[str, Any]]], 
                                           context: Optional[str] = None) -> List[Dict[str, Any]]:
        intermediate_summaries = []
        
        for topic, summaries in grouped_summaries.items():
            if len(summaries) == 1:
                # Single summary, use as-is
                intermediate_summaries.append({
                    "topic": topic,
                    "summary": summaries[0]["summary"],
                    "source_count": 1
                })
            else:
                # Multiple summaries, merge them
                combined_text = "\n\n".join([s["summary"] for s in summaries])
                
                system_prompt = f"""You are an expert at merging related summaries. Combine the following summaries about '{topic}' into a single, coherent summary that captures all the key points without redundancy."""
                
                context_info = f"\nContext: {context}" if context else ""
                
                prompt = f"""Please merge the following summaries into a single, comprehensive summary about '{topic}'. Eliminate redundancy while preserving all important information.{context_info}

Summaries to merge:
{combined_text}

Merged summary:"""
                
                try:
                    merged_summary = await self.llm_manager.generate_with_fallback(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        tool_type="smart"
                    )
                    
                    intermediate_summaries.append({
                        "topic": topic,
                        "summary": merged_summary.strip(),
                        "source_count": len(summaries)
                    })
                
                except Exception as e:
                    logger.error(f"Failed to merge summaries for topic '{topic}': {str(e)}")
                    # Fallback: concatenate summaries
                    intermediate_summaries.append({
                        "topic": topic,
                        "summary": combined_text,
                        "source_count": len(summaries),
                        "error": str(e)
                    })
        
        return intermediate_summaries
    
    async def _create_final_summary(self, intermediate_summaries: List[Dict[str, Any]], 
                                  context: Optional[str] = None) -> str:
        if not intermediate_summaries:
            return ""
        
        if len(intermediate_summaries) == 1:
            return intermediate_summaries[0]["summary"]
        
        # Combine all intermediate summaries
        combined_sections = []
        for summary_data in intermediate_summaries:
            topic = summary_data["topic"]
            summary = summary_data["summary"]
            combined_sections.append(f"**{topic.title()}:**\n{summary}")
        
        combined_text = "\n\n".join(combined_sections)
        
        system_prompt = """You are an expert at creating comprehensive final summaries. Synthesize the following topic-based summaries into a single, well-structured, coherent summary that flows naturally and covers all key points."""
        
        context_info = f"\nContext: {context}" if context else ""
        
        prompt = f"""Please create a comprehensive final summary by synthesizing the following topic-based summaries. The final summary should be well-structured, coherent, and cover all the key points from each topic.{context_info}

Topic-based summaries:
{combined_text}

Final comprehensive summary:"""
        
        try:
            final_summary = await self.llm_manager.generate_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                tool_type="strategic"
            )
            
            return final_summary.strip()
        
        except Exception as e:
            logger.error(f"Failed to create final summary: {str(e)}")
            # Fallback: return combined sections
            return combined_text


class LongTextProcessor:
    def __init__(self, config: Config):
        self.config = config
        self.llm_manager = LLMManager(config)
        self.summarization_tool = create_summarization_tool(config)
        self.hierarchical_summarizer = HierarchicalSummarizer(self.llm_manager, config)
        
        # Initialize chunking strategy
        self.chunking_strategy = create_chunking_strategy(
            strategy_type="adaptive",
            base_chunk_size=config.max_chunk_size_for_summary,
            min_chunk_size=config.max_chunk_size_for_summary // 2,
            max_chunk_size=config.max_chunk_size_for_summary * 2
        )
    
    async def process_long_text(self, text: str, metadata: Optional[Dict[str, Any]] = None,
                              processing_options: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        if not text or len(text) < self.config.long_text_threshold:
            raise ValueError(f"Text must be at least {self.config.long_text_threshold} characters long")
        
        start_time = datetime.now()
        metadata = metadata or {}
        processing_options = processing_options or {}
        
        logger.info(f"Processing long text of {len(text)} characters")
        
        try:
            # Step 1: Intelligent chunking
            chunks = await self._chunk_text(text, metadata)
            logger.info(f"Created {len(chunks)} chunks")
            
            # Step 2: Summarize each chunk
            chunk_summaries = await self._summarize_chunks(chunks, processing_options)
            logger.info(f"Generated {len(chunk_summaries)} chunk summaries")
            
            # Step 3: Create hierarchical summary
            hierarchical_summary = await self._create_hierarchical_summary(
                chunk_summaries, metadata.get("context")
            )
            logger.info("Created hierarchical summary")
            
            # Step 4: Generate final summary
            final_summary = hierarchical_summary["summary"]
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            processing_metadata = {
                "original_length": len(text),
                "final_summary_length": len(final_summary),
                "compression_ratio": len(final_summary) / len(text),
                "chunk_count": len(chunks),
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "config_used": {
                    "chunk_size": self.config.max_chunk_size_for_summary,
                    "overlap": self.config.summary_chunk_overlap,
                    "max_summary_length": self.config.max_summary_length,
                    "strategy": processing_options.get("strategy", "hybrid")
                }
            }
            
            return ProcessingResult(
                original_text=text,
                chunks=chunks,
                chunk_summaries=chunk_summaries,
                hierarchical_summary=hierarchical_summary,
                final_summary=final_summary,
                processing_metadata=processing_metadata
            )
        
        except Exception as e:
            logger.error(f"Long text processing failed: {str(e)}")
            raise
    
    async def _chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        return await self.chunking_strategy.chunk_text(text, metadata)
    
    async def _summarize_chunks(self, chunks: List[Dict[str, Any]], 
                              processing_options: Dict[str, Any]) -> List[Dict[str, Any]]:
        strategy = processing_options.get("strategy", "hybrid")
        max_length = processing_options.get("max_summary_length", self.config.max_summary_length)
        
        return await self.summarization_tool.summarize_chunks(
            chunks, strategy, max_length
        )
    
    async def _create_hierarchical_summary(self, chunk_summaries: List[Dict[str, Any]], 
                                         context: Optional[str] = None) -> Dict[str, Any]:
        if not self.config.enable_hierarchical_summary:
            # Simple concatenation fallback
            all_summaries = [cs["summary"] for cs in chunk_summaries]
            combined_summary = "\n\n".join(all_summaries)
            
            return {
                "summary": combined_summary,
                "levels": {"chunk_summaries": chunk_summaries},
                "metadata": {"simple_concatenation": True}
            }
        
        return await self.hierarchical_summarizer.create_hierarchical_summary(
            chunk_summaries, context
        )
    
    async def process_multiple_texts(self, texts: List[Tuple[str, Dict[str, Any]]], 
                                   processing_options: Optional[Dict[str, Any]] = None) -> List[ProcessingResult]:
        processing_options = processing_options or {}
        
        # Process texts in parallel with concurrency limit
        semaphore = asyncio.Semaphore(self.config.max_parallel_summaries)
        
        async def process_single_text(text_data: Tuple[str, Dict[str, Any]]) -> ProcessingResult:
            async with semaphore:
                text, metadata = text_data
                return await self.process_long_text(text, metadata, processing_options)
        
        tasks = [process_single_text(text_data) for text_data in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return successful results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        
        if len(successful_results) < len(texts):
            logger.warning(f"Only {len(successful_results)}/{len(texts)} texts were successfully processed")
        
        return successful_results
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        return {
            "total_cost": self.llm_manager.get_total_cost(),
            "config": {
                "long_text_threshold": self.config.long_text_threshold,
                "max_chunk_size": self.config.max_chunk_size_for_summary,
                "chunk_overlap": self.config.summary_chunk_overlap,
                "max_summary_length": self.config.max_summary_length,
                "hierarchical_enabled": self.config.enable_hierarchical_summary,
                "max_parallel": self.config.max_parallel_summaries
            }
        }


def create_long_text_processor(config: Config) -> LongTextProcessor:
    return LongTextProcessor(config)
