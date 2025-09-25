#!/usr/bin/env python3
"""
Test script for enhanced citation verification system
Testing the problematic citations from the user's example
"""

import os
import sys

from dotenv import load_dotenv


# Add the current directory to the path
sys.path.insert(0, os.path.dirname(__file__))

# Import our components
from models.citation_parser import create_citation_parser
from models.fact_checker import create_fact_checker
from models.ner_extractor import create_ner_extractor
from search.firecrawl_client import create_search_client


# Load environment variables
load_dotenv()


def test_enhanced_citations():
    """Test the enhanced citation verification with problematic examples"""

    print("🧪 Enhanced Citation Verification Test")
    print("=" * 50)

    # Test cases from the user's example
    test_citations = [
        {
            "citation": '"Attention Is All You Need" by Vaswani et al. - This foundational paper introduces the transformer model, the basis for BERT and many other advancements in NLP. [Link](https://arxiv.org/abs/1706.03762)',
            "expected": "Should be verified via arXiv API",
            "has_arxiv": True,
        },
        {
            "citation": '"GPT-3: Language Models are Few-Shot Learners" by Brown et al. - Demonstrates the capabilities of massive scale language models, highlighting a different approach from BERT but equally influential. [Link](https://arxiv.org/abs/2005.14165)',
            "expected": "Should be verified via arXiv API",
            "has_arxiv": True,
        },
        {
            "citation": '"RoBERTa: A Robustly Optimized BERT Pretraining Approach" by Liu et al. - An optimized version of BERT that achieves better performance by modifying key hyperparameters and training data. [Link](https://arxiv.org/abs/1907.11692)',
            "expected": "Should be verified via arXiv API",
            "has_arxiv": True,
        },
        {
            "citation": '"XLNet: Generalized Autoregressive Pretraining for Language Understanding" by Yang et al. - Presents a novel approach that outperforms BERT on several NLP benchmarks by combining the strengths of autoregressive and autoencoding models. [Link](https://arxiv.org/abs/1906.08237)',
            "expected": "Should be verified via arXiv API",
            "has_arxiv": True,
        },
        {
            "citation": '"Deep Learning" by Goodfellow et al. - The comprehensive textbook on deep learning published by MIT Press.',
            "expected": "Should be found via book search",
            "has_arxiv": False,
        },
    ]

    # Initialize components
    try:
        print("🔧 Initializing components...")

        # Test citation parser
        citation_parser = create_citation_parser()
        print(f"✅ Citation parser: {'OK' if citation_parser.validate_setup() else 'FAILED'}")

        # Test search client (with mock if no API keys)
        use_mock = not os.getenv("FIRECRAWL_API_KEY")
        search_client = create_search_client(use_mock=use_mock)
        print(f"✅ Search client: {'OK (Mock)' if use_mock else 'OK'}")

        # Test fact checker
        fact_checker = create_fact_checker(search_client)
        print(f"✅ Fact checker: {'OK' if fact_checker.validate_setup() else 'FAILED'}")

        # Test NER extractor
        ner_extractor = create_ner_extractor()
        print(f"✅ NER extractor: {'OK' if ner_extractor.validate_setup() else 'FAILED'}")

        print("\n📋 Running citation tests...\n")

        # Test each citation
        for i, test_case in enumerate(test_citations, 1):
            print(f"🔍 Test {i}: {test_case['citation'][:80]}...")
            print(f"   Expected: {test_case['expected']}")

            try:
                # Step 1: Extract citations using NER
                raw_citations = ner_extractor.extract_citations(test_case["citation"])
                print(f"   📝 NER found {len(raw_citations)} citations")

                if raw_citations:
                    # Test the first citation found
                    citation = raw_citations[0]
                    print(f"   📄 Citation text: {citation.text[:60]}...")

                    # Step 2: Parse with structured parser
                    if citation_parser:
                        try:
                            structured = citation_parser.parse_citation(citation.text)
                            print(
                                f"   🎯 Structured parsing: {structured.first_author} ({structured.year})"
                            )
                            print(
                                f"   📊 Confidence: {structured.confidence:.2f} ({structured.extraction_method})"
                            )

                            # Show extracted components
                            if structured.arxiv_id:
                                print(f"   🔗 arXiv ID: {structured.arxiv_id}")
                            if structured.doi:
                                print(f"   🔗 DOI: {structured.doi}")
                            if structured.title:
                                print(f"   📖 Title: {structured.title[:50]}...")

                        except Exception as e:
                            print(f"   ❌ Structured parsing failed: {e}")

                    # Step 3: Test fact checking (only if not using mock)
                    if not use_mock and fact_checker:
                        try:
                            fact_check_results = fact_checker.fact_check_citations([citation])
                            if fact_check_results:
                                result = fact_check_results[0]
                                print(f"   ✅ Verification: {result.verification_status}")
                                print(f"   📈 Confidence: {result.confidence:.2f}")
                                print(f"   📝 Explanation: {result.explanation[:100]}...")

                                # Show sources found
                                if result.sources_found:
                                    print(f"   🔍 Sources found: {len(result.sources_found)}")
                                    for j, source in enumerate(result.sources_found[:2]):
                                        source_type = source.get("source", "unknown")
                                        confidence = source.get("confidence", "N/A")
                                        title = source.get("title", "No title")[:40]
                                        print(
                                            f"      {j + 1}. [{source_type}] {title} (conf: {confidence})"
                                        )

                        except Exception as e:
                            print(f"   ❌ Fact checking failed: {e}")
                    elif use_mock:
                        print("   ⏭️  Skipping fact check (using mock client)")

                else:
                    print("   ❌ No citations found by NER")

                print()

            except Exception as e:
                print(f"   ❌ Test failed: {e}\n")

        print("🎉 Test completed!")

    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

    return True


