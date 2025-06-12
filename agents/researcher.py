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

            # Ensure minimum source requirement is met for initial research
            min_sources_required = getattr(self.config, 'min_sources_per_topic', 2)
            if len(all_relevant_content) < min_sources_required:
                logger.warning(f"Initial research found only {len(all_relevant_content)} sources, need at least {min_sources_required}. Attempting enhanced search.")

                # Get language code from state
                language_code = state["task"].language if hasattr(state["task"], 'language') else "en"

                # Try enhanced search for initial research
                additional_sources = await self._enhanced_search_for_minimum_sources(
                    query, all_relevant_content, min_sources_required
                )
                all_relevant_content.extend(additional_sources)

            # Check if we have any content after all attempts
            if not all_relevant_content:
                logger.warning("No research content found from any source after all attempts")
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
            min_sources_required = getattr(self.config, 'min_sources_per_topic', 2)
            max_retries = getattr(self.config, 'max_search_retries', 3)

            # Research each specific query using hybrid approach
            for query in specific_queries:
                query_results = []

                # 1. Local document search (if RAG is enabled)
                if self.use_rag and self.rag_retriever:
                    try:
                        local_results = await self.rag_retriever.retrieve_relevant_documents(
                            query=query,
                            top_k=5  # Increased for better coverage
                        )
                        query_results.extend(local_results)
                    except Exception as e:
                        logger.warning(f"Local search failed for query '{query}': {str(e)}")

                # 2. Web search with intelligent source selection
                if self.config.retriever != "local":
                    search_results = await self.search_manager.search_with_diversification(
                        query, max_per_domain=2  # Increased for better coverage
                    )

                    if search_results:
                        # Select highest quality sources for deep research
                        top_results = sorted(search_results,
                                           key=lambda x: (x.get('domain_priority', 5), x.get('domain_reliability', 0.5)),
                                           reverse=True)[:5]  # Increased for better coverage
                        urls = [result["url"] for result in top_results]

                        scraped_data = await self.scraper.scrape_multiple(
                            urls, max_concurrent=3, min_success_rate=0.3  # More lenient for better coverage
                        )
                        web_content = self.content_extractor.extract_relevant_content(
                            scraped_data, query, min_quality_score=0.3  # Lower threshold for better coverage
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

            # Ensure minimum source requirement is met
            retry_count = 0
            while len(unique_research_data) < min_sources_required and retry_count < max_retries:
                logger.warning(f"Only found {len(unique_research_data)} sources for topic '{topic}', need at least {min_sources_required}. Attempting enhanced search (retry {retry_count + 1}/{max_retries})")

                additional_sources = await self._enhanced_search_for_minimum_sources(
                    topic, unique_research_data, min_sources_required
                )

                # Add new sources
                for source in additional_sources:
                    url = source.get("url", "")
                    if url not in seen_urls:
                        seen_urls.add(url)
                        unique_research_data.append(source)

                retry_count += 1

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
    
    async def _enhanced_search_for_minimum_sources(self, topic: str, existing_sources: List[Dict[str, Any]], min_required: int) -> List[Dict[str, Any]]:
        """Enhanced search strategy to ensure minimum source requirements are met"""
        additional_sources = []

        # Strategy 1: Use alternative query formulations
        alternative_queries = [
            f"{topic} research",
            f"{topic} study",
            f"{topic} analysis",
            f"{topic} review",
            f"{topic} paper",
            f"{topic} article"
        ]

        # Add English translations if original is Chinese
        if any(ord(char) > 127 for char in topic):  # Contains non-ASCII characters
            english_topic = self._translate_query_to_english(topic)
            if english_topic:
                alternative_queries.extend([
                    f"{english_topic} research",
                    f"{english_topic} study",
                    f"{english_topic} analysis"
                ])

        # Strategy 2: Use broader search terms
        broader_queries = [
            self._broaden_search_terms(topic),
            self._add_academic_terms(topic)
        ]
        alternative_queries.extend(broader_queries)

        # Get existing URLs to avoid duplicates
        existing_urls = {source.get("url", "") for source in existing_sources}

        for query in alternative_queries:
            if len(additional_sources) + len(existing_sources) >= min_required:
                break

            try:
                # Use more aggressive search settings
                search_results = await self.search_manager.search_all(query)

                if search_results:
                    # Lower quality thresholds for this enhanced search
                    filtered_results = [r for r in search_results
                                      if r.get("url", "") not in existing_urls][:5]

                    if filtered_results:
                        urls = [result["url"] for result in filtered_results]
                        scraped_data = await self.scraper.scrape_multiple(
                            urls, max_concurrent=3, min_success_rate=0.2  # Very lenient
                        )

                        # Use lower quality threshold
                        web_content = self.content_extractor.extract_relevant_content(
                            scraped_data, topic, min_quality_score=0.1
                        )

                        for content in web_content:
                            if content.get("url", "") not in existing_urls:
                                additional_sources.append(content)
                                existing_urls.add(content.get("url", ""))

                                if len(additional_sources) + len(existing_sources) >= min_required:
                                    break

            except Exception as e:
                logger.warning(f"Enhanced search failed for query '{query}': {str(e)}")
                continue

        logger.info(f"Enhanced search found {len(additional_sources)} additional sources for topic '{topic}'")
        return additional_sources

    async def _generate_research_draft(self, topic: str, research_data: List[Dict[str, Any]], main_query: str, language_code: Optional[str] = None) -> str:
        min_sources_required = getattr(self.config, 'min_sources_per_topic', 2)

        if not research_data:
            # If no data at all, generate a basic research framework
            logger.warning(f"No research data available for topic: {topic}. Generating basic framework.")
            return await self._generate_basic_research_framework(topic, main_query, language_code)

        if len(research_data) < min_sources_required:
            logger.warning(f"Only {len(research_data)} sources found for topic '{topic}', below minimum of {min_sources_required}")

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

    async def _generate_basic_research_framework(self, topic: str, main_query: str, language_code: Optional[str] = None) -> str:
        """Generate a basic research framework when no sources are available"""

        # Get localized prompts for basic framework generation
        system_prompt, user_prompt = self.prompt_manager.format_prompt(
            PromptType.RESEARCH_SUMMARY,  # Reuse existing prompt type
            language_code=language_code,
            query=main_query,
            content_summary=f"Research topic: {topic}. No specific sources available, generate a comprehensive research framework based on general knowledge."
        )

        try:
            framework = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )

            # Add disclaimer about limited sources
            disclaimer = "\n\n**Note: This section is based on general knowledge due to limited available sources. Further research is recommended for comprehensive coverage.**"
            return framework + disclaimer

        except Exception as e:
            logger.error(f"Failed to generate basic research framework for topic {topic}: {str(e)}")
            # Return a minimal but structured response
            return f"""## {topic}

This research area requires further investigation. Key aspects to explore include:

1. **Definition and Overview**: Understanding the fundamental concepts of {topic}
2. **Current State**: Examining the current developments and applications
3. **Challenges and Opportunities**: Identifying key challenges and potential opportunities
4. **Future Directions**: Exploring potential future developments and research directions

**Note: This framework is generated due to limited available sources. Comprehensive research with additional sources is recommended.**"""

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
