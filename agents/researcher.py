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

            # 2. Web search (always performed unless retriever is "local")
            if self.config.retriever != "local":
                search_results = await self.search_manager.search_with_fallback(query)

                if search_results:
                    # Extract URLs for scraping
                    max_web_results = self.config.max_search_results_per_query
                    if self.use_rag:
                        max_web_results = max_web_results // 2  # Split between local and web

                    urls = [result["url"] for result in search_results[:max_web_results]]

                    # Scrape content from URLs
                    scraped_data = await self.scraper.scrape_multiple(urls, max_concurrent=5)

                    # Extract relevant content
                    web_content = self.content_extractor.extract_relevant_content(scraped_data, query)
                    all_relevant_content.extend(web_content)
                    logger.info(f"Found {len(web_content)} relevant web sources")

            # Check if we have any content
            if not all_relevant_content:
                logger.warning("No research content found from any source")
                state["errors"].append("No research content found")
                return state

            # Generate initial research summary
            initial_research = await self._generate_research_summary(query, all_relevant_content)

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
            # Generate specific queries for the topic
            specific_queries = await self._generate_specific_queries(topic, state["task"].query)

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

                # 2. Web search (if not local-only)
                if self.config.retriever != "local":
                    search_results = await self.search_manager.search_with_fallback(query)

                    if search_results:
                        urls = [result["url"] for result in search_results[:3]]  # Limit for deep research
                        scraped_data = await self.scraper.scrape_multiple(urls, max_concurrent=3)
                        web_content = self.content_extractor.extract_relevant_content(scraped_data, query)
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
            research_draft = await self._generate_research_draft(topic, unique_research_data, state["task"].query)
            
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
    
    async def _generate_research_summary(self, query: str, content_list: List[Dict[str, Any]]) -> str:
        if not content_list:
            return "No relevant content found for the research query."
        
        # Prepare content for summarization
        content_summary = self.content_extractor.summarize_content(content_list, max_summary_length=3000)
        
        system_prompt = """You are a research analyst tasked with creating a comprehensive summary of research findings.
        Your goal is to synthesize information from multiple sources into a coherent, well-structured summary.
        Focus on key insights, important facts, and relevant details that address the research query."""
        
        user_prompt = f"""Research Query: {query}

Research Content from Multiple Sources:
{content_summary}

Please create a comprehensive research summary that:
1. Addresses the main research query
2. Synthesizes key findings from the sources
3. Identifies important patterns or themes
4. Highlights any conflicting information
5. Provides a balanced perspective

Format the summary in clear, well-structured paragraphs."""
        
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
    
    async def _generate_specific_queries(self, topic: str, main_query: str) -> List[str]:
        system_prompt = """You are a research query specialist. Generate specific, targeted search queries 
        that will help gather comprehensive information about a given topic in the context of the main research question."""
        
        user_prompt = f"""Main Research Query: {main_query}
Specific Topic: {topic}

Generate 3-5 specific search queries that would help gather detailed information about this topic 
in relation to the main research question. Each query should be:
1. Specific and focused
2. Likely to return relevant results
3. Different from the others to cover various aspects

Return only the queries, one per line, without numbering or additional text."""
        
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
    
    async def _generate_research_draft(self, topic: str, research_data: List[Dict[str, Any]], main_query: str) -> str:
        if not research_data:
            return f"No research data available for topic: {topic}"
        
        # Prepare research content
        content_summary = self.content_extractor.summarize_content(research_data, max_summary_length=4000)
        
        system_prompt = """You are an expert researcher and writer. Create a comprehensive, well-structured 
        research section that thoroughly covers the given topic based on the provided research data.
        
        Your writing should be:
        - Academically rigorous but accessible
        - Well-organized with clear structure
        - Factual and evidence-based
        - Properly contextualized within the main research question"""
        
        user_prompt = f"""Main Research Question: {main_query}
Section Topic: {topic}

Research Data:
{content_summary}

Write a comprehensive research section about "{topic}" that:
1. Provides thorough coverage of the topic
2. Integrates findings from multiple sources
3. Maintains focus on how this topic relates to the main research question
4. Uses clear, professional language
5. Structures information logically with appropriate subheadings if needed
6. Includes specific examples and evidence where relevant

The section should be substantial (800-1200 words) and serve as a complete treatment of this aspect of the research."""
        
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
