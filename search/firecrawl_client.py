import os
from typing import Any

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
