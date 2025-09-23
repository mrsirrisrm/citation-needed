import os
from dataclasses import dataclass
from typing import Any

import dspy

from .ner_extractor import Citation


@dataclass
class FactCheckResult:
    """Result of fact-checking a citation"""

    citation: Citation
    verification_status: str  # 'verified', 'not_found', 'contradicted', 'error'
    confidence: float  # Confidence in the verification (0.0 to 1.0)
    sources_found: list[dict[str, str]]  # List of found sources
    explanation: str  # Human-readable explanation
    search_queries_used: list[str]  # Queries that were used for search


class AnalyzeCitationSignature(dspy.Signature):
    """Analyze a citation to generate effective search queries"""

    citation_text = dspy.InputField(desc="The citation text to analyze")
    search_queries = dspy.OutputField(
        desc="3-5 specific search queries to verify this citation, one per line"
    )


class VerifySourceSignature(dspy.Signature):
    """Verify if search results support or contradict a citation"""

    citation_text = dspy.InputField(desc="Original citation to verify")
    search_results = dspy.InputField(desc="Search results content")
    verification_status = dspy.OutputField(
        desc="Status: 'verified', 'not_found', 'contradicted', or 'partial'"
    )
    confidence = dspy.OutputField(desc="Confidence score 0.0-1.0")
    explanation = dspy.OutputField(desc="Brief explanation of verification result")


class FactChecker:
    """Model B: Fact-checking model using GPT-3.5"""

    def __init__(self, search_client=None):
        """
        Initialize the fact checker

        Args:
            search_client: Firecrawl client for web search
        """
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.fact_check_model_name = os.getenv("FACT_CHECK_MODEL", "openai/gpt-3.5-turbo")
        self.search_client = search_client

        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        # Configure DSPy with OpenRouter for fact-checking model
        self.lm = dspy.LM(
            model=self.fact_check_model_name,
            api_key=self.openrouter_api_key,
            api_base="https://openrouter.ai/api/v1",
            max_tokens=1024,
            temperature=0.1,  # Lower temperature for more consistent fact-checking
        )

        # Initialize DSPy chains
        with dspy.context(lm=self.lm):
            self.citation_analyzer = dspy.ChainOfThought(AnalyzeCitationSignature)
            self.source_verifier = dspy.ChainOfThought(VerifySourceSignature)

    def fact_check_citations(self, citations: list[Citation]) -> list[FactCheckResult]:
        """
        Fact-check a list of citations

        Args:
            citations: List of Citation objects to verify

        Returns:
            List of FactCheckResult objects
        """
        results = []

        for citation in citations:
            try:
                result = self._fact_check_single_citation(citation)
                results.append(result)
            except Exception as e:
                # Create error result
                error_result = FactCheckResult(
                    citation=citation,
                    verification_status="error",
                    confidence=0.0,
                    sources_found=[],
                    explanation=f"Error during fact-checking: {str(e)}",
                    search_queries_used=[],
                )
                results.append(error_result)

        return results

    def _fact_check_single_citation(self, citation: Citation) -> FactCheckResult:
        """Fact-check a single citation"""

        # Step 1: Generate search queries
        search_queries = self._generate_search_queries(citation)

        # Step 2: Search for sources (if search client available)
        sources_found = []
        if self.search_client and search_queries:
            sources_found = self._search_for_sources(search_queries)

        # Step 3: Verify against found sources
        verification_result = self._verify_citation(citation, sources_found)

        return FactCheckResult(
            citation=citation,
            verification_status=verification_result["status"],
            confidence=verification_result["confidence"],
            sources_found=sources_found,
            explanation=verification_result["explanation"],
            search_queries_used=search_queries,
        )

    def _generate_search_queries(self, citation: Citation) -> list[str]:
        """Generate search queries for a citation"""
        try:
            with dspy.context(lm=self.lm):
                result = self.citation_analyzer(citation_text=citation.text)

            # Parse queries from response
            queries = [q.strip() for q in result.search_queries.split("\n") if q.strip()]
            return queries[:5]  # Limit to 5 queries

        except Exception:
            # Fallback: generate basic queries from citation components
            queries = []

            if citation.authors and citation.year:
                author_query = f"{citation.authors[0]} {citation.year}"
                queries.append(author_query)

            if citation.title:
                queries.append(f'"{citation.title}"')

            if citation.doi:
                queries.append(f"doi:{citation.doi}")

            # Generic query
            if not queries:
                queries.append(citation.text[:100])  # First 100 chars

            return queries

    def _search_for_sources(self, queries: list[str]) -> list[dict[str, str]]:
        """Search for sources using the search client"""
        if not self.search_client:
            return []

        sources = []
        for query in queries[:3]:  # Limit to 3 queries to avoid rate limits
            try:
                search_results = self.search_client.search(query)
                if search_results:
                    sources.extend(search_results[:2])  # Top 2 results per query
            except Exception as e:
                print(f"Search error for query '{query}': {e}")
                continue

        # Remove duplicates based on URL
        unique_sources = []
        seen_urls = set()
        for source in sources:
            url = source.get("url", "")
            if url and url not in seen_urls:
                unique_sources.append(source)
                seen_urls.add(url)

        return unique_sources[:5]  # Return top 5 unique sources

    def _verify_citation(self, citation: Citation, sources: list[dict[str, str]]) -> dict[str, Any]:
        """Verify citation against found sources"""

        if not sources:
            return {
                "status": "not_found",
                "confidence": 0.8,
                "explanation": "No sources found to verify this citation.",
            }

        # Combine search results into context
        search_context = ""
        for i, source in enumerate(sources[:3]):  # Use top 3 sources
            title = source.get("title", "Untitled")
            content = source.get("content", source.get("text", ""))[:500]  # First 500 chars
            url = source.get("url", "")

            search_context += f"Source {i + 1}: {title}\nURL: {url}\nContent: {content}\n\n"

        if not search_context.strip():
            return {
                "status": "not_found",
                "confidence": 0.7,
                "explanation": "Sources found but no content available for verification.",
            }

        # Use LLM to verify
        try:
            with dspy.context(lm=self.lm):
                result = self.source_verifier(
                    citation_text=citation.text, search_results=search_context
                )

            # Parse confidence score
            try:
                confidence = float(result.confidence)
                confidence = max(0.0, min(1.0, confidence))  # Clamp to [0,1]
            except (ValueError, AttributeError):
                confidence = 0.5

            return {
                "status": result.verification_status.lower(),
                "confidence": confidence,
                "explanation": result.explanation,
            }

        except Exception as e:
            return {
                "status": "error",
                "confidence": 0.0,
                "explanation": f"Error during verification: {str(e)}",
            }

    def validate_setup(self) -> bool:
        """Validate that the fact checker is properly configured"""
        try:
            # Test citation analysis
            test_citation = Citation(
                text="Smith et al. (2023) Nature",
                start=0,
                end=25,
                citation_type="journal",
                confidence=0.9,
            )

            queries = self._generate_search_queries(test_citation)
            return len(queries) > 0

        except Exception:
            return False


# Factory function for easy import
def create_fact_checker(search_client=None) -> FactChecker:
    """Create and return a configured FactChecker instance"""
    return FactChecker(search_client=search_client)
