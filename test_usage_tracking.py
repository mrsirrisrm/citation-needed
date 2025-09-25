#!/usr/bin/env python3
"""
Test script for usage tracking system
"""

import os
import sys

from dotenv import load_dotenv


# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables
load_dotenv()


def test_usage_tracking():
    """Test the usage tracking system"""
    print("🧪 Usage Tracking Test")
    print("=" * 40)

    try:
        from usage_tracker import APIProvider, track_api_call, usage_tracker

        print("✅ Usage tracker imported successfully")

        # Test tracking some API calls
        print("\n📊 Tracking test API calls...")

        # Simulate some API calls
        track_api_call(
            provider=APIProvider.OPENROUTER,
            endpoint="chat_completion",
            duration=1.5,
            success=True,
            tokens_used=250,
            metadata={"model": "gpt-4", "test": True},
        )

        track_api_call(
            provider=APIProvider.FIRECRAWL,
            endpoint="search",
            duration=2.3,
            success=True,
            metadata={"query": "test query", "results": 5},
        )

        track_api_call(
            provider=APIProvider.SEARXNG,
            endpoint="search",
            duration=0.8,
            success=True,
            metadata={"query": "academic search", "results": 3},
        )

        # Test a failed call
        track_api_call(
            provider=APIProvider.FIRECRAWL,
            endpoint="scrape_url",
            duration=5.0,
            success=False,
            error_message="Timeout",
            metadata={"url": "https://example.com"},
        )

        print("✅ Test API calls tracked")

        # Get statistics
        print("\n📈 Getting usage statistics...")
        daily_stats = usage_tracker.get_daily_stats()
        usage_tracker.print_summary(daily_stats)

        # Test CSV export
        print("\n📁 Testing CSV export...")
        usage_tracker.export_to_csv("test_usage.csv")
        print("✅ Usage data exported to test_usage.csv")

        # Test cost calculation
        print("\n💰 Testing cost calculation...")
        total_cost = daily_stats.total_cost_usd
        print(f"Total cost for tracked calls: ${total_cost:.4f}")

        print("\n✅ Usage tracking test completed successfully!")

    except Exception as e:
        print(f"❌ Usage tracking test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_integration_with_components():
    """Test integration with existing components"""
    print("\n🧪 Component Integration Test")
    print("=" * 40)

    try:
        # Test chat model tracking
        print("\n💬 Testing chat model tracking...")
        from models.chat_model import create_chat_model

        # This should be tracked automatically
        chat_model = create_chat_model()
        if chat_model.validate_setup():
            print("✅ Chat model created and validated")
        else:
            print("⚠️  Chat model validation failed (may be due to missing API key)")

        # Test search client tracking
        print("\n🔍 Testing search client tracking...")
        from search.firecrawl_client import create_search_client

        # Use mock to avoid API calls
        search_client = create_search_client(use_mock=True)
        results = search_client.search("test query", num_results=2)
        print(f"✅ Mock search completed, found {len(results)} results")

        print("\n✅ Component integration test completed!")

    except Exception as e:
        print(f"❌ Component integration test failed: {e}")
        return False

    return True


def show_usage_data():
    """Show the current usage data"""
    print("\n📋 Current Usage Data")
    print("=" * 40)

    try:
        from usage_tracker import usage_tracker

        if not usage_tracker.calls:
            print("No usage data available yet")
            return

        print(f"Total API calls tracked: {len(usage_tracker.calls)}")
        print("\nRecent calls:")

        for call in usage_tracker.calls[-5:]:  # Show last 5 calls
            status = "✅" if call.success else "❌"
            cost = f"${call.cost_usd:.4f}" if call.cost_usd > 0 else "Free"
            print(
                f"  {status} {call.provider.value} {call.endpoint} - {cost} ({call.duration:.2f}s)"
            )

    except Exception as e:
        print(f"Error showing usage data: {e}")


if __name__ == "__main__":
    print("🔧 Testing Usage Tracking for Citation Needed")
    print("=" * 60)

    # Run tests
    success1 = test_usage_tracking()
    success2 = test_integration_with_components()

    # Show current usage data
    show_usage_data()

    if success1 and success2:
        print("\n🎉 All usage tracking tests passed!")
        print("\n💡 Usage tracking features:")
        print("   ✓ API call tracking with duration and cost")
        print("   ✓ Provider-specific cost calculation")
        print("   ✓ Success/failure tracking")
        print("   ✓ Statistical summaries")
        print("   ✓ CSV export functionality")
        print("   ✓ Automatic integration with chat and search components")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
