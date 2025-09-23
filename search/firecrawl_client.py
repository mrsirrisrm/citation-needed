import os
import re
import json
import requests
from typing import Any, Optional, Dict
from urllib.parse import urlparse, urljoin

from firecrawl import FirecrawlApp


class FirecrawlSearchClient:
    """Client for searching and scraping web content using Firecrawl"""

    def __init__(self):
        """Initialize Firecrawl client"""
        self.api_key = os.getenv("FIRECRAWL_API_KEY")

        if not self.api_key:
            raise ValueError("FIRECRAWL_API_KEY environment variable not set")

        try:
            self.app = FirecrawlApp(api_key=self.api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize Firecrawl client: {e}") from e

    def search(self, query: str, num_results: int = 5) -> list[dict[str, str]]:
        """
        Search for web content using Firecrawl

        Args:
            query: Search query string
            num_results: Maximum number of results to return

        Returns:
            List of search results with title, url, and content
        """
        try:
            # Use Firecrawl's search functionality
            # Add academic site filters to the query for better results
            academic_query = f"{query} site:scholar.google.com OR site:arxiv.org OR site:pubmed.ncbi.nlm.nih.gov OR site:doi.org"
            search_results = self.app.search(
                query=academic_query,
                limit=num_results,
            )

            processed_results = []
            # Handle SearchResponse object
            if hasattr(search_results, 'data'):
                results_list = search_results.data
            elif hasattr(search_results, 'results'):
                results_list = search_results.results
            else:
                # Fallback to dict access
                results_list = getattr(search_results, 'data', [])

            for result in results_list[:num_results]:
                processed_result = {
                    "title": result.get("title", "Untitled"),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "description": result.get("description", ""),
                    "source": "firecrawl_search",
                }
                processed_results.append(processed_result)

            return processed_results

        except Exception as e:
            print(f"Search error: {e}")
            return []

    def scrape_url(self, url: str) -> dict[str, str]:
        """
        Scrape content from a specific URL

        Args:
            url: URL to scrape

        Returns:
            Dictionary with scraped content
        """
        try:
            result = self.app.scrape_url(
                url=url,
                params={
                    "formats": ["markdown", "html"],
                    "includeTags": ["title", "meta", "h1", "h2", "h3", "p", "article"],
                    "excludeTags": ["nav", "footer", "aside", "script", "style"],
                    "waitFor": 1000,  # Wait 1 second for page to load
                },
            )

            return {
                "title": result.get("metadata", {}).get("title", "Untitled"),
                "url": url,
                "content": result.get("content", ""),
                "markdown": result.get("markdown", ""),
                "metadata": result.get("metadata", {}),
                "source": "firecrawl_scrape",
            }

        except Exception as e:
            print(f"Scraping error for {url}: {e}")
            return {
                "title": "Error",
                "url": url,
                "content": f"Failed to scrape: {str(e)}",
                "source": "firecrawl_scrape",
            }

    def enhanced_citation_search(
        self, citation_text: str, citation_components: dict[str, Any]
    ) -> list[dict[str, str]]:
        """
        Enhanced search specifically for academic citations

        Args:
            citation_text: Full citation text
            citation_components: Parsed citation components (authors, title, year, etc.)

        Returns:
            List of relevant search results
        """
        all_results = []

        # Try direct URL validation first for known academic sources
        direct_results = self._try_direct_url_validation(citation_components)
        if direct_results:
            all_results.extend(direct_results)
            print(f"✅ Found {len(direct_results)} direct URL validation results")

        # Generate multiple search strategies
        search_queries = []

        # Strategy 1: Full citation text
        if citation_text:
            search_queries.append(f'"{citation_text[:100]}"')

        # Strategy 2: Author + Year + Title
        if citation_components.get("authors") and citation_components.get("year"):
            author = citation_components["authors"][0] if citation_components["authors"] else ""
            year = citation_components["year"]
            if citation_components.get("title"):
                title_snippet = citation_components["title"][:50]
                search_queries.append(f'{author} {year} "{title_snippet}"')
            else:
                search_queries.append(f"{author} {year}")

        # Strategy 3: DOI search
        if citation_components.get("doi"):
            search_queries.append(f"doi:{citation_components['doi']}")

        # Strategy 4: Title only (if available)
        if citation_components.get("title"):
            search_queries.append(f'"{citation_components["title"]}"')

        # Strategy 5: Journal + Year (if available)
        if citation_components.get("journal") and citation_components.get("year"):
            search_queries.append(f"{citation_components['journal']} {citation_components['year']}")

        # Execute searches
        for query in search_queries[:3]:  # Limit to 3 queries
            try:
                print(f"🔍 Searching for: {query}")
                results = self.search(query, num_results=3)
                all_results.extend(results)
            except Exception as e:
                print(f"Error searching for '{query}': {e}")
                continue

        # Remove duplicates and return top results
        unique_results = []
        seen_urls = set()

        for result in all_results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                unique_results.append(result)
                seen_urls.add(url)

        return unique_results[:5]  # Return top 5 unique results

    def _try_direct_url_validation(self, citation_components: dict[str, Any]) -> list[dict[str, str]]:
        """
        Try direct URL validation for known academic sources

        Args:
            citation_components: Parsed citation components

        Returns:
            List of validation results
        """
        results = []

        # Try DOI validation
        if citation_components.get("doi"):
            doi_result = self._validate_doi(citation_components["doi"])
            if doi_result:
                results.append(doi_result)

        # Try arXiv validation
        if citation_components.get("arxiv_id"):
            arxiv_result = self._validate_arxiv(citation_components["arxiv_id"])
            if arxiv_result:
                results.append(arxiv_result)

        # Try PubMed validation
        if citation_components.get("pmid"):
            pubmed_result = self._validate_pubmed(citation_components["pmid"])
            if pubmed_result:
                results.append(pubmed_result)

        return results

    def _validate_doi(self, doi: str) -> Optional[dict[str, str]]:
        """Validate a DOI by resolving it and checking content"""
        try:
            # Clean DOI
            doi_clean = doi.lower().replace("doi:", "").strip()
            if not doi_clean.startswith("10."):
                return None

            # Try to resolve DOI via doi.org
            doi_url = f"https://doi.org/{doi_clean}"
            print(f"🔗 Validating DOI: {doi_clean}")

            # Try to get basic info from DOI resolver
            headers = {
                'User-Agent': 'Citation-Needed/1.0 (https://github.com/martin/citation-needed)',
                'Accept': 'application/json',
            }

            # First try Content Negotiation
            try:
                response = requests.get(
                    f"https://doi.org/{doi_clean}",
                    headers={**headers, 'Accept': 'application/vnd.citationstyles.csl+json'},
                    timeout=10
                )
                if response.status_code == 200:
                    doi_data = response.json()
                    return {
                        "title": doi_data.get("title", "DOI Validated"),
                        "url": doi_url,
                        "content": f"DOI resolved to: {doi_data.get('title', 'Unknown publication')}",
                        "metadata": {
                            "type": "doi",
                            "resolved": True,
                            "title": doi_data.get("title"),
                            "authors": [author.get("family") + ", " + author.get("given") for author in doi_data.get("author", [])[:3]],
                            "journal": doi_data.get("container-title"),
                            "year": doi_data.get("published", {}).get("date-parts", [[""]])[0][0],
                        },
                        "source": "doi_direct",
                        "confidence": 0.95,
                    }
            except requests.RequestException:
                pass

            # Fallback: Try to scrape the DOI URL
            try:
                scrape_result = self.scrape_url(doi_url)
                if scrape_result and scrape_result.get("content"):
                    return {
                        "title": scrape_result.get("title", "DOI Validated"),
                        "url": doi_url,
                        "content": scrape_result.get("content", "")[:500],
                        "metadata": {"type": "doi", "resolved": True},
                        "source": "doi_scrape",
                        "confidence": 0.9,
                    }
            except Exception as e:
                print(f"DOI scraping failed: {e}")

        except Exception as e:
            print(f"DOI validation error: {e}")

        return None

    def _validate_arxiv(self, arxiv_id: str) -> Optional[dict[str, str]]:
        """Validate an arXiv ID using the arXiv API"""
        try:
            # Clean arXiv ID
            arxiv_clean = arxiv_id.lower().replace("arxiv:", "").strip()
            if not re.match(r'^\d+\.\d+', arxiv_clean):
                return None

            print(f"📄 Validating arXiv: {arxiv_clean}")

            # Use arXiv API
            api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_clean}"
            response = requests.get(api_url, timeout=10)

            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)

                # Find entry in XML response
                namespace = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
                entry = root.find('atom:entry', namespace)

                if entry is not None:
                    title = entry.find('atom:title', namespace).text.strip()
                    authors = []
                    for author in entry.findall('atom:author', namespace):
                        name = author.find('atom:name', namespace).text
                        authors.append(name)

                    summary = entry.find('atom:summary', namespace).text.strip()
                    published = entry.find('atom:published', namespace).text
                    year = published.split('-')[0] if published else ""

                    return {
                        "title": title,
                        "url": f"https://arxiv.org/abs/{arxiv_clean}",
                        "content": f"arXiv paper: {title}\n\n{summary[:300]}...",
                        "metadata": {
                            "type": "arxiv",
                            "resolved": True,
                            "title": title,
                            "authors": authors[:3],
                            "year": year,
                            "summary": summary,
                        },
                        "source": "arxiv_api",
                        "confidence": 0.98,
                    }

        except Exception as e:
            print(f"arXiv validation error: {e}")

        return None

    def _validate_pubmed(self, pmid: str) -> Optional[dict[str, str]]:
        """Validate a PubMed ID"""
        try:
            # Clean PMID
            pmid_clean = pmid.lower().replace("pmid:", "").strip()
            if not pmid_clean.isdigit():
                return None

            print(f"🧬 Validating PubMed: {pmid_clean}")

            # Use NCBI E-utilities API
            api_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid_clean}&retmode=json"
            response = requests.get(api_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                result = data.get("result", {})
                pmid_data = result.get(pmid_clean)

                if pmid_data:
                    title = pmid_data.get("title", "")
                    authors = pmid_data.get("authors", [])
                    journal = pmid_data.get("fulljournalname", "")
                    year = pmid_data.get("pubdate", "").split()[0] if pmid_data.get("pubdate") else ""

                    return {
                        "title": title,
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid_clean}/",
                        "content": f"PubMed article: {title}\nJournal: {journal}\nYear: {year}",
                        "metadata": {
                            "type": "pubmed",
                            "resolved": True,
                            "title": title,
                            "authors": authors[:3],
                            "journal": journal,
                            "year": year,
                        },
                        "source": "pubmed_api",
                        "confidence": 0.96,
                    }

        except Exception as e:
            print(f"PubMed validation error: {e}")

        return None

    def smart_citation_search(
        self, structured_citation, citation_text: str = ""
    ) -> list[dict[str, str]]:
        """
        Smart citation search using both direct validation and web search

        Args:
            structured_citation: StructuredCitation object
            citation_text: Original citation text

        Returns:
            List of search results with confidence scores
        """
        all_results = []

        # Convert structured citation to dict for compatibility
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

        # Try direct validation first
        direct_results = self._try_direct_url_validation(citation_dict)
        if direct_results:
            all_results.extend(direct_results)
            print(f"✅ Direct validation found {len(direct_results)} results")

        # If direct validation didn't find high-confidence results, try web search
        if not any(r.get("confidence", 0) > 0.9 for r in direct_results):
            print("🔍 High-confidence direct validation not found, trying web search")

            # Generate search queries from structured citation
            search_queries = []

            if structured_citation.doi:
                search_queries.append(structured_citation.doi)
            if structured_citation.arxiv_id:
                search_queries.append(structured_citation.arxiv_id)

            # Author + year + title
            if structured_citation.first_author and structured_citation.year and structured_citation.title:
                title_snippet = " ".join(structured_citation.title.split()[:6])
                search_queries.append(f'{structured_citation.first_author} {structured_citation.year} "{title_snippet}"')

            # Title search
            if structured_citation.title:
                search_queries.append(f'"{structured_citation.title}"')

            # Author + year
            if structured_citation.first_author and structured_citation.year:
                search_queries.append(f'{structured_citation.first_author} {structured_citation.year}')

            # Execute searches
            for query in search_queries[:3]:
                try:
                    print(f"🔍 Web search query: {query}")
                    results = self.search(query, num_results=3)
                    all_results.extend(results)
                except Exception as e:
                    print(f"Web search error for '{query}': {e}")

        # Remove duplicates based on URL
        unique_results = []
        seen_urls = set()

        for result in all_results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                unique_results.append(result)
                seen_urls.add(url)

        # Log results for debugging
        print(f"📊 Total results found: {len(unique_results)}")
        for i, result in enumerate(unique_results[:3]):
            confidence = result.get("confidence", "N/A")
            source = result.get("source", "unknown")
            title = result.get("title", "No title")[:60]
            print(f"  {i+1}. [{source}] {title} (conf: {confidence})")

        return unique_results[:5]

    def validate_setup(self) -> bool:
        """Validate that Firecrawl is properly configured"""
        try:
            # Test with a simple search
            self.search("test academic paper", num_results=1)
            return True  # If no exception, we're good
        except Exception as e:
            print(f"Firecrawl validation failed: {e}")
            return False


