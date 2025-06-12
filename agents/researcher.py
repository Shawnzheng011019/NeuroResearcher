import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from tools.search_tools import SearchManager
from tools.scraper_tools import WebScraperTool, ContentExtractorTool
from tools.llm_tools import LLMManager
from tools.rag_retriever import RAGRetriever
from state import ResearchState, SearchState
from config import Config
from localization.prompt_manager import MultilingualPromptManager, PromptType

logger = logging.getLogger(__name__)


class ResearcherAgent:
    def __init__(self, config: Config, search_manager: SearchManager, llm_manager: LLMManager):
        self.config = config
        self.search_manager = search_manager
        self.llm_manager = llm_manager
        self.scraper = WebScraperTool()
        self.content_extractor = ContentExtractorTool()
        self.rag_retriever = None
        self.use_rag = config.retriever in ["local", "hybrid"]

        # Initialize multilingual prompt manager
        self.prompt_manager = MultilingualPromptManager()

        # Initialize RAG retriever if needed
        if self.use_rag:
            try:
                self.rag_retriever = RAGRetriever(config)
                logger.info("RAG retriever initialized for local document search")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG retriever: {str(e)}")
                self.use_rag = False

    async def initialize_rag(self) -> bool:
        if not self.use_rag or not self.rag_retriever:
            return True

        try:
            success = await self.rag_retriever.initialize()
            if success:
                logger.info("RAG retriever initialized successfully")
            else:
                logger.warning("Failed to initialize RAG retriever, falling back to web-only search")
                self.use_rag = False
            return success
        except Exception as e:
            logger.error(f"Error initializing RAG retriever: {str(e)}")
            self.use_rag = False
            return False
        
    async def conduct_initial_research(self, state: ResearchState) -> ResearchState:
        query = state["task"].query
        logger.info(f"Starting initial research for query: {query}")

        try:
            # Initialize RAG if needed
            if self.use_rag and self.rag_retriever:
                await self.initialize_rag()

            # Collect research data from multiple sources
            all_relevant_content = []

            # 1. Local document search (if RAG is enabled)
            if self.use_rag and self.rag_retriever:
                try:
                    local_results = await self.rag_retriever.retrieve_relevant_documents(
                        query=query,
                        top_k=self.config.max_search_results_per_query // 2
                    )
                    if local_results:
                        all_relevant_content.extend(local_results)
                        logger.info(f"Found {len(local_results)} relevant local documents")
                except Exception as e:
                    logger.warning(f"Local document search failed: {str(e)}")

            # 2. Web search with intelligent source diversification
            if self.config.retriever != "local":
                # Use diversified search to reduce dependency on single sources
                search_results = await self.search_manager.search_with_diversification(
                    query, max_per_domain=2
                )

                if search_results:
                    # Extract URLs for scraping with priority consideration
                    max_web_results = self.config.max_search_results_per_query
                    if self.use_rag:
                        max_web_results = max_web_results // 2  # Split between local and web

                    # Select URLs based on priority and reliability
                    prioritized_results = sorted(search_results,
                                               key=lambda x: (x.get('domain_priority', 5), x.get('domain_reliability', 0.5)),
                                               reverse=True)
                    urls = [result["url"] for result in prioritized_results[:max_web_results]]

                    # Scrape content with intelligent retry and failure handling
                    scraped_data = await self.scraper.scrape_multiple(
                        urls, max_concurrent=3, min_success_rate=0.3
                    )

                    # Extract relevant content with enhanced quality assessment
                    web_content = self.content_extractor.extract_relevant_content(
                        scraped_data, query, min_quality_score=0.2
                    )
                    all_relevant_content.extend(web_content)

                    # Log source diversity metrics
                    successful_domains = set()
                    for content in web_content:
                        domain = content.get('domain', '')
                        if domain:
                            successful_domains.add(domain)

                    logger.info(f"Found {len(web_content)} relevant web sources from {len(successful_domains)} different domains")

                    # If we have very few sources, try alternative search strategies
                    if len(web_content) < 2:
                        logger.warning("Low content yield, attempting alternative search strategy")
                        await self._try_alternative_search(query, all_relevant_content)

            # Check if we have any content
            if not all_relevant_content:
                logger.warning("No research content found from any source")
                state["errors"].append("No research content found")
                return state

            # Generate initial research summary
            language_code = state["task"].language if hasattr(state["task"], 'language') else "en"
            initial_research = await self._generate_research_summary(query, all_relevant_content, language_code)

            # Update state
            state["initial_research"] = initial_research
            state["research_data"] = all_relevant_content
            state["current_step"] = "initial_research_completed"

            logger.info(f"Initial research completed. Found {len(all_relevant_content)} total sources")
            return state
            
        except Exception as e:
            logger.error(f"Error in initial research: {str(e)}")
            state["errors"].append(f"Initial research failed: {str(e)}")
            return state
    
    async def conduct_deep_research(self, state: ResearchState, topic: str) -> Dict[str, Any]:
        logger.info(f"Conducting deep research on topic: {topic}")

        try:
            # Get language code from task
            language_code = state["task"].language if hasattr(state["task"], 'language') else "en"

            # Generate specific queries for the topic
            specific_queries = await self._generate_specific_queries(topic, state["task"].query, language_code)

            all_research_data = []

            # Research each specific query using hybrid approach
            for query in specific_queries:
                query_results = []

                # 1. Local document search (if RAG is enabled)
                if self.use_rag and self.rag_retriever:
                    try:
                        local_results = await self.rag_retriever.retrieve_relevant_documents(
                            query=query,
                            top_k=3  # Limit for deep research
                        )
                        query_results.extend(local_results)
                    except Exception as e:
                        logger.warning(f"Local search failed for query '{query}': {str(e)}")

                # 2. Web search with intelligent source selection
                if self.config.retriever != "local":
                    search_results = await self.search_manager.search_with_diversification(
                        query, max_per_domain=1  # More restrictive for deep research
                    )

                    if search_results:
                        # Select highest quality sources for deep research
                        top_results = sorted(search_results,
                                           key=lambda x: (x.get('domain_priority', 5), x.get('domain_reliability', 0.5)),
                                           reverse=True)[:3]
                        urls = [result["url"] for result in top_results]

                        scraped_data = await self.scraper.scrape_multiple(
                            urls, max_concurrent=2, min_success_rate=0.5
                        )
                        web_content = self.content_extractor.extract_relevant_content(
                            scraped_data, query, min_quality_score=0.4  # Higher quality threshold for deep research
                        )
                        query_results.extend(web_content)

                all_research_data.extend(query_results)
            
            # Remove duplicates based on URL
            seen_urls = set()
            unique_research_data = []
            for item in all_research_data:
                url = item.get("url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_research_data.append(item)
            
            # Generate comprehensive research draft
            research_draft = await self._generate_research_draft(topic, unique_research_data, state["task"].query, language_code)
            
            logger.info(f"Deep research completed for topic: {topic}. Found {len(unique_research_data)} unique sources")
            
            return {
                "topic": topic,
                "content": research_draft,
                "sources": unique_research_data,
                "source_count": len(unique_research_data)
            }
            
        except Exception as e:
            logger.error(f"Error in deep research for topic {topic}: {str(e)}")
            return {
                "topic": topic,
                "content": f"Research failed for topic: {topic}. Error: {str(e)}",
                "sources": [],
                "source_count": 0
            }
    
    async def _generate_research_summary(self, query: str, content_list: List[Dict[str, Any]], language_code: Optional[str] = None) -> str:
        if not content_list:
            return "No relevant content found for the research query."

        # Prepare content for summarization
        content_summary = self.content_extractor.summarize_content(content_list, max_summary_length=3000)

        # Get localized prompts
        system_prompt, user_prompt = self.prompt_manager.format_prompt(
            PromptType.RESEARCH_SUMMARY,
            language_code=language_code,
            query=query,
            content_summary=content_summary
        )

        try:
            summary = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            return summary
        except Exception as e:
            logger.error(f"Failed to generate research summary: {str(e)}")
            return f"Failed to generate summary. Raw content available from {len(content_list)} sources."
    
    async def _generate_specific_queries(self, topic: str, main_query: str, language_code: Optional[str] = None) -> List[str]:
        # Get localized prompts
        system_prompt, user_prompt = self.prompt_manager.format_prompt(
            PromptType.RESEARCH_QUERY_GENERATION,
            language_code=language_code,
            main_query=main_query,
            topic=topic
        )

        try:
            response = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="fast"
            )

            queries = [q.strip() for q in response.split('\n') if q.strip()]
            return queries[:5]  # Limit to 5 queries

        except Exception as e:
            logger.error(f"Failed to generate specific queries: {str(e)}")
            return [f"{topic} {main_query}"]  # Fallback query
    
    async def _generate_research_draft(self, topic: str, research_data: List[Dict[str, Any]], main_query: str, language_code: Optional[str] = None) -> str:
        if not research_data:
            return f"No research data available for topic: {topic}"

        # Prepare research content
        content_summary = self.content_extractor.summarize_content(research_data, max_summary_length=4000)

        # Get localized prompts
        system_prompt, user_prompt = self.prompt_manager.format_prompt(
            PromptType.RESEARCH_DRAFT,
            language_code=language_code,
            main_query=main_query,
            topic=topic,
            content_summary=content_summary
        )

        try:
            draft = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            return draft
        except Exception as e:
            logger.error(f"Failed to generate research draft for topic {topic}: {str(e)}")
            return f"Failed to generate research draft for topic: {topic}. Error: {str(e)}"

    async def _try_alternative_search(self, original_query: str, existing_content: List[Dict[str, Any]]):
        """Try alternative search strategies when initial search yields poor results"""

        alternative_strategies = [
            # Try English translation of Chinese queries
            self._translate_query_to_english(original_query),
            # Try broader terms
            self._broaden_search_terms(original_query),
            # Try more specific academic terms
            self._add_academic_terms(original_query)
        ]

        for strategy_query in alternative_strategies:
            if strategy_query and strategy_query != original_query:
                logger.info(f"Trying alternative search strategy: '{strategy_query}'")

                try:
                    # Use fallback search with different strategy
                    search_results = await self.search_manager.search_with_fallback(strategy_query)

                    if search_results:
                        # Focus on reliable sources only
                        reliable_results = [r for r in search_results
                                          if r.get('domain_reliability', 0) > 0.7]

                        if reliable_results:
                            urls = [result["url"] for result in reliable_results[:3]]
                            scraped_data = await self.scraper.scrape_multiple(
                                urls, max_concurrent=2, min_success_rate=0.5
                            )

                            alternative_content = self.content_extractor.extract_relevant_content(
                                scraped_data, original_query, min_quality_score=0.3
                            )

                            if alternative_content:
                                existing_content.extend(alternative_content)
                                logger.info(f"Alternative search found {len(alternative_content)} additional sources")
                                break  # Stop after first successful alternative

                except Exception as e:
                    logger.warning(f"Alternative search strategy failed: {str(e)}")
                    continue

    def _translate_query_to_english(self, query: str) -> Optional[str]:
        """Simple heuristic to create English version of Chinese queries"""
        chinese_to_english_terms = {
            '扩散模型': 'diffusion model',
            '人工智能': 'artificial intelligence',
            '深度学习': 'deep learning',
            '机器学习': 'machine learning',
            '神经网络': 'neural network',
            '自然语言处理': 'natural language processing',
            '计算机视觉': 'computer vision',
            '算法': 'algorithm',
            '训练': 'training',
            '架构': 'architecture',
            '方法': 'method',
            '应用': 'application',
            '效果': 'performance',
            '任务': 'task'
        }

        english_query = query
        for chinese, english in chinese_to_english_terms.items():
            english_query = english_query.replace(chinese, english)

        return english_query if english_query != query else None

    def _broaden_search_terms(self, query: str) -> str:
        """Create broader search terms"""
        broad_terms = {
            'diffusion model': 'generative model',
            'specific algorithm': 'machine learning',
            'particular method': 'approach'
        }

        broader_query = query
        for specific, broad in broad_terms.items():
            if specific in query.lower():
                broader_query = query.replace(specific, broad)
                break

        return broader_query

    def _add_academic_terms(self, query: str) -> str:
        """Add academic search terms to improve results"""
        academic_terms = ['research', 'paper', 'study', 'analysis']

        # Add academic terms if not already present
        query_lower = query.lower()
        for term in academic_terms:
            if term not in query_lower:
                return f"{query} {term}"

        return query
