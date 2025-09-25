#!/usr/bin/env python3
"""
Integration tests for the Citation Needed system
"""

import os

import pytest
from dotenv import load_dotenv

from models.chat_model import create_chat_model
from models.fact_checker import create_fact_checker
from models.ner_extractor import create_ner_extractor
from search.firecrawl_client import create_search_client


load_dotenv()


class TestIntegration:
    """Integration tests for the complete system"""

    def setup_method(self):
        """Set up test components"""
        self.ner = create_ner_extractor()
        self.search_client = create_search_client(use_mock=True)  # Use mock for testing
        self.fact_checker = create_fact_checker(self.search_client)

        # Only test chat model if API key is available
        self.has_api_key = bool(os.getenv("OPENROUTER_API_KEY"))
        if self.has_api_key:
            self.chat_model = create_chat_model()

    def test_end_to_end_pipeline_mock(self):
        """Test the complete pipeline with mock data"""
        # Simulate a chat response with citations
        mock_response = """
        The attention mechanism was revolutionary. According to Vaswani et al. (2017),
        the transformer architecture eliminated the need for recurrence. This work built
        upon earlier attention mechanisms described in Bahdanau et al. (2014).
        The paper can be found at arXiv:1706.03762.
        """

        print(f"\nTesting pipeline with text: {mock_response[:100]}...")

        # Step 1: Extract citations
        citations = self.ner.extract_citations(mock_response)
        print(f"Found {len(citations)} citations:")
        for i, citation in enumerate(citations):
            print(
                f"  {i + 1}. '{citation.text}' (type: {citation.citation_type}, conf: {citation.confidence:.2f})"
            )

        assert len(citations) > 0, "No citations detected"

        # Step 2: Fact-check citations
        fact_check_results = self.fact_checker.fact_check_citations(citations)
        print("\nFact-check results:")
        for i, result in enumerate(fact_check_results):
            print(f"  {i + 1}. Status: {result.verification_status}")
            print(f"      Confidence: {result.confidence:.2f}")
            print(f"      Sources: {len(result.sources_found)}")
            print(f"      Explanation: {result.explanation[:100]}...")

        assert len(fact_check_results) == len(citations), "Mismatch in fact-check results"

        # Step 3: Verify each result has required fields
        for result in fact_check_results:
            assert result.verification_status in ["verified", "not_found", "contradicted", "error"]
            assert 0.0 <= result.confidence <= 1.0
            assert isinstance(result.sources_found, list)
            assert isinstance(result.explanation, str)
            assert isinstance(result.search_queries_used, list)

    @pytest.mark.skipif(not os.getenv("OPENROUTER_API_KEY"), reason="No OpenRouter API key")
    def test_real_chat_integration(self):
        """Test integration with real chat model (requires API key)"""
        if not self.has_api_key:
            pytest.skip("No OpenRouter API key available")

        # Test a simple query about transformers
        query = "Tell me about the attention mechanism in transformers and cite the original paper"

        try:
            response = self.chat_model.chat(query)
            print(f"\nChat response: {response[:200]}...")

            # Extract citations from response
            citations = self.ner.extract_citations(response)
            print(f"Citations found in response: {len(citations)}")

            # The response should ideally contain citations
            # Note: This may not always happen depending on the model's response
            if citations:
                print("✓ Citations detected in chat response")
                for citation in citations:
                    print(f"  - {citation.text}")
            else:
                print("ℹ No citations in this response (model-dependent)")

        except Exception as e:
            pytest.fail(f"Chat integration failed: {e}")

    def test_famous_paper_detection_integration(self):
        """Test detection and fact-checking of famous papers"""
        test_papers = [
            {
                "text": "The groundbreaking Attention Is All You Need paper by Vaswani et al. (2017) introduced transformers.",
                "expected_paper": "transformers",
                "expected_authors": "Vaswani",
            },
            {
                "text": "BERT (Devlin et al., 2018) revolutionized natural language understanding.",
                "expected_paper": "BERT",
                "expected_authors": "Devlin",
            },
            {
                "text": "The original GPT paper (Radford et al., 2018) demonstrated unsupervised learning potential.",
                "expected_paper": "GPT",
                "expected_authors": "Radford",
            },
        ]

        for paper_info in test_papers:
            print(f"\nTesting: {paper_info['expected_paper']}")

            # Extract citations
            citations = self.ner.extract_citations(paper_info["text"])
            assert len(citations) > 0, f"No citations found for {paper_info['expected_paper']}"

            # Verify citation contains expected elements
            found_citation = citations[0]
            citation_lower = found_citation.text.lower()

            # Check for expected authors
            assert paper_info["expected_authors"].lower() in citation_lower, (
                f"Expected author {paper_info['expected_authors']} not found in {found_citation.text}"
            )

            # Fact-check the citation
            fact_results = self.fact_checker.fact_check_citations([found_citation])
            assert len(fact_results) == 1, "Fact-check should return one result"

            result = fact_results[0]
            print(f"  Citation: {found_citation.text}")
            print(f"  Status: {result.verification_status}")
            print(f"  Queries generated: {len(result.search_queries_used)}")

            # Should generate reasonable search queries
            assert len(result.search_queries_used) > 0, "No search queries generated"

    def test_error_handling(self):
        """Test system behavior with edge cases and errors"""
        edge_cases = [
            "",  # Empty text
            "No citations here, just regular text.",  # No citations
            "Invalid citation format (author year) without proper structure.",  # Malformed
            "Mixed content with Smith et al. (2023) and regular text.",  # Mixed
        ]

        for case in edge_cases:
            print(f"\nTesting edge case: '{case[:50]}...'")

            try:
                # Should not crash on any input
                citations = self.ner.extract_citations(case)
                print(f"  Citations found: {len(citations)}")

                if citations:
                    fact_results = self.fact_checker.fact_check_citations(citations)
                    print(f"  Fact-check results: {len(fact_results)}")

                    # Should always return results for input citations
                    assert len(fact_results) == len(citations)

            except Exception as e:
                pytest.fail(f"System crashed on edge case '{case}': {e}")

    def test_performance_basic(self):
        """Basic performance test with multiple citations"""
        import time

        # Text with multiple citations
        multi_citation_text = """
        The field of deep learning has seen remarkable progress. The foundational work
        by LeCun et al. (1998) on convolutional networks laid the groundwork. Later,
        the attention mechanism (Bahdanau et al., 2014) and transformers (Vaswani et al., 2017)
        revolutionized sequence modeling. BERT (Devlin et al., 2018), GPT (Radford et al., 2018),
        and subsequent models have pushed the boundaries further. For implementation details,
        see DOI: 10.1038/nature14539 and arXiv:1706.03762.
        """

        print(f"\nPerformance test with {len(multi_citation_text)} character text...")

        # Time NER extraction
        start_time = time.time()
        citations = self.ner.extract_citations(multi_citation_text)
        ner_time = time.time() - start_time

        print(f"NER extraction: {ner_time:.3f}s for {len(citations)} citations")

        # Time fact-checking (with mock client)
        start_time = time.time()
        self.fact_checker.fact_check_citations(citations)
        fact_check_time = time.time() - start_time

        print(f"Fact-checking: {fact_check_time:.3f}s for {len(citations)} citations")

        # Basic performance expectations
        assert ner_time < 5.0, f"NER too slow: {ner_time:.3f}s"
        assert fact_check_time < 30.0, f"Fact-checking too slow: {fact_check_time:.3f}s"
        assert len(citations) >= 4, f"Expected multiple citations, got {len(citations)}"

    def test_component_validation(self):
        """Test that all components validate correctly"""
        print("\nValidating all components...")

        assert self.ner.validate_setup(), "NER validation failed"
        print("✓ NER component valid")

        assert self.search_client.validate_setup(), "Search client validation failed"
        print("✓ Search client valid")

        assert self.fact_checker.validate_setup(), "Fact checker validation failed"
        print("✓ Fact checker valid")

        if self.has_api_key:
            assert self.chat_model.validate_setup(), "Chat model validation failed"
            print("✓ Chat model valid")
        else:
            print("ℹ Chat model not tested (no API key)")


