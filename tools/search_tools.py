import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from duckduckgo_search import DDGS
import json
import logging

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


class SearchManager:
    def __init__(self, search_tools: List[SearchTool]):
        self.search_tools = search_tools
    
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
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        logger.info(f"Combined search completed: {len(unique_results)} unique results for query '{query}'")
        return unique_results
    
    async def search_with_fallback(self, query: str) -> List[Dict[str, Any]]:
        for tool in self.search_tools:
            try:
                results = await tool.search(query)
                if results:
                    return results
            except Exception as e:
                logger.warning(f"Search tool {type(tool).__name__} failed, trying next: {str(e)}")
                continue
        
        logger.error(f"All search tools failed for query '{query}'")
        return []


def create_search_manager(config) -> SearchManager:
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
    
    return SearchManager(tools)
