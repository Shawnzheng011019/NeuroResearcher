import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
import re
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class WebScraperTool:
    def __init__(self, timeout: int = 30, max_content_length: int = 50000):
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }
    
    async def scrape_url(self, url: str) -> Dict[str, Any]:
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout, headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Limit content length to prevent memory issues
                        if len(content) > self.max_content_length:
                            content = content[:self.max_content_length]
                        
                        extracted_data = self._extract_content(content, url)
                        extracted_data["url"] = url
                        extracted_data["status"] = "success"
                        
                        logger.info(f"Successfully scraped: {url}")
                        return extracted_data
                    else:
                        logger.warning(f"Failed to scrape {url}: HTTP {response.status}")
                        return {"url": url, "status": "failed", "error": f"HTTP {response.status}"}
                        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout scraping {url}")
            return {"url": url, "status": "failed", "error": "timeout"}
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return {"url": url, "status": "failed", "error": str(e)}
    
    def _extract_content(self, html_content: str, url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Extract title
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
        
        # Extract main content
        content = ""
        
        # Try to find main content areas
        main_selectors = [
            'main', 'article', '[role="main"]', 
            '.content', '.main-content', '.article-content',
            '.post-content', '.entry-content'
        ]
        
        main_content = None
        for selector in main_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if main_content:
            content = main_content.get_text(separator=' ', strip=True)
        else:
            # Fallback to body content
            body = soup.find('body')
            if body:
                content = body.get_text(separator=' ', strip=True)
        
        # Clean up content
        content = self._clean_text(content)
        
        # Extract metadata
        metadata = self._extract_metadata(soup)
        
        return {
            "title": title,
            "content": content,
            "metadata": metadata,
            "word_count": len(content.split()),
            "domain": urlparse(url).netloc
        }
    
    def _clean_text(self, text: str) -> str:
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\{\}\"\'\/\@\#\$\%\&\*\+\=\<\>\|\~\`]', '', text)
        return text.strip()
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        metadata = {}
        
        # Extract meta tags
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            name = tag.get('name') or tag.get('property')
            content = tag.get('content')
            if name and content:
                metadata[name] = content
        
        # Extract headings
        headings = []
        for i in range(1, 7):
            heading_tags = soup.find_all(f'h{i}')
            for heading in heading_tags:
                headings.append({
                    'level': i,
                    'text': heading.get_text().strip()
                })
        metadata['headings'] = headings
        
        return metadata
    
    async def scrape_multiple(self, urls: List[str], max_concurrent: int = 5) -> List[Dict[str, Any]]:
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url):
            async with semaphore:
                return await self.scrape_url(url)
        
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return successful results
        successful_results = []
        for result in results:
            if isinstance(result, dict):
                successful_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Scraping task failed: {str(result)}")
        
        logger.info(f"Scraped {len(successful_results)} out of {len(urls)} URLs successfully")
        return successful_results


class ContentExtractorTool:
    def __init__(self):
        self.min_content_length = 100
        self.max_content_length = 10000
    
    def extract_relevant_content(self, scraped_data: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        relevant_content = []
        query_terms = query.lower().split()
        
        for data in scraped_data:
            if data.get("status") != "success":
                continue
            
            content = data.get("content", "")
            title = data.get("title", "")
            
            # Skip if content is too short or too long
            if len(content) < self.min_content_length or len(content) > self.max_content_length:
                continue
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance(content, title, query_terms)
            
            if relevance_score > 0.1:  # Minimum relevance threshold
                extracted = {
                    "url": data.get("url"),
                    "title": title,
                    "content": content[:self.max_content_length],  # Truncate if needed
                    "relevance_score": relevance_score,
                    "word_count": data.get("word_count", 0),
                    "domain": data.get("domain", ""),
                    "metadata": data.get("metadata", {})
                }
                relevant_content.append(extracted)
        
        # Sort by relevance score
        relevant_content.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        logger.info(f"Extracted {len(relevant_content)} relevant content pieces from {len(scraped_data)} scraped pages")
        return relevant_content
    
    def _calculate_relevance(self, content: str, title: str, query_terms: List[str]) -> float:
        content_lower = content.lower()
        title_lower = title.lower()
        
        # Count term occurrences
        title_matches = sum(1 for term in query_terms if term in title_lower)
        content_matches = sum(1 for term in query_terms if term in content_lower)
        
        # Calculate scores
        title_score = (title_matches / len(query_terms)) * 0.4 if query_terms else 0
        content_score = (content_matches / len(query_terms)) * 0.6 if query_terms else 0
        
        return title_score + content_score
    
    def summarize_content(self, content_list: List[Dict[str, Any]], max_summary_length: int = 2000) -> str:
        if not content_list:
            return ""
        
        # Combine all content
        combined_content = []
        for item in content_list:
            title = item.get("title", "")
            content = item.get("content", "")
            url = item.get("url", "")
            
            if title and content:
                combined_content.append(f"Title: {title}\nURL: {url}\nContent: {content[:500]}...\n")
        
        summary = "\n".join(combined_content)
        
        # Truncate if too long
        if len(summary) > max_summary_length:
            summary = summary[:max_summary_length] + "..."
        
        return summary