def test_direct_validation():
    """Test direct URL validation for academic sources"""
    print("\n🧪 Direct URL Validation Test")
    print("=" * 40)

    test_ids = [
        ("arxiv:1706.03762", "arXiv"),
        ("10.1007/978-3-030-12345-6_1", "DOI"),
        ("12345678", "PubMed"),
    ]

    try:
        search_client = create_search_client(use_mock=True)  # Use mock for safety

        for test_id, source_type in test_ids:
            print(f"🔍 Testing {source_type}: {test_id}")

            # Create a mock structured citation
            from models.citation_parser import StructuredCitation

            if source_type == "arXiv":
                citation = StructuredCitation(
                    original_text="Test citation",
                    authors=["Vaswani"],
                    first_author="Vaswani",
                    title="Attention Is All You Need",
                    year="2017",
                    arxiv_id=test_id,
                    confidence=0.9,
                )
            elif source_type == "DOI":
                citation = StructuredCitation(
                    original_text="Test citation",
                    authors=["Smith"],
                    first_author="Smith",
                    title="Test Paper",
                    year="2023",
                    doi=test_id,
                    confidence=0.9,
                )
            else:
                citation = StructuredCitation(
                    original_text="Test citation",
                    authors=["Johnson"],
                    first_author="Johnson",
                    title="Medical Study",
                    year="2022",
                    pmid=test_id,
                    confidence=0.9,
                )

            # Test direct validation (this will fail with mock, but shows the flow)
            try:
                results = search_client._try_direct_url_validation(
                    {"doi": citation.doi, "arxiv_id": citation.arxiv_id, "pmid": citation.pmid}
                )
                print(f"   Results: {len(results)} found")
                for result in results:
                    print(
                        f"   - {result.get('title', 'No title')} ({result.get('confidence', 'N/A')})"
                    )

            except Exception as e:
                print(f"   Error: {e}")

            print()

    except Exception as e:
        print(f"❌ Direct validation test failed: {e}")


if __name__ == "__main__":
    # Run tests
    success = test_enhanced_citations()
    test_direct_validation()

    if success:
        print("\n✅ All tests completed successfully!")
        print("\n💡 To test with real API calls:")
        print("   1. Set FIRECRAWL_API_KEY in your .env file")
        print("   2. Set OPENROUTER_API_KEY in your .env file")
        print("   3. Run this script again")
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)