def test_system_startup():
    """Test that the system can start up without errors"""
    # This test ensures basic imports and initialization work
    try:
        ner = create_ner_extractor()
        search = create_search_client(use_mock=True)
        fact_checker = create_fact_checker(search)

        assert ner is not None
        assert search is not None
        assert fact_checker is not None

        print("✓ System startup test passed")

    except Exception as e:
        pytest.fail(f"System startup failed: {e}")


if __name__ == "__main__":
    # Run integration tests manually
    test_class = TestIntegration()
    test_class.setup_method()

    print("Running Citation Needed Integration Tests...")
    print("=" * 60)

    # Run tests
    test_class.test_end_to_end_pipeline_mock()
    print("✓ End-to-end pipeline test passed")

    test_class.test_famous_paper_detection_integration()
    print("✓ Famous paper detection test passed")

    test_class.test_error_handling()
    print("✓ Error handling test passed")

    test_class.test_performance_basic()
    print("✓ Basic performance test passed")

    test_class.test_component_validation()
    print("✓ Component validation test passed")

    # Test with real API if available
    if os.getenv("OPENROUTER_API_KEY"):
        test_class.test_real_chat_integration()
        print("✓ Real chat integration test passed")
    else:
        print("ℹ Skipped real chat test (no API key)")

    print("\n🎉 All integration tests passed!")
