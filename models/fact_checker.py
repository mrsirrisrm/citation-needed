import os
from dataclasses import dataclass
from typing import Any

import dspy

from .citation_parser import StructuredCitation, create_citation_parser
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

        # Initialize structured citation parser
        try:
            self.citation_parser = create_citation_parser()
            print("✅ Structured citation parser initialized")
        except Exception as e:
            print(f"⚠️  Citation parser initialization failed: {e}")
            self.citation_parser = None

    def fact_check_citations(
        self, citations: list[Citation], progress_callback=None
    ) -> list[FactCheckResult]:
        """
        Fact-check a list of citations

        Args:
            citations: List of Citation objects to verify
            progress_callback: Optional callback function for progress updates

        Returns:
            List of FactCheckResult objects
        """
        results = []
        total_citations = len(citations)

        for i, citation in enumerate(citations):
            try:
                result = self._fact_check_single_citation(citation)
                results.append(result)

                # Update progress if callback provided
                if progress_callback:
                    progress = (i + 1) / total_citations
                    progress_callback(progress, result)

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

                # Update progress even for errors
                if progress_callback:
                    progress = (i + 1) / total_citations
                    progress_callback(progress, error_result)

        return results

    def _fact_check_single_citation(self, citation: Citation) -> FactCheckResult:
        """Fact-check a single citation"""

        print(f"🔍 Fact-checking citation: {citation.text[:80]}...")

        # Step 1: Parse citation into structured format (if parser available)
        structured_citation = None
        if self.citation_parser:
            try:
                structured_citation = self.citation_parser.parse_citation(citation.text)
                print(
                    f"📋 Parsed citation: {structured_citation.first_author} ({structured_citation.year}) - {structured_citation.title[:50]}..."
                )
                print(
                    f"📊 Extraction method: {structured_citation.extraction_method}, confidence: {structured_citation.confidence:.2f}"
                )
            except Exception as e:
                print(f"⚠️  Structured parsing failed: {e}")

        # Step 2: Search for sources using enhanced strategy
        sources_found = []
        if self.search_client:
            if structured_citation:
                # Use smart search with structured citation
                if hasattr(self.search_client, "smart_citation_search"):
                    sources_found = self.search_client.smart_citation_search(
                        structured_citation, citation.text
                    )
                else:
                    # Fallback to enhanced search
                    citation_dict = {
                        "authors": structured_citation.authors,
                        "first_author": structured_citation.first_author,
                        "title": structured_citation.title,
                        "year": structured_citation.year,
                        "journal": structured_citation.journal,
                        "doi": structured_citation.doi,
                        "arxiv_id": structured_citation.arxiv_id,
                        "pmid": structured_citation.pmid,
                    }
                    sources_found = self.search_client.enhanced_citation_search(
                        citation.text, citation_dict
                    )
            else:
                # Fallback to old method
                search_queries = self._generate_search_queries(citation)
                if search_queries:
                    sources_found = self._search_for_sources(search_queries)

        # Step 3: Verify against found sources
        verification_result = self._verify_citation_enhanced(
            citation, sources_found, structured_citation
        )

        # Generate search queries for logging
        if structured_citation:
            search_queries = self.citation_parser.generate_search_queries(structured_citation)
        else:
            search_queries = self._generate_search_queries(citation)

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

    def _verify_citation_enhanced(
        self,
        citation: Citation,
        sources: list[dict[str, str]],
        structured_citation: StructuredCitation = None,
    ) -> dict[str, Any]:
        """Verify citation against found sources with enhanced matching"""

        if not sources:
            return {
                "status": "not_found",
                "confidence": 0.8,
                "explanation": "No sources found to verify this citation.",
            }

        print(f"🔍 Verifying against {len(sources)} sources...")

        # Check for high-confidence direct validations
        direct_validations = [s for s in sources if s.get("confidence", 0) > 0.9]
        if direct_validations:
            best_validation = max(direct_validations, key=lambda x: x.get("confidence", 0))
            source_type = best_validation.get("metadata", {}).get("type", "unknown")
            return {
                "status": "verified",
                "confidence": best_validation.get("confidence", 0.95),
                "explanation": f"Direct validation via {source_type}: {best_validation.get('title', 'Source found')}",
            }

        # Enhanced verification with structured citation data
        if structured_citation:
            verification_result = self._verify_with_structured_data(structured_citation, sources)
            if verification_result["confidence"] > 0.7:
                return verification_result

        # Fallback to LLM verification
        return self._verify_citation(citation, sources)

    def _verify_with_structured_data(
        self, structured_citation: StructuredCitation, sources: list[dict[str, str]]
    ) -> dict[str, Any]:
        """Verify citation using structured data and enhanced matching"""

        best_match = None
        best_score = 0.0

        for source in sources:
            score = self._calculate_match_score(structured_citation, source)
            if score > best_score:
                best_score = score
                best_match = source

        if best_score > 0.7:  # Good match threshold
            return {
                "status": "verified",
                "confidence": min(0.9, best_score + 0.1),  # Boost confidence slightly
                "explanation": f"Matched source: {best_match.get('title', 'Unknown')} (score: {best_score:.2f})",
            }
        elif best_score > 0.4:  # Partial match
            return {
                "status": "partial",
                "confidence": best_score,
                "explanation": f"Partial match with: {best_match.get('title', 'Unknown')} (score: {best_score:.2f})",
            }
        else:
            return {
                "status": "not_found",
                "confidence": 0.6,
                "explanation": "No strong matches found in search results",
            }

    def _calculate_match_score(
        self, structured_citation: StructuredCitation, source: dict[str, str]
    ) -> float:
        """Calculate match score between structured citation and source"""

        score = 0.0
        max_score = 0.0

        # Title matching (highest weight)
        if structured_citation.title:
            max_score += 0.4
            source_title = source.get("title", "").lower()
            citation_title = structured_citation.title.lower()

            # Exact title match
            if citation_title == source_title:
                score += 0.4
            # Partial title match
            elif citation_title in source_title or source_title in citation_title:
                score += 0.25
            # Word overlap
            else:
                title_words = set(citation_title.split())
                source_words = set(source_title.split())
                overlap = len(title_words.intersection(source_words))
                if overlap > 0:
                    score += min(0.3, overlap / len(title_words) * 0.4)

        # Author matching
        if structured_citation.first_author:
            max_score += 0.3
            source_content = source.get("content", "").lower()
            author_name = structured_citation.first_author.lower()

            if author_name in source_content:
                score += 0.3

        # Year matching
        if structured_citation.year:
            max_score += 0.2
            if structured_citation.year in source.get("content", ""):
                score += 0.2

        # Journal/conference matching
        if structured_citation.journal:
            max_score += 0.1
            journal_lower = structured_citation.journal.lower()
            if journal_lower in source.get("content", "").lower():
                score += 0.1

        # Boost score based on source confidence
        source_confidence = source.get("confidence", 0.5)
        score *= 0.5 + source_confidence * 0.5  # Scale by source reliability

        return score / max_score if max_score > 0 else 0.0

    def _verify_citation(self, citation: Citation, sources: list[dict[str, str]]) -> dict[str, Any]:
        """Verify citation against found sources (original method)"""

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