class MockSearchClient:
    """Mock search client for testing when Firecrawl is not available"""

    def search(self, query: str, num_results: int = 5) -> list[dict[str, str]]:
        """Mock search that returns dummy results"""
        return [
            {
                "title": f"Mock Result for: {query}",
                "url": "https://example.com/mock-result",
                "content": f"This is a mock search result for the query: {query}",
                "source": "mock",
            }
        ]

    def scrape_url(self, url: str) -> dict[str, str]:
        """Mock scraping that returns dummy content"""
        return {
            "title": "Mock Scraped Content",
            "url": url,
            "content": f"Mock content scraped from {url}",
            "source": "mock",
        }

    def enhanced_citation_search(
        self, citation_text: str, citation_components: dict[str, Any]
    ) -> list[dict[str, str]]:
        """Mock enhanced search"""
        return self.search(citation_text, num_results=3)

    def _try_direct_url_validation(self, citation_components: dict[str, Any]) -> list[dict[str, str]]:
        """Mock direct URL validation for testing"""
        results = []

        # Mock DOI validation
        if citation_components.get("doi"):
            results.append({
                "title": f"Mock DOI Validation: {citation_components['doi']}",
                "url": f"https://doi.org/{citation_components['doi'].replace('doi:', '')}",
                "content": "Mock DOI validation result",
                "metadata": {"type": "doi", "resolved": True},
                "source": "doi_mock",
                "confidence": 0.95,
            })

        # Mock arXiv validation
        if citation_components.get("arxiv_id"):
            results.append({
                "title": f"Mock arXiv Validation: {citation_components['arxiv_id']}",
                "url": f"https://arxiv.org/abs/{citation_components['arxiv_id'].replace('arxiv:', '')}",
                "content": "Mock arXiv validation result",
                "metadata": {"type": "arxiv", "resolved": True},
                "source": "arxiv_mock",
                "confidence": 0.98,
            })

        # Mock PubMed validation
        if citation_components.get("pmid"):
            results.append({
                "title": f"Mock PubMed Validation: {citation_components['pmid']}",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{citation_components['pmid']}",
                "content": "Mock PubMed validation result",
                "metadata": {"type": "pubmed", "resolved": True},
                "source": "pubmed_mock",
                "confidence": 0.96,
            })

        return results

    def smart_citation_search(self, structured_citation, citation_text: str = "") -> list[dict[str, str]]:
        """Mock smart citation search"""
        return self._try_direct_url_validation({
            "doi": structured_citation.doi,
            "arxiv_id": structured_citation.arxiv_id,
            "pmid": structured_citation.pmid,
        })

    def validate_setup(self) -> bool:
        """Mock validation always returns True"""
        return True


# Factory function for easy import
def create_search_client(use_mock: bool = False) -> FirecrawlSearchClient:
    """
    Create and return a search client

    Args:
        use_mock: If True, return mock client for testing

    Returns:
        Search client instance
    """
    if use_mock:
        return MockSearchClient()

    try:
        return FirecrawlSearchClient()
    except ValueError as e:
        print(f"Warning: {e}")
        print("Falling back to mock search client")
        return MockSearchClient()
