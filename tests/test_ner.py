#!/usr/bin/env python3
"""
Tests for the NER (Named Entity Recognition) citation extractor
"""
import pytest
from models.ner_extractor import create_ner_extractor, Citation


class TestNERExtractor:
    """Test suite for citation extraction"""

    def setup_method(self):
        """Set up test fixtures"""
        self.ner = create_ner_extractor()

    def test_famous_papers_detection(self):
        """Test detection of famous academic papers"""
        test_cases = [
            # Original Transformer paper (Vaswani et al.)
            {
                "text": "The groundbreaking work by Vaswani et al. (2017) introduced the attention mechanism.",
                "expected_citations": ["Vaswani et al. (2017)"],
                "description": "Attention Is All You Need paper"
            },
            # Alternative format - should detect at least the journal part
            {
                "text": "As described in Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., ... & Polosukhin, I. (2017). Attention is all you need. Advances in neural information processing systems, 30.",
                "expected_citations": ["(2017). Attention is all you need", "Polosukhin, I. (2017)"],  # More flexible matching
                "description": "Full citation format"
            },
            # BERT paper
            {
                "text": "BERT was introduced by Devlin et al. (2018) and revolutionized NLP.",
                "expected_citations": ["Devlin et al. (2018)"],
                "description": "BERT paper"
            },
            # GPT paper
            {
                "text": "The original GPT model (Radford et al., 2018) showed the potential of unsupervised learning.",
                "expected_citations": ["(Radford et al., 2018)"],
                "description": "GPT paper in parentheses"
            },
            # ResNet paper
            {
                "text": "Deep residual networks (He et al., 2016) solved the vanishing gradient problem.",
                "expected_citations": ["(He et al., 2016)"],
                "description": "ResNet paper"
            },
        ]

        for case in test_cases:
            citations = self.ner.extract_citations(case["text"])
            citation_texts = [c.text for c in citations]

            print(f"\nTesting: {case['description']}")
            print(f"Text: {case['text']}")
            print(f"Found: {citation_texts}")
            print(f"Expected: {case['expected_citations']}")

            assert len(citations) > 0, f"No citations found for {case['description']}"

            # Check if at least one expected citation is found
            found_expected = any(
                expected in citation_texts for expected in case["expected_citations"]
            )
            assert found_expected, f"Expected citation not found for {case['description']}"

    def test_arxiv_papers(self):
        """Test detection of arXiv papers"""
        test_cases = [
            {
                "text": "Recent work on arXiv:2301.00234 shows promising results.",
                "expected_type": "preprint",
                "expected_text": "arXiv:2301.00234"
            },
            {
                "text": "The paper arXiv:1706.03762 introduced the Transformer architecture.",
                "expected_type": "preprint",
                "expected_text": "arXiv:1706.03762"
            },
        ]

        for case in test_cases:
            citations = self.ner.extract_citations(case["text"])

            assert len(citations) > 0, f"No citations found in: {case['text']}"

            found_citation = None
            for citation in citations:
                if case["expected_text"] in citation.text:
                    found_citation = citation
                    break

            assert found_citation is not None, f"Expected citation '{case['expected_text']}' not found"
            assert found_citation.citation_type == case["expected_type"]

    def test_doi_citations(self):
        """Test detection of DOI citations"""
        test_cases = [
            {
                "text": "The study can be found at DOI: 10.1038/nature14539.",
                "expected_type": "doi",
                "expected_text": "DOI: 10.1038/nature14539"
            },
            {
                "text": "See https://doi.org/10.1126/science.aaa1234 for details.",
                "expected_type": "doi",
                "expected_text": "https://doi.org/10.1126/science.aaa1234"
            },
        ]

        for case in test_cases:
            citations = self.ner.extract_citations(case["text"])

            assert len(citations) > 0, f"No citations found in: {case['text']}"

            # Check citation type
            found_doi = False
            for citation in citations:
                if citation.citation_type == case["expected_type"]:
                    found_doi = True
                    break

            assert found_doi, f"DOI citation not detected in: {case['text']}"

    def test_journal_citations(self):
        """Test detection of full journal citations"""
        test_cases = [
            {
                "text": "Smith, J. (2023). Deep Learning Advances. Nature Machine Intelligence, 15(3), 123-145.",
                "expected_type": "author_year",
                "min_confidence": 0.8
            },
            {
                "text": "Johnson, A., & Brown, B. (2022). AI Research Methods. Science, 376(6594), 789-792.",
                "expected_type": "author_year",
                "min_confidence": 0.8
            },
        ]

        for case in test_cases:
            citations = self.ner.extract_citations(case["text"])

            assert len(citations) > 0, f"No citations found in: {case['text']}"

            # Check confidence and type
            for citation in citations:
                assert citation.confidence >= case["min_confidence"], \
                    f"Low confidence ({citation.confidence}) for: {citation.text}"

                # Should detect author and year components
                assert citation.year is not None, f"Year not extracted from: {citation.text}"

    def test_confidence_scoring(self):
        """Test confidence scoring for different citation qualities"""
        test_cases = [
            {
                "text": "According to Smith et al. (2023), machine learning continues to advance.",
                "min_confidence": 0.9,  # High confidence for clear citation
                "description": "Clear author-year citation"
            },
            {
                "text": "DOI: 10.1038/nature12345",
                "min_confidence": 0.95,  # Very high confidence for DOI
                "description": "DOI citation"
            },
            {
                "text": "Some text with (2023) but no author.",
                "max_confidence": 0.3,  # Should be low confidence or not detected
                "description": "Year only, no author"
            },
        ]

        for case in test_cases:
            citations = self.ner.extract_citations(case["text"])

            if "min_confidence" in case:
                assert len(citations) > 0, f"No citations found for: {case['description']}"
                max_conf = max(c.confidence for c in citations)
                assert max_conf >= case["min_confidence"], \
                    f"Confidence too low ({max_conf}) for: {case['description']}"

            if "max_confidence" in case:
                if citations:
                    max_conf = max(c.confidence for c in citations)
                    assert max_conf <= case["max_confidence"], \
                        f"Confidence too high ({max_conf}) for: {case['description']}"

    def test_no_false_positives(self):
        """Test that non-citations are not detected"""
        test_cases = [
            "I was born in (1990) and graduated in 2012.",
            "The meeting is scheduled for (Monday) at 3pm.",
            "Please call me at (555) 123-4567.",
            "The price is ($50) for the basic package.",
            "Version 2.1.0 was released in March.",
        ]

        for text in test_cases:
            citations = self.ner.extract_citations(text)
            # Should find few or no citations
            assert len(citations) <= 1, f"False positive detected in: {text}"

            # If any citation found, confidence should be low
            for citation in citations:
                assert citation.confidence < 0.7, \
                    f"High confidence false positive: {citation.text} in {text}"

    def test_multiple_citations_in_text(self):
        """Test extraction of multiple citations from single text"""
        text = """
        The transformer architecture was introduced by Vaswani et al. (2017),
        which built upon previous attention mechanisms (Bahdanau et al., 2014).
        Later improvements include BERT (Devlin et al., 2018) and GPT-2 (Radford et al., 2019).
        For implementation details, see DOI: 10.1038/s41586-021-03819-2 and arXiv:2005.14165.
        """

        citations = self.ner.extract_citations(text)

        # Should find multiple citations
        assert len(citations) >= 4, f"Expected at least 4 citations, found {len(citations)}"

        # Check for expected citations
        citation_texts = [c.text for c in citations]
        expected_patterns = ["Vaswani et al. (2017)", "Devlin et al. (2018)", "DOI:", "arXiv:"]

        for pattern in expected_patterns:
            found = any(pattern in text for text in citation_texts)
            assert found, f"Expected pattern '{pattern}' not found in citations"

    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        test_cases = [
            {
                "text": "",  # Empty string
                "expected_count": 0
            },
            {
                "text": "et al.",  # Just the phrase
                "expected_count": 0
            },
            {
                "text": "(2023)",  # Just a year
                "expected_count": 0
            },
            {
                "text": "Smith et al. (2023) Smith et al. (2023)",  # Duplicate
                "expected_count": 1  # Should deduplicate
            },
        ]

        for case in test_cases:
            citations = self.ner.extract_citations(case["text"])
            assert len(citations) == case["expected_count"], \
                f"Expected {case['expected_count']} citations for '{case['text']}', got {len(citations)}"

    def test_citation_components_extraction(self):
        """Test extraction of citation components"""
        test_cases = [
            {
                "text": "Smith et al. (2023) conducted the study.",
                "expected_authors": ["Smith"],
                "expected_year": "2023"
            },
            {
                "text": "The paper DOI: 10.1038/nature12345 provides evidence.",
                "expected_doi": "10.1038/nature12345"
            },
        ]

        for case in test_cases:
            citations = self.ner.extract_citations(case["text"])
            assert len(citations) > 0, f"No citations found in: {case['text']}"

            citation = citations[0]

            if "expected_authors" in case:
                assert citation.authors is not None, "Authors not extracted"
                assert len(citation.authors) > 0, "No authors found"

            if "expected_year" in case:
                assert citation.year == case["expected_year"], \
                    f"Expected year {case['expected_year']}, got {citation.year}"

            if "expected_doi" in case:
                assert citation.doi == case["expected_doi"], \
                    f"Expected DOI {case['expected_doi']}, got {citation.doi}"


def test_ner_validation():
    """Test that NER system validates correctly"""
    ner = create_ner_extractor()
    assert ner.validate_setup(), "NER validation failed"


if __name__ == "__main__":
    # Run tests manually
    test_class = TestNERExtractor()
    test_class.setup_method()

    print("Running NER Citation Extraction Tests...")
    print("=" * 50)

    # Run key tests
    test_class.test_famous_papers_detection()
    print("✓ Famous papers detection tests passed")

    test_class.test_arxiv_papers()
    print("✓ arXiv papers detection tests passed")

    test_class.test_doi_citations()
    print("✓ DOI citations detection tests passed")

    test_class.test_confidence_scoring()
    print("✓ Confidence scoring tests passed")

    test_class.test_no_false_positives()
    print("✓ False positive prevention tests passed")

    test_class.test_multiple_citations_in_text()
    print("✓ Multiple citations detection tests passed")

    print("\n🎉 All NER tests passed!")