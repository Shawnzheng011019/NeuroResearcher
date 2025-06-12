import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
import re
import random
import time
from abc import ABC, abstractmethod
from collections import defaultdict

logger = logging.getLogger(__name__)


class SmartWebScraperTool:
    def __init__(self, timeout: int = 30, max_content_length: int = 50000):
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.failed_domains = defaultdict(int)
        self.domain_failure_threshold = 3
        self.retry_delays = [1, 2, 5]  # Progressive retry delays

        # Enhanced headers to avoid detection
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        # Alternative user agents for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0'
        ]
    
    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped due to repeated failures"""
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        failure_count = self.failed_domains.get(domain, 0)
        return failure_count >= self.domain_failure_threshold

    def _record_failure(self, url: str):
        """Record a failure for the domain"""
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        self.failed_domains[domain] += 1

    def _get_random_headers(self) -> Dict[str, str]:
        """Get randomized headers to avoid detection"""
        headers = self.headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        return headers

    async def scrape_url(self, url: str, max_retries: int = 3) -> Dict[str, Any]:
        """Scrape URL with intelligent retry and failure handling"""

        # Skip if domain has failed too many times
        if self._should_skip_url(url):
            logger.info(f"Skipping {url} due to repeated domain failures")
            return {"url": url, "status": "skipped", "error": "domain_blocked"}

        last_error = None

        for attempt in range(max_retries):
            try:
                # Add random delay to avoid rate limiting
                if attempt > 0:
                    delay = self.retry_delays[min(attempt - 1, len(self.retry_delays) - 1)]
                    await asyncio.sleep(delay + random.uniform(0, 1))

                # Use randomized headers
                headers = self._get_random_headers()
                timeout = aiohttp.ClientTimeout(total=self.timeout)

                async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.text()

                            # Limit content length to prevent memory issues
                            if len(content) > self.max_content_length:
                                content = content[:self.max_content_length]

                            extracted_data = self._extract_content(content, url)
                            extracted_data["url"] = url
                            extracted_data["status"] = "success"
                            extracted_data["attempts"] = attempt + 1

                            logger.info(f"Successfully scraped: {url} (attempt {attempt + 1})")
                            return extracted_data

                        elif response.status in [403, 429]:
                            # Anti-crawler or rate limiting - try with longer delay
                            logger.warning(f"Anti-crawler detected for {url}: HTTP {response.status}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(random.uniform(5, 10))
                                continue
                            else:
                                self._record_failure(url)
                                return {"url": url, "status": "failed", "error": f"HTTP {response.status}", "attempts": attempt + 1}

                        elif response.status >= 500:
                            # Server error - retry
                            logger.warning(f"Server error for {url}: HTTP {response.status}")
                            last_error = f"HTTP {response.status}"
                            continue

                        else:
                            # Other client errors - don't retry
                            logger.warning(f"Failed to scrape {url}: HTTP {response.status}")
                            return {"url": url, "status": "failed", "error": f"HTTP {response.status}", "attempts": attempt + 1}

            except asyncio.TimeoutError:
                logger.warning(f"Timeout scraping {url} (attempt {attempt + 1})")
                last_error = "timeout"
                continue
            except Exception as e:
                logger.error(f"Error scraping {url} (attempt {attempt + 1}): {str(e)}")
                last_error = str(e)
                continue

        # All retries failed
        self._record_failure(url)
        return {"url": url, "status": "failed", "error": last_error, "attempts": max_retries}
    
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
    
    async def scrape_multiple(self, urls: List[str], max_concurrent: int = 5,
                             min_success_rate: float = 0.3) -> List[Dict[str, Any]]:
        """Scrape multiple URLs with intelligent failure handling and source switching"""

        # Sort URLs by domain priority (if available)
        prioritized_urls = self._prioritize_urls(urls)

        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_with_semaphore(url):
            async with semaphore:
                # Add small random delay to avoid overwhelming servers
                await asyncio.sleep(random.uniform(0.1, 0.5))
                return await self.scrape_url(url)

        # Process URLs in batches to allow for adaptive strategy
        batch_size = max(5, len(prioritized_urls) // 3)
        all_results = []
        successful_count = 0

        for i in range(0, len(prioritized_urls), batch_size):
            batch_urls = prioritized_urls[i:i + batch_size]

            # Process current batch
            tasks = [scrape_with_semaphore(url) for url in batch_urls]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process batch results
            batch_successful = 0
            for result in batch_results:
                if isinstance(result, dict):
                    all_results.append(result)
                    if result.get("status") == "success":
                        batch_successful += 1
                        successful_count += 1
                elif isinstance(result, Exception):
                    logger.error(f"Scraping task failed: {str(result)}")

            # Check if we need to adjust strategy
            current_success_rate = successful_count / len(all_results) if all_results else 0

            if current_success_rate < min_success_rate and i + batch_size < len(prioritized_urls):
                logger.warning(f"Low success rate ({current_success_rate:.2f}), adjusting scraping strategy")
                # Increase delays and reduce concurrency for remaining URLs
                max_concurrent = max(2, max_concurrent // 2)
                semaphore = asyncio.Semaphore(max_concurrent)

        # Separate successful and failed results
        successful_results = [r for r in all_results if r.get("status") == "success"]
        failed_results = [r for r in all_results if r.get("status") != "success"]

        logger.info(f"Scraped {len(successful_results)} out of {len(urls)} URLs successfully")
        logger.info(f"Failed domains: {dict(self.failed_domains)}")

        # If success rate is too low, suggest alternative sources
        if len(successful_results) / len(urls) < min_success_rate:
            logger.warning(f"Low overall success rate. Consider using alternative content sources.")
            self._suggest_alternatives(failed_results)

        return all_results

    def _prioritize_urls(self, urls: List[str]) -> List[str]:
        """Sort URLs by reliability and priority"""
        def get_priority_score(url):
            domain = urlparse(url).netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]

            # Higher score for reliable domains, lower for failed domains
            base_score = 5  # Default priority
            failure_penalty = self.failed_domains.get(domain, 0)

            # Known reliable domains get higher scores
            reliable_domains = {
                'arxiv.org': 10, 'github.com': 8, 'stackoverflow.com': 7,
                'wikipedia.org': 7, 'blog.csdn.net': 6, 'medium.com': 6
            }

            if domain in reliable_domains:
                base_score = reliable_domains[domain]

            return max(1, base_score - failure_penalty)

        return sorted(urls, key=get_priority_score, reverse=True)

    def _suggest_alternatives(self, failed_results: List[Dict[str, Any]]):
        """Suggest alternative content sources based on failed attempts"""
        failed_domains = set()
        for result in failed_results:
            if result.get("status") == "failed":
                domain = urlparse(result.get("url", "")).netloc.lower()
                if domain.startswith('www.'):
                    domain = domain[4:]
                failed_domains.add(domain)

        if 'zhihu.com' in failed_domains or 'zhuanlan.zhihu.com' in failed_domains:
            logger.info("Suggestion: Consider using CSDN, GitHub, or academic sources instead of Zhihu")

        if len(failed_domains) > 3:
            logger.info("Suggestion: High failure rate detected. Consider enabling local document search or using different search terms")


# Backward compatibility alias
WebScraperTool = SmartWebScraperTool


class SmartContentExtractorTool:
    def __init__(self):
        self.min_content_length = 100
        self.max_content_length = 10000

        # Domain-specific quality indicators
        self.quality_indicators = {
            'academic': ['abstract', 'introduction', 'methodology', 'results', 'conclusion', 'references'],
            'technical': ['code', 'implementation', 'example', 'tutorial', 'documentation'],
            'news': ['published', 'author', 'source', 'date'],
            'general': ['overview', 'summary', 'details', 'information']
        }

        # Domain reliability scores
        self.domain_reliability = {
            'arxiv.org': 0.95, 'github.com': 0.9, 'stackoverflow.com': 0.85,
            'wikipedia.org': 0.8, 'blog.csdn.net': 0.7, 'medium.com': 0.75,
            'zhihu.com': 0.5, 'zhuanlan.zhihu.com': 0.5
        }

    def extract_relevant_content(self, scraped_data: List[Dict[str, Any]], query: str,
                                min_quality_score: float = 0.3) -> List[Dict[str, Any]]:
        """Extract relevant content with enhanced quality assessment"""
        relevant_content = []
        query_terms = query.lower().split()

        successful_data = [data for data in scraped_data if data.get("status") == "success"]
        failed_data = [data for data in scraped_data if data.get("status") != "success"]

        logger.info(f"Processing {len(successful_data)} successful and {len(failed_data)} failed scraping results")

        for data in successful_data:
            content = data.get("content", "")
            title = data.get("title", "")
            url = data.get("url", "")

            # Skip if content is too short or too long
            if len(content) < self.min_content_length or len(content) > self.max_content_length:
                continue

            # Calculate comprehensive quality score
            relevance_score = self._calculate_relevance(content, title, query_terms)
            quality_score = self._calculate_quality_score(content, title, url, data.get("metadata", {}))
            domain_score = self._get_domain_reliability_score(url)

            # Combined score with weights
            combined_score = (relevance_score * 0.5 + quality_score * 0.3 + domain_score * 0.2)

            if combined_score > min_quality_score:
                extracted = {
                    "url": url,
                    "title": title,
                    "content": content[:self.max_content_length],
                    "relevance_score": relevance_score,
                    "quality_score": quality_score,
                    "domain_score": domain_score,
                    "combined_score": combined_score,
                    "word_count": data.get("word_count", 0),
                    "domain": data.get("domain", ""),
                    "metadata": data.get("metadata", {}),
                    "scraping_attempts": data.get("attempts", 1)
                }
                relevant_content.append(extracted)

        # Sort by combined score
        relevant_content.sort(key=lambda x: x["combined_score"], reverse=True)

        # Log quality distribution
        if relevant_content:
            avg_quality = sum(item["quality_score"] for item in relevant_content) / len(relevant_content)
            avg_relevance = sum(item["relevance_score"] for item in relevant_content) / len(relevant_content)
            logger.info(f"Extracted {len(relevant_content)} relevant content pieces. "
                       f"Avg quality: {avg_quality:.2f}, Avg relevance: {avg_relevance:.2f}")
        else:
            logger.warning("No relevant content extracted. Consider adjusting quality thresholds or search terms.")
            # Suggest fallback strategies
            self._suggest_fallback_strategies(failed_data, query)

        return relevant_content

    def _calculate_quality_score(self, content: str, title: str, url: str, metadata: Dict[str, Any]) -> float:
        """Calculate content quality score based on multiple factors"""
        score = 0.0
        content_lower = content.lower()
        title_lower = title.lower()

        # Length factor (optimal range)
        length_score = min(1.0, len(content) / 2000)  # Normalize to 2000 chars
        score += length_score * 0.2

        # Structure indicators
        structure_indicators = ['introduction', 'conclusion', 'summary', 'abstract', 'overview']
        structure_score = sum(1 for indicator in structure_indicators if indicator in content_lower) / len(structure_indicators)
        score += structure_score * 0.3

        # Technical depth indicators
        technical_indicators = ['method', 'approach', 'algorithm', 'implementation', 'analysis', 'result']
        technical_score = sum(1 for indicator in technical_indicators if indicator in content_lower) / len(technical_indicators)
        score += technical_score * 0.2

        # Metadata quality
        metadata_score = 0.0
        if metadata.get('headings'):
            metadata_score += 0.3  # Has structured headings
        if any(key in metadata for key in ['author', 'date', 'published']):
            metadata_score += 0.2  # Has authorship info
        score += metadata_score * 0.3

        return min(1.0, score)

    def _get_domain_reliability_score(self, url: str) -> float:
        """Get reliability score based on domain"""
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        return self.domain_reliability.get(domain, 0.5)  # Default to medium reliability

    def _suggest_fallback_strategies(self, failed_data: List[Dict[str, Any]], query: str):
        """Suggest alternative strategies when content extraction fails"""
        failed_domains = set()
        for data in failed_data:
            if data.get("url"):
                domain = urlparse(data["url"]).netloc.lower()
                if domain.startswith('www.'):
                    domain = domain[4:]
                failed_domains.add(domain)

        suggestions = []

        if 'zhihu.com' in failed_domains or 'zhuanlan.zhihu.com' in failed_domains:
            suggestions.append("Try searching with English terms to access international sources")
            suggestions.append("Consider using academic databases like arXiv or Google Scholar")

        if len(failed_domains) > 2:
            suggestions.append("Enable local document search if available")
            suggestions.append("Try broader or more specific search terms")
            suggestions.append("Consider using different search engines")

        for suggestion in suggestions:
            logger.info(f"Fallback suggestion: {suggestion}")


    def _calculate_relevance(self, content: str, title: str, query_terms: List[str]) -> float:
        """Calculate relevance score based on query term matches"""
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
        """Create a summary from multiple content pieces"""
        if not content_list:
            return ""

        # Combine all content, prioritizing by quality score
        combined_content = []
        for item in sorted(content_list, key=lambda x: x.get("combined_score", 0), reverse=True):
            title = item.get("title", "")
            content = item.get("content", "")
            url = item.get("url", "")
            quality_score = item.get("quality_score", 0)

            if title and content:
                combined_content.append(
                    f"Title: {title}\n"
                    f"URL: {url}\n"
                    f"Quality Score: {quality_score:.2f}\n"
                    f"Content: {content[:500]}...\n"
                )

        summary = "\n".join(combined_content)

        # Truncate if too long
        if len(summary) > max_summary_length:
            summary = summary[:max_summary_length] + "..."

        return summary


# Backward compatibility alias
ContentExtractorTool = SmartContentExtractorTool
