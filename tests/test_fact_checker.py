#!/usr/bin/env python3
"""
Tests for the fact-checking component
"""
import pytest
import os
from dotenv import load_dotenv

from models.fact_checker import create_fact_checker, FactCheckResult
from models.ner_extractor import Citation
from search.firecrawl_client import create_search_client

load_dotenv()


class TestFactChecker:
    """Test suite for fact-checking functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.search_client = create_search_client(use_mock=True)
        self.fact_checker = create_fact_checker(self.search_client)

    def test_search_query_generation(self):
        """Test generation of search queries from citations"""
        test_citations = [
            Citation(
                text="Smith et al. (2023)",
                start=0,
                end=18,
                citation_type="author_year",
                confidence=0.9,
                authors=["Smith"],
                year="2023"
            ),
            Citation(
                text="DOI: 10.1038/nature12345",
                start=0,
                end=25,
                citation_type="doi",
                confidence=0.99,
                doi="10.1038/nature12345"
            ),
            Citation(
                text="arXiv:1706.03762",
                start=0,
                end=16,
                citation_type="preprint",
                confidence=0.99
            ),
        ]

        for citation in test_citations:
            queries = self.fact_checker._generate_search_queries(citation)

            print(f"\nCitation: {citation.text}")
            print(f"Generated queries: {queries}")

            assert len(queries) > 0, f"No queries generated for {citation.text}"
            assert len(queries) <= 5, f"Too many queries generated: {len(queries)}"

            # Check query quality
            for query in queries:
                assert len(query.strip()) > 0, "Empty query generated"
                assert len(query) < 200, f"Query too long: {len(query)} chars"

    def test_mock_search_integration(self):
        """Test fact-checking with mock search results"""
        citation = Citation(
            text="Vaswani et al. (2017)",
            start=0,
            end=21,
            citation_type="author_year",
            confidence=0.9,
            authors=["Vaswani"],
            year="2017"
        )

        result = self.fact_checker._fact_check_single_citation(citation)

        print(f"\nMock fact-check result:")
        print(f"  Citation: {citation.text}")
        print(f"  Status: {result.verification_status}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Sources: {len(result.sources_found)}")
        print(f"  Queries: {result.search_queries_used}")
        print(f"  Explanation: {result.explanation}")

        # Verify result structure
        assert isinstance(result, FactCheckResult)
        assert result.citation == citation
        assert result.verification_status in ['verified', 'not_found', 'contradicted', 'error']
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.sources_found, list)
        assert isinstance(result.explanation, str)
        assert isinstance(result.search_queries_used, list)

    def test_multiple_citations_fact_check(self):
        """Test fact-checking multiple citations at once"""
        citations = [
            Citation(
                text="Smith et al. (2023)",
                start=0,
                end=18,
                citation_type="author_year",
                confidence=0.9
            ),
            Citation(
                text="Jones and Brown (2022)",
                start=50,
                end=72,
                citation_type="author_year",
                confidence=0.85
            ),
            Citation(
                text="DOI: 10.1038/nature12345",
                start=100,
                end=125,
                citation_type="doi",
                confidence=0.99
            ),
        ]

        results = self.fact_checker.fact_check_citations(citations)

        print(f"\nMultiple citations fact-check:")
        print(f"Input citations: {len(citations)}")
        print(f"Results: {len(results)}")

        assert len(results) == len(citations), "Mismatch in results count"

        for i, result in enumerate(results):
            print(f"  {i+1}. {result.citation.text} -> {result.verification_status}")
            assert result.citation == citations[i], "Citation mismatch in results"

    def test_famous_papers_fact_check(self):
        """Test fact-checking of famous academic papers"""
        famous_papers = [
            {
                "citation": Citation(
                    text="Vaswani et al. (2017)",
                    start=0,
                    end=21,
                    citation_type="author_year",
                    confidence=0.9,
                    authors=["Vaswani"],
                    year="2017"
                ),
                "description": "Attention Is All You Need (Transformer paper)"
            },
            {
                "citation": Citation(
                    text="Devlin et al. (2018)",
                    start=0,
                    end=20,
                    citation_type="author_year",
                    confidence=0.9,
                    authors=["Devlin"],
                    year="2018"
                ),
                "description": "BERT paper"
            },
            {
                "citation": Citation(
                    text="arXiv:1706.03762",
                    start=0,
                    end=16,
                    citation_type="preprint",
                    confidence=0.99
                ),
                "description": "Transformer paper arXiv"
            },
        ]

        for paper in famous_papers:
            result = self.fact_checker._fact_check_single_citation(paper["citation"])

            print(f"\nFact-checking: {paper['description']}")
            print(f"  Citation: {paper['citation'].text}")
            print(f"  Result: {result.verification_status}")
            print(f"  Queries generated: {len(result.search_queries_used)}")

            # Should generate meaningful search queries
            assert len(result.search_queries_used) > 0, "No search queries generated"

            # Should complete without errors
            assert result.verification_status != 'error', f"Error in fact-checking: {result.explanation}"

    def test_error_handling_fact_check(self):
        """Test error handling in fact-checking"""
        problematic_citations = [
            Citation(
                text="",  # Empty citation
                start=0,
                end=0,
                citation_type="unknown",
                confidence=0.1
            ),
            Citation(
                text="Invalid citation format",
                start=0,
                end=24,
                citation_type="unknown",
                confidence=0.2
            ),
        ]

        for citation in problematic_citations:
            try:
                result = self.fact_checker._fact_check_single_citation(citation)

                print(f"\nError handling test:")
                print(f"  Citation: '{citation.text}'")
                print(f"  Status: {result.verification_status}")

                # Should handle gracefully
                assert isinstance(result, FactCheckResult)
                assert result.citation == citation

            except Exception as e:
                pytest.fail(f"Fact-checker crashed on problematic citation '{citation.text}': {e}")

    def test_search_query_quality(self):
        """Test the quality of generated search queries"""
        test_cases = [
            {
                "citation": Citation(
                    text="Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., ... & Polosukhin, I. (2017). Attention is all you need. Advances in neural information processing systems, 30.",
                    start=0,
                    end=150,
                    citation_type="journal",
                    confidence=0.95,
                    authors=["Vaswani", "Shazeer", "Parmar"],
                    year="2017",
                    title="Attention is all you need"
                ),
                "expected_terms": ["Vaswani", "2017", "attention", "transformer"]
            },
            {
                "citation": Citation(
                    text="DOI: 10.1038/nature14539",
                    start=0,
                    end=25,
                    citation_type="doi",
                    confidence=0.99,
                    doi="10.1038/nature14539"
                ),
                "expected_terms": ["doi", "10.1038/nature14539"]
            },
        ]

        for case in test_cases:
            queries = self.fact_checker._generate_search_queries(case["citation"])

            print(f"\nQuery quality test:")
            print(f"  Citation: {case['citation'].text[:50]}...")
            print(f"  Generated queries: {queries}")

            # Check that queries contain expected terms
            all_queries_text = " ".join(queries).lower()

            for term in case["expected_terms"]:
                assert term.lower() in all_queries_text, \
                    f"Expected term '{term}' not found in queries: {queries}"

    @pytest.mark.skipif(not os.getenv("OPENROUTER_API_KEY"), reason="No OpenRouter API key")
    def test_real_llm_fact_check(self):
        """Test fact-checking with real LLM (requires API key)"""
        if not os.getenv("OPENROUTER_API_KEY"):
            pytest.skip("No OpenRouter API key available")

        # Create fact-checker with real LLM but mock search
        real_fact_checker = create_fact_checker(self.search_client)

        citation = Citation(
            text="Smith et al. (2023)",
            start=0,
            end=18,
            citation_type="author_year",
            confidence=0.9
        )

        try:
            result = real_fact_checker._fact_check_single_citation(citation)

            print(f"\nReal LLM fact-check:")
            print(f"  Citation: {citation.text}")
            print(f"  Status: {result.verification_status}")
            print(f"  Explanation: {result.explanation[:100]}...")

            # Should complete successfully
            assert isinstance(result, FactCheckResult)
            assert len(result.explanation) > 10, "Explanation too short"

        except Exception as e:
            pytest.fail(f"Real LLM fact-check failed: {e}")

    def test_fact_checker_validation(self):
        """Test fact-checker validation"""
        assert self.fact_checker.validate_setup(), "Fact-checker validation failed"

        # Test with no search client
        no_search_fact_checker = create_fact_checker(None)
        # Should still validate (will use fallback behavior)
        assert no_search_fact_checker.validate_setup(), "Fact-checker without search should still validate"


if __name__ == "__main__":
    # Run tests manually
    test_class = TestFactChecker()
    test_class.setup_method()

    print("Running Fact-Checker Tests...")
    print("=" * 40)

    test_class.test_search_query_generation()
    print("✓ Search query generation tests passed")

    test_class.test_mock_search_integration()
    print("✓ Mock search integration tests passed")

    test_class.test_multiple_citations_fact_check()
    print("✓ Multiple citations fact-check tests passed")

    test_class.test_famous_papers_fact_check()
    print("✓ Famous papers fact-check tests passed")

    test_class.test_error_handling_fact_check()
    print("✓ Error handling tests passed")

    test_class.test_search_query_quality()
    print("✓ Search query quality tests passed")

    test_class.test_fact_checker_validation()
    print("✓ Fact-checker validation tests passed")

    # Test with real LLM if available
    if os.getenv("OPENROUTER_API_KEY"):
        test_class.test_real_llm_fact_check()
        print("✓ Real LLM fact-check tests passed")
    else:
        print("ℹ Skipped real LLM test (no API key)")

    print("\n🎉 All fact-checker tests passed!")