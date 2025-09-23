#!/usr/bin/env python3
"""
Test script for SearXNG integration
"""

import os
import sys

from dotenv import load_dotenv


# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables
load_dotenv()

def test_searxng_client():
    """Test the SearXNG client integration"""
    print("🧪 SearXNG Integration Test")
    print("=" * 40)

    try:
        # Test SearXNG client
        from search.searxng_client import SearXNGSearchClient

        # Get SearXNG URL from environment or use default
        searxng_url = os.getenv("SEARXNG_URL", "http://localhost:8080")
        print(f"🔗 Testing SearXNG at: {searxng_url}")

        # Initialize client
        client = SearXNGSearchClient(searxng_url)
        print("✅ SearXNG client initialized successfully")

        # Test basic search
        print("\n🔍 Testing basic search...")
        results = client.search("machine learning", num_results=3)
        print(f"📊 Found {len(results)} results")

        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")[:60]
            url = result.get("url", "No URL")[:60]
            confidence = result.get("confidence", 0)
            print(f"  {i}. {title} (conf: {confidence:.2f})")
            print(f"     URL: {url}")

        # Test academic search
        print("\n🎓 Testing academic search...")
        academic_results = client.academic_search("transformer architecture", num_results=3)
        print(f"📊 Found {len(academic_results)} academic results")

        for i, result in enumerate(academic_results, 1):
            title = result.get("title", "No title")[:60]
            engine = result.get("metadata", {}).get("engine", "unknown")
            print(f"  {i}. [{engine}] {title}")

        # Test citation search
        print("\n📚 Testing citation search...")
        test_citation = {
            "title": "Attention Is All You Need",
            "first_author": "Vaswani",
            "year": "2017",
            "doi": "10.48550/arXiv.1706.03762"
        }

        citation_results = client.enhanced_citation_search("Vaswani et al. (2017)", test_citation)
        print(f"📊 Found {len(citation_results)} citation results")

        for i, result in enumerate(citation_results[:3], 1):
            title = result.get("title", "No title")[:60]
            source = result.get("source", "unknown")
            confidence = result.get("confidence", 0)
            print(f"  {i}. [{source}] {title} (conf: {confidence:.2f})")

        print("\n✅ SearXNG integration test completed successfully!")

    except Exception as e:
        print(f"❌ SearXNG test failed: {e}")
        print("\n💡 Make sure SearXNG is running and accessible")
        print("   - If using Docker: docker run -p 8080:8080 searxng/searxng")
        print("   - Or set SEARXNG_URL environment variable")
        return False

    return True

def test_search_client_factory():
    """Test the search client factory with SearXNG"""
    print("\n🧪 Search Client Factory Test")
    print("=" * 40)

    try:
        from search.firecrawl_client import create_search_client

        # Test SearXNG client through factory
        print("🏭 Testing SearXNG client through factory...")
        searxng_url = os.getenv("SEARXNG_URL")
        if searxng_url:
            client = create_search_client(use_searxng=True)
            print(f"✅ Factory created client: {type(client).__name__}")
            print(f"✅ Client validation: {client.validate_setup()}")
        else:
            print("⚠️  SEARXNG_URL not set, skipping factory test")

        # Test Firecrawl fallback
        print("\n🔥 Testing Firecrawl fallback...")
        try:
            firecrawl_client = create_search_client(use_searxng=False)
            print(f"✅ Firecrawl client: {type(firecrawl_client).__name__}")
        except Exception as e:
            print(f"⚠️  Firecrawl not available: {e}")

        print("\n✅ Search client factory test completed!")

    except Exception as e:
        print(f"❌ Factory test failed: {e}")
        return False

    return True

if __name__ == "__main__":
    print("🔧 Testing SearXNG Integration for Citation Needed")
    print("=" * 60)

    # Run tests
    success1 = test_searxng_client()
    success2 = test_search_client_factory()

    if success1 and success2:
        print("\n🎉 All SearXNG tests passed!")
        print("\n💡 To use SearXNG in the main application:")
        print("   1. Set SEARXNG_URL=http://localhost:8080 in your .env file")
        print("   2. Make sure SearXNG is running")
        print("   3. Run: python app.py")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
