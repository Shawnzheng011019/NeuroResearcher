import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from duckduckgo_search import DDGS
import json
import logging
import random
from urllib.parse import urlparse
from collections import defaultdict

logger = logging.getLogger(__name__)


class SearchTool(ABC):
    def __init__(self, max_results: int = 10):
        self.max_results = max_results
    
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        pass
    
    def format_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        formatted_results = []
        for result in results[:self.max_results]:
            formatted_result = {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("snippet", ""),
                "source": result.get("source", "unknown")
            }
            formatted_results.append(formatted_result)
        return formatted_results


class DuckDuckGoSearchTool(SearchTool):
    def __init__(self, max_results: int = 10):
        super().__init__(max_results)
        self.ddgs = DDGS()
    
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        try:
            results = []
            search_results = self.ddgs.text(query, max_results=self.max_results)
            
            for result in search_results:
                formatted_result = {
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", ""),
                    "source": "duckduckgo"
                }
                results.append(formatted_result)
            
            logger.info(f"DuckDuckGo search completed: {len(results)} results for query '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed for query '{query}': {str(e)}")
            return []


class GoogleSearchTool(SearchTool):
    def __init__(self, api_key: str, cx_id: str, max_results: int = 10):
        super().__init__(max_results)
        self.api_key = api_key
        self.cx_id = cx_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"
    
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        try:
            params = {
                "key": self.api_key,
                "cx": self.cx_id,
                "q": query,
                "num": min(self.max_results, 10)  # Google API max is 10 per request
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        for item in data.get("items", []):
                            formatted_result = {
                                "title": item.get("title", ""),
                                "url": item.get("link", ""),
                                "snippet": item.get("snippet", ""),
                                "source": "google"
                            }
                            results.append(formatted_result)
                        
                        logger.info(f"Google search completed: {len(results)} results for query '{query}'")
                        return results
                    else:
                        logger.error(f"Google search API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Google search failed for query '{query}': {str(e)}")
            return []


class ContentSourceManager:
    def __init__(self):
        # Define reliable content sources with priority scores
        self.reliable_sources = {
            # Academic and research sources (highest priority)
            'arxiv.org': {'priority': 10, 'type': 'academic', 'reliability': 0.95},
            'scholar.google.com': {'priority': 10, 'type': 'academic', 'reliability': 0.95},
            'researchgate.net': {'priority': 9, 'type': 'academic', 'reliability': 0.9},
            'ieee.org': {'priority': 9, 'type': 'academic', 'reliability': 0.9},
            'acm.org': {'priority': 9, 'type': 'academic', 'reliability': 0.9},
            'nature.com': {'priority': 9, 'type': 'academic', 'reliability': 0.9},
            'science.org': {'priority': 9, 'type': 'academic', 'reliability': 0.9},
            'sciencedirect.com': {'priority': 8, 'type': 'academic', 'reliability': 0.85},
            'springer.com': {'priority': 8, 'type': 'academic', 'reliability': 0.85},
            'wiley.com': {'priority': 8, 'type': 'academic', 'reliability': 0.85},

            # Technical blogs and documentation (high priority)
            'github.com': {'priority': 8, 'type': 'technical', 'reliability': 0.8},
            'stackoverflow.com': {'priority': 7, 'type': 'technical', 'reliability': 0.8},
            'medium.com': {'priority': 6, 'type': 'technical', 'reliability': 0.7},
            'towardsdatascience.com': {'priority': 7, 'type': 'technical', 'reliability': 0.8},
            'blog.csdn.net': {'priority': 6, 'type': 'technical', 'reliability': 0.7},

            # News and general sources (medium priority)
            'wikipedia.org': {'priority': 7, 'type': 'general', 'reliability': 0.8},
            'bbc.com': {'priority': 6, 'type': 'news', 'reliability': 0.75},
            'reuters.com': {'priority': 6, 'type': 'news', 'reliability': 0.75},
            'techcrunch.com': {'priority': 5, 'type': 'tech_news', 'reliability': 0.7},

            # Problematic sources (lower priority or blocked)
            'zhihu.com': {'priority': 3, 'type': 'social', 'reliability': 0.5, 'issues': ['anti_crawler']},
            'zhuanlan.zhihu.com': {'priority': 3, 'type': 'social', 'reliability': 0.5, 'issues': ['anti_crawler']},
            'quora.com': {'priority': 4, 'type': 'social', 'reliability': 0.6},
        }

        # Track failed domains to avoid repeated attempts
        self.failed_domains = defaultdict(int)
        self.domain_failure_threshold = 3

    def get_domain_priority(self, url: str) -> int:
        domain = urlparse(url).netloc.lower()
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]

        source_info = self.reliable_sources.get(domain, {'priority': 5})

        # Reduce priority for frequently failing domains
        failure_count = self.failed_domains.get(domain, 0)
        priority_penalty = min(failure_count, 5)  # Max penalty of 5

        return max(1, source_info['priority'] - priority_penalty)

    def get_domain_reliability(self, url: str) -> float:
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        source_info = self.reliable_sources.get(domain, {'reliability': 0.5})
        return source_info['reliability']

    def has_known_issues(self, url: str) -> List[str]:
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        source_info = self.reliable_sources.get(domain, {})
        return source_info.get('issues', [])

    def record_failure(self, url: str):
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        self.failed_domains[domain] += 1

    def should_skip_domain(self, url: str) -> bool:
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        failure_count = self.failed_domains.get(domain, 0)
        return failure_count >= self.domain_failure_threshold


