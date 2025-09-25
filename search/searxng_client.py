import os
import re
import time
from typing import Any

import requests

from usage_tracker import APIProvider, track_api_call


class SearXNGSearchClient:
    """Client for searching using SearXNG local instance"""

    def __init__(self, searxng_url: str = None):
        """
        Initialize SearXNG client

        Args:
            searxng_url: URL of the SearXNG instance (defaults to environment variable)
        """
        self.searxng_url = searxng_url or os.getenv("SEARXNG_URL", "http://localhost:8080")

        # Validate SearXNG instance
        if not self._validate_searxng_instance():
            raise ValueError(f"SearXNG instance not accessible at {self.searxng_url}")

    def _validate_searxng_instance(self) -> bool:
        """Validate that the SearXNG instance is accessible"""
        try:
            response = requests.get(f"{self.searxng_url}/config", timeout=10)
            if response.status_code == 200:
                config = response.json()
                print(
                    f"✅ SearXNG instance validated: {config.get('brand', {}).get('NAME', 'SearXNG')}"
                )
                return True
            return False
        except Exception as e:
            print(f"❌ SearXNG validation failed: {e}")
            return False

    def search(self, query: str, num_results: int = 5) -> list[dict[str, str]]:
        """
        Search using SearXNG with academic focus

        Args:
            query: Search query string
            num_results: Maximum number of results to return

        Returns:
            List of search results with title, url, and content
        """
        start_time = time.time()
        success = True
        error_message = None
        results = []

        try:
            # Prepare search parameters - use HTML instead of JSON to avoid bot detection
            search_params = {
                "q": query,
                "engines": ["google", "google_scholar", "arxiv", "pubmed", "crossref", "doaj"],
                "time_range": None,  # No time restriction
                "safesearch": 0,  # No safe search restriction
                "language": "en",
                "pageno": 1,
            }

            # Make the search request with proper headers to avoid bot detection
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; Citation-Needed/1.0)",
                "Accept": "application/json, text/javascript, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "X-Forwarded-For": "127.0.0.1",
                "X-Real-IP": "127.0.0.1",
            }

            response = requests.get(
                f"{self.searxng_url}/search", params=search_params, headers=headers, timeout=30
            )

            if response.status_code != 200:
                success = False
                error_message = f"SearXNG search failed with status {response.status_code}"
                print(error_message)
                return []

            # Parse HTML results instead of JSON
            try:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(response.content, "html.parser")

                # Find all result elements
                result_elements = soup.select(".result")

                for result_elem in result_elements[:num_results]:
                    # Extract title
                    title_elem = result_elem.select_one("h3 a, .result_title a")
                    title = title_elem.get_text(strip=True) if title_elem else "No title"

                    # Extract URL
                    url = title_elem.get("href", "") if title_elem else ""

                    # Extract content/description
                    content_elem = result_elem.select_one(".result-content, .content, .description")
                    content = content_elem.get_text(strip=True) if content_elem else ""

                    if len(content) > 1000:
                        content = content[:1000] + "..."

                    processed_result = {
                        "title": title,
                        "url": url,
                        "content": content,
                        "source": "searxng_html",
                        "metadata": {"engine": "html_parser", "type": "general"},
                        "confidence": 0.7,
                    }

                    results.append(processed_result)

            except ImportError:
                # Fallback if BeautifulSoup is not available
                print("BeautifulSoup not available, using simple text extraction")
                # Simple regex-based extraction as fallback
                import re

                # Look for result patterns in HTML
                result_pattern = r'<div class="result"[^>]*>.*?<h3[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>.*?</h3>.*?<p[^>]*>([^<]*)</p>'
                matches = re.findall(result_pattern, response.text, re.DOTALL)

                for url, title, content in matches[:num_results]:
                    title = re.sub(r"<[^>]+>", "", title).strip()
                    content = re.sub(r"<[^>]+>", "", content).strip()

                    if len(content) > 1000:
                        content = content[:1000] + "..."

                    processed_result = {
                        "title": title,
                        "url": url,
                        "content": content,
                        "source": "searxng_html_fallback",
                        "metadata": {"engine": "regex_parser", "type": "general"},
                        "confidence": 0.6,
                    }

                    results.append(processed_result)

            print(f"🔍 SearXNG found {len(results)} results for query: {query[:50]}...")
            return results

        except Exception as e:
            success = False
            error_message = str(e)
            print(f"SearXNG search error: {e}")
            return []

        finally:
            duration = time.time() - start_time
            track_api_call(
                provider=APIProvider.SEARXNG,
                endpoint="search",
                duration=duration,
                success=success,
                error_message=error_message,
                metadata={
                    "query": query,
                    "num_results": num_results,
                    "results_count": len(results),
                    "engines": ["google", "google_scholar", "arxiv", "pubmed", "crossref", "doaj"],
                },
            )

    def _calculate_searxng_confidence(self, result: dict[str, Any]) -> float:
        """Calculate confidence score for SearXNG result"""
        confidence = 0.5  # Base confidence

        # Boost for academic engines
        engine = result.get("engine", "")
        if engine in ["google_scholar", "arxiv", "pubmed", "crossref", "doaj"]:
            confidence += 0.3

        # Boost for content quality
        content = (
            result.get("content", "") or result.get("snippet", "") or result.get("abstract", "")
        )
        if len(content) > 100:
            confidence += 0.1

        # Boost for published papers
        if result.get("publishedDate"):
            confidence += 0.1

        # Boost for academic domains
        url = result.get("url", "")
        academic_domains = [
            ".edu",
            ".ac.",
            ".gov",
            "arxiv.org",
            "pubmed.ncbi.nlm.nih.gov",
            "doi.org",
        ]
        if any(domain in url for domain in academic_domains):
            confidence += 0.2

        return min(1.0, confidence)

    def academic_search(self, query: str, num_results: int = 5) -> list[dict[str, str]]:
        """
        Specialized academic search using SearXNG

        Args:
            query: Search query string
            num_results: Maximum number of results to return

        Returns:
            List of academic search results
        """
        # Enhance query for academic search
        academic_engines = [
            "google_scholar",
            "arxiv",
            "pubmed",
            "crossref",
            "doaj",
            "semanticscholar",
        ]

        search_params = {
            "q": query,
            "engines": academic_engines,
            "format": "json",
            "time_range": None,
            "safesearch": 0,
            "language": "en",
            "pageno": 1,
        }

        try:
            # Make the search request with proper headers to avoid bot detection
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; Citation-Needed/1.0)",
                "Accept": "application/json, text/javascript, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "X-Forwarded-For": "127.0.0.1",
                "X-Real-IP": "127.0.0.1",
            }

            response = requests.get(
                f"{self.searxng_url}/search", params=search_params, headers=headers, timeout=30
            )

            if response.status_code != 200:
                return []

            data = response.json()
            results = []

            for result in data.get("results", [])[:num_results]:
                content = (
                    result.get("content", "")
                    or result.get("snippet", "")
                    or result.get("abstract", "")
                )
                if len(content) > 1000:
                    content = content[:1000] + "..."

                processed_result = {
                    "title": result.get("title", "No title"),
                    "url": result.get("url", ""),
                    "content": content,
                    "source": "searxng_academic",
                    "metadata": {
                        "engine": result.get("engine", "unknown"),
                        "publishedDate": result.get("publishedDate"),
                        "type": "academic",
                    },
                    "confidence": 0.7,  # Higher base confidence for academic search
                }

                results.append(processed_result)

            print(f"🎓 SearXNG academic search found {len(results)} results")
            return results

        except Exception as e:
            print(f"SearXNG academic search error: {e}")
            return []

    def scrape_url(self, url: str) -> dict[str, str] | None:
        """
        Scrape content from a URL using SearXNG's internal scraping capabilities

        Args:
            url: URL to scrape

        Returns:
            Dictionary with scraped content or None if failed
        """
        try:
            # Check if SearXNG has scraping capability
            scrape_params = {"url": url, "format": "json"}

            response = requests.get(f"{self.searxng_url}/scrape", params=scrape_params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                return {
                    "title": data.get("title", url),
                    "url": url,
                    "content": data.get("content", ""),
                    "source": "searxng_scrape",
                    "confidence": 0.8,
                }

        except Exception as e:
            print(f"SearXNG scraping error: {e}")

        # Fallback to basic HTTP request if SearXNG scraping fails
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; Citation-Needed/1.0)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }

            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                # Simple content extraction (could be improved with proper parsing)
                try:
                    from bs4 import BeautifulSoup

                    soup = BeautifulSoup(response.content, "html.parser")

                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()

                    content = soup.get_text()
                    content = " ".join(content.split())  # Normalize whitespace

                    if len(content) > 2000:
                        content = content[:2000] + "..."

                    return {
                        "title": soup.title.string if soup.title else url,
                        "url": url,
                        "content": content,
                        "source": "searxng_fallback",
                        "confidence": 0.6,
                    }
                except ImportError:
                    # Fallback without BeautifulSoup
                    content = response.text
                    content = " ".join(content.split())  # Normalize whitespace
                    if len(content) > 2000:
                        content = content[:2000] + "..."

                    return {
                        "title": url,
                        "url": url,
                        "content": content,
                        "source": "searxng_basic",
                        "confidence": 0.4,
                    }

        except Exception as e:
            print(f"Fallback scraping error: {e}")

        return None

    def enhanced_citation_search(
        self, citation_text: str, citation_components: dict[str, Any]
    ) -> list[dict[str, str]]:
        """
        Enhanced citation search using SearXNG

        Args:
            citation_text: Full citation text
            citation_components: Parsed citation components

        Returns:
            List of relevant search results
        """
        all_results = []

        # Try direct URL validation first (if available in citation components)
        direct_results = self._try_direct_url_validation(citation_components)
        if direct_results:
            all_results.extend(direct_results)

        # Generate multiple search strategies optimized for SearXNG
        search_queries = []

        # Strategy 1: Full citation text (quoted for exact match)
        if citation_text:
            search_queries.append(f'"{citation_text[:150]}"')

        # Strategy 2: DOI search
        if citation_components.get("doi"):
            search_queries.append(citation_components["doi"])

        # Strategy 3: arXiv search
        if citation_components.get("arxiv_id"):
            search_queries.append(citation_components["arxiv_id"])

        # Strategy 4: Author + Year + Title
        if (
            citation_components.get("first_author")
            and citation_components.get("year")
            and citation_components.get("title")
        ):
            author = citation_components["first_author"]
            year = citation_components["year"]
            title = citation_components["title"]

            # Try different combinations
            search_queries.append(f'{author} {year} "{title[:50]}"')
            search_queries.append(f'"{title}" {author} {year}')

        # Strategy 5: Title search
        if citation_components.get("title"):
            search_queries.append(f'"{citation_components["title"]}"')

        # Strategy 6: Author + Year
        if citation_components.get("first_author") and citation_components.get("year"):
            search_queries.append(
                f"{citation_components['first_author']} {citation_components['year']}"
            )

        # Execute searches with academic focus
        for query in search_queries[:4]:  # Limit to prevent too many requests
            try:
                print(f"🔍 SearXNG query: {query}")
                results = self.academic_search(query, num_results=3)
                all_results.extend(results)
            except Exception as e:
                print(f"SearXNG search error for '{query}': {e}")

        # Remove duplicates and sort by confidence
        unique_results = []
        seen_urls = set()

        for result in all_results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                unique_results.append(result)
                seen_urls.add(url)

        # Sort by confidence score
        unique_results.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        print(f"📊 SearXNG total results: {len(unique_results)}")
        return unique_results[:5]

    def _try_direct_url_validation(
        self, citation_components: dict[str, Any]
    ) -> list[dict[str, str]]:
        """Try direct validation for known academic sources"""
        results = []

        # Try DOI validation
        if citation_components.get("doi"):
            doi_result = self._validate_doi_with_searxng(citation_components["doi"])
            if doi_result:
                results.append(doi_result)

        # Try arXiv validation
        if citation_components.get("arxiv_id"):
            arxiv_result = self._validate_arxiv_with_searxng(citation_components["arxiv_id"])
            if arxiv_result:
                results.append(arxiv_result)

        # Try PubMed validation
        if citation_components.get("pmid"):
            pubmed_result = self._validate_pubmed_with_searxng(citation_components["pmid"])
            if pubmed_result:
                results.append(pubmed_result)

        return results

    def _validate_doi_with_searxng(self, doi: str) -> dict[str, str] | None:
        """Validate DOI using SearXNG"""
        try:
            # Clean DOI
            doi_clean = doi.lower().replace("doi:", "").strip()
            if not doi_clean.startswith("10."):
                return None

            # Search for the DOI
            results = self.search(doi_clean, num_results=1)
            if results:
                result = results[0]
                return {
                    "title": result.get("title", "DOI Validated"),
                    "url": result.get("url", f"https://doi.org/{doi_clean}"),
                    "content": result.get("content", "DOI found via SearXNG"),
                    "metadata": {"type": "doi", "resolved": True},
                    "source": "searxng_doi",
                    "confidence": 0.9,
                }

        except Exception as e:
            print(f"DOI validation error: {e}")

        return None

    def _validate_arxiv_with_searxng(self, arxiv_id: str) -> dict[str, str] | None:
        """Validate arXiv ID using SearXNG"""
        try:
            # Clean arXiv ID
            arxiv_clean = arxiv_id.lower().replace("arxiv:", "").strip()
            if not re.match(r"^\d+\.\d+", arxiv_clean):
                return None

            # Search for the arXiv ID
            results = self.search(arxiv_clean, num_results=1)
            if results and "arxiv.org" in results[0].get("url", ""):
                result = results[0]
                return {
                    "title": result.get("title", "arXiv Validated"),
                    "url": result.get("url", f"https://arxiv.org/abs/{arxiv_clean}"),
                    "content": result.get("content", "arXiv paper found via SearXNG"),
                    "metadata": {"type": "arxiv", "resolved": True},
                    "source": "searxng_arxiv",
                    "confidence": 0.95,
                }

        except Exception as e:
            print(f"arXiv validation error: {e}")

        return None

    def _validate_pubmed_with_searxng(self, pmid: str) -> dict[str, str] | None:
        """Validate PubMed ID using SearXNG"""
        try:
            # Clean PMID
            pmid_clean = pmid.lower().replace("pmid:", "").strip()
            if not pmid_clean.isdigit():
                return None

            # Search for the PMID
            results = self.search(pmid_clean, num_results=1)
            if results and "pubmed.ncbi.nlm.nih.gov" in results[0].get("url", ""):
                result = results[0]
                return {
                    "title": result.get("title", "PubMed Validated"),
                    "url": result.get("url", f"https://pubmed.ncbi.nlm.nih.gov/{pmid_clean}/"),
                    "content": result.get("content", "PubMed article found via SearXNG"),
                    "metadata": {"type": "pubmed", "resolved": True},
                    "source": "searxng_pubmed",
                    "confidence": 0.93,
                }

        except Exception as e:
            print(f"PubMed validation error: {e}")

        return None

    def smart_citation_search(
        self, structured_citation, citation_text: str = ""
    ) -> list[dict[str, str]]:
        """
        Smart citation search using SearXNG

        Args:
            structured_citation: StructuredCitation object
            citation_text: Original citation text

        Returns:
            List of search results with confidence scores
        """
        # Convert to dict for compatibility
        citation_dict = {
            "doi": structured_citation.doi,
            "arxiv_id": structured_citation.arxiv_id,
            "pmid": structured_citation.pmid,
            "title": structured_citation.title,
            "authors": structured_citation.authors,
            "first_author": structured_citation.first_author,
            "year": structured_citation.year,
            "journal": structured_citation.journal,
            "conference": structured_citation.conference,
        }

        return self.enhanced_citation_search(citation_text, citation_dict)

    def validate_setup(self) -> bool:
        """Validate that SearXNG is properly configured"""
        try:
            # Test with a simple academic search
            results = self.academic_search("machine learning", num_results=1)
            return len(results) > 0
        except Exception as e:
            print(f"SearXNG validation failed: {e}")
            return False