class SearchManager:
    def __init__(self, search_tools: List[SearchTool]):
        self.search_tools = search_tools
        self.source_manager = ContentSourceManager()

    async def search_all(self, query: str) -> List[Dict[str, Any]]:
        all_results = []
        tasks = []

        for tool in self.search_tools:
            task = asyncio.create_task(tool.search(query))
            tasks.append(task)

        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        for results in results_list:
            if isinstance(results, list):
                all_results.extend(results)
            elif isinstance(results, Exception):
                logger.error(f"Search tool failed: {str(results)}")

        # Remove duplicates and prioritize results
        unique_results = self._prioritize_and_deduplicate(all_results)

        logger.info(f"Combined search completed: {len(unique_results)} unique results for query '{query}'")
        return unique_results

    async def search_with_fallback(self, query: str) -> List[Dict[str, Any]]:
        for tool in self.search_tools:
            try:
                results = await tool.search(query)
                if results:
                    # Prioritize results even for single tool
                    prioritized_results = self._prioritize_and_deduplicate(results)
                    return prioritized_results
            except Exception as e:
                logger.warning(f"Search tool {type(tool).__name__} failed, trying next: {str(e)}")
                continue

        logger.error(f"All search tools failed for query '{query}'")
        return []

    async def search_with_diversification(self, query: str, max_per_domain: int = 2) -> List[Dict[str, Any]]:
        """Search with domain diversification to reduce dependency on single sources"""
        all_results = await self.search_all(query)

        # Group results by domain
        domain_results = defaultdict(list)
        for result in all_results:
            domain = urlparse(result.get('url', '')).netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            domain_results[domain].append(result)

        # Select diverse results
        diversified_results = []

        # First, add high-priority sources
        for domain, results in sorted(domain_results.items(),
                                    key=lambda x: max(self.source_manager.get_domain_priority(r['url']) for r in x[1]),
                                    reverse=True):

            # Skip domains with known issues or too many failures
            if any(self.source_manager.should_skip_domain(r['url']) for r in results):
                logger.info(f"Skipping domain {domain} due to repeated failures")
                continue

            # Add up to max_per_domain results from this domain
            selected_count = 0
            for result in results:
                if selected_count < max_per_domain:
                    result['domain_priority'] = self.source_manager.get_domain_priority(result['url'])
                    result['domain_reliability'] = self.source_manager.get_domain_reliability(result['url'])
                    diversified_results.append(result)
                    selected_count += 1

        logger.info(f"Diversified search: {len(diversified_results)} results from {len(domain_results)} domains")
        return diversified_results

    def _prioritize_and_deduplicate(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates and sort by source priority"""
        seen_urls = set()
        unique_results = []

        for result in results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                # Add priority and reliability scores
                result['domain_priority'] = self.source_manager.get_domain_priority(url)
                result['domain_reliability'] = self.source_manager.get_domain_reliability(url)
                result['known_issues'] = self.source_manager.has_known_issues(url)
                unique_results.append(result)

        # Sort by priority (higher is better)
        unique_results.sort(key=lambda x: x.get('domain_priority', 5), reverse=True)

        return unique_results


def create_search_manager(config) -> SearchManager:
    """Create an intelligent search manager with source diversification"""
    tools = []

    # Always include DuckDuckGo as fallback
    tools.append(DuckDuckGoSearchTool(max_results=config.max_search_results_per_query))

    # Add Google if API keys are available
    if config.google_api_key_search and config.google_cx_id:
        tools.append(GoogleSearchTool(
            api_key=config.google_api_key_search,
            cx_id=config.google_cx_id,
            max_results=config.max_search_results_per_query
        ))

    search_manager = SearchManager(tools)

    # Log the configuration
    logger.info(f"Created search manager with {len(tools)} search tools")
    logger.info(f"Content source manager initialized with {len(search_manager.source_manager.reliable_sources)} known sources")

    return search_manager
