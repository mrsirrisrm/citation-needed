import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum


class APIProvider(Enum):
    """API providers for tracking"""
    OPENROUTER = "openrouter"
    FIRECRAWL = "firecrawl"
    SEARXNG = "searxng"  # Local, so no cost but good to track usage
    ARXIV = "arxiv"      # Free API
    DOI = "doi"         # Free API
    PUBMED = "pubmed"   # Free API


@dataclass
class APICall:
    """Represents a single API call"""
    provider: APIProvider
    endpoint: str
    timestamp: datetime
    duration: float  # in seconds
    success: bool
    cost_usd: float = 0.0
    tokens_used: int = 0
    error_message: str | None = None
    metadata: dict | None = None


@dataclass
class UsageStats:
    """Usage statistics for a time period"""
    period_start: datetime
    period_end: datetime
    total_calls: int
    successful_calls: int
    failed_calls: int
    total_cost_usd: float
    total_tokens: int
    average_duration: float
    provider_breakdown: dict[str, dict]
    top_endpoints: list[dict]


class UsageTracker:
    """Tracks API usage and costs"""

    def __init__(self, data_file: str = "usage_data.json"):
        self.data_file = data_file
        self.calls: list[APICall] = []
        self.cost_rates = {
            # OpenRouter rates (approximate, should be configured based on actual model)
            APIProvider.OPENROUTER: {
                "input_tokens_per_1k": 0.001,  # $0.001 per 1K input tokens
                "output_tokens_per_1k": 0.002,  # $0.002 per 1K output tokens
                "default_cost_per_call": 0.01   # Default cost if tokens not available
            },
            # Firecrawl rates
            APIProvider.FIRECRAWL: {
                "scrape_per_page": 0.001,       # $0.001 per page scrape
                "search_per_query": 0.01,       # $0.01 per search query
                "default_cost_per_call": 0.005
            },
            # SearXNG is free (local instance)
            APIProvider.SEARXNG: {
                "default_cost_per_call": 0.0
            },
            # Academic APIs are free
            APIProvider.ARXIV: {"default_cost_per_call": 0.0},
            APIProvider.DOI: {"default_cost_per_call": 0.0},
            APIProvider.PUBMED: {"default_cost_per_call": 0.0}
        }

        self.load_data()

    def load_data(self):
        """Load usage data from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file) as f:
                    data = json.load(f)
                    # Convert loaded data back to APICall objects
                    self.calls = []
                    for call_data in data.get('calls', []):
                        call = APICall(
                            provider=APIProvider(call_data['provider']),
                            endpoint=call_data['endpoint'],
                            timestamp=datetime.fromisoformat(call_data['timestamp']),
                            duration=call_data['duration'],
                            success=call_data['success'],
                            cost_usd=call_data.get('cost_usd', 0.0),
                            tokens_used=call_data.get('tokens_used', 0),
                            error_message=call_data.get('error_message'),
                            metadata=call_data.get('metadata')
                        )
                        self.calls.append(call)
        except Exception as e:
            print(f"Warning: Could not load usage data: {e}")
            self.calls = []

    def save_data(self):
        """Save usage data to file"""
        try:
            data = {
                'calls': [asdict(call) for call in self.calls],
                'last_updated': datetime.now().isoformat()
            }

            # Convert datetime objects to strings and APIProvider enum to string for
            # JSON serialization
            for call_data in data['calls']:
                call_data['timestamp'] = call_data['timestamp'].isoformat()
                call_data['provider'] = call_data['provider'].value

            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save usage data: {e}")

    def track_call(self, provider: APIProvider, endpoint: str, duration: float,
                   success: bool = True, tokens_used: int = 0,
                   error_message: str | None = None, metadata: dict | None = None):
        """
        Track an API call

        Args:
            provider: API provider
            endpoint: API endpoint or operation
            duration: Call duration in seconds
            success: Whether the call was successful
            tokens_used: Number of tokens used (for LLM calls)
            error_message: Error message if call failed
            metadata: Additional metadata about the call
        """
        cost_usd = self.calculate_cost(provider, endpoint, tokens_used, success)

        call = APICall(
            provider=provider,
            endpoint=endpoint,
            timestamp=datetime.now(),
            duration=duration,
            success=success,
            cost_usd=cost_usd,
            tokens_used=tokens_used,
            error_message=error_message,
            metadata=metadata or {}
        )

        self.calls.append(call)

        # Keep only last 10,000 calls to prevent file from growing too large
        if len(self.calls) > 10000:
            self.calls = self.calls[-10000:]

        self.save_data()

        # Log expensive calls
        if cost_usd > 0.01:  # Log calls costing more than 1 cent
            print(f"💰 API call: {provider.value} {endpoint} - ${cost_usd:.4f}")

    def calculate_cost(self, provider: APIProvider, endpoint: str,
                      tokens_used: int, success: bool) -> float:
        """Calculate cost for an API call"""
        if not success:
            return 0.0  # Don't charge for failed calls

        rates = self.cost_rates.get(provider, {})
        default_cost = rates.get("default_cost_per_call", 0.0)

        if provider == APIProvider.OPENROUTER and tokens_used > 0:
            # For OpenRouter, estimate based on tokens
            # Assume 50/50 split between input and output tokens
            input_tokens = tokens_used // 2
            output_tokens = tokens_used - input_tokens

            input_cost = (input_tokens / 1000) * rates.get("input_tokens_per_1k", 0.001)
            output_cost = (output_tokens / 1000) * rates.get("output_tokens_per_1k", 0.002)

            return input_cost + output_cost

        elif provider == APIProvider.FIRECRAWL:
            if "search" in endpoint.lower():
                return rates.get("search_per_query", 0.01)
            elif "scrape" in endpoint.lower():
                return rates.get("scrape_per_page", 0.001)

        return default_cost

    def get_stats(self, period_hours: int = 24) -> UsageStats:
        """
        Get usage statistics for a time period

        Args:
            period_hours: Number of hours to include in stats

        Returns:
            UsageStats object with period statistics
        """
        now = datetime.now()
        period_start = now - timedelta(hours=period_hours)

        # Filter calls for the period
        period_calls = [
            call for call in self.calls
            if call.timestamp >= period_start
        ]

        if not period_calls:
            return UsageStats(
                period_start=period_start,
                period_end=now,
                total_calls=0,
                successful_calls=0,
                failed_calls=0,
                total_cost_usd=0.0,
                total_tokens=0,
                average_duration=0.0,
                provider_breakdown={},
                top_endpoints=[]
            )

        # Calculate basic stats
        total_calls = len(period_calls)
        successful_calls = sum(1 for call in period_calls if call.success)
        failed_calls = total_calls - successful_calls
        total_cost_usd = sum(call.cost_usd for call in period_calls)
        total_tokens = sum(call.tokens_used for call in period_calls)
        average_duration = sum(call.duration for call in period_calls) / total_calls

        # Provider breakdown
        provider_stats = {}
        for call in period_calls:
            provider = call.provider.value
            if provider not in provider_stats:
                provider_stats[provider] = {
                    'calls': 0,
                    'successful_calls': 0,
                    'cost_usd': 0.0,
                    'tokens_used': 0,
                    'avg_duration': 0.0
                }

            provider_stats[provider]['calls'] += 1
            if call.success:
                provider_stats[provider]['successful_calls'] += 1
            provider_stats[provider]['cost_usd'] += call.cost_usd
            provider_stats[provider]['tokens_used'] += call.tokens_used

        # Calculate average duration per provider
        for provider, stats in provider_stats.items():
            provider_calls = [c for c in period_calls if c.provider.value == provider]
            if provider_calls:
                stats['avg_duration'] = sum(c.duration for c in provider_calls) / len(provider_calls)

        # Top endpoints by call count
        endpoint_counts = {}
        for call in period_calls:
            endpoint_key = f"{call.provider.value}:{call.endpoint}"
            endpoint_counts[endpoint_key] = endpoint_counts.get(endpoint_key, 0) + 1

        top_endpoints = [
            {'endpoint': endpoint, 'calls': count}
            for endpoint, count in sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        return UsageStats(
            period_start=period_start,
            period_end=now,
            total_calls=total_calls,
            successful_calls=successful_calls,
            failed_calls=failed_calls,
            total_cost_usd=total_cost_usd,
            total_tokens=total_tokens,
            average_duration=average_duration,
            provider_breakdown=provider_stats,
            top_endpoints=top_endpoints
        )

    def get_daily_stats(self) -> UsageStats:
        """Get stats for the last 24 hours"""
        return self.get_stats(24)

    def get_weekly_stats(self) -> UsageStats:
        """Get stats for the last 7 days"""
        return self.get_stats(24 * 7)

    def get_monthly_stats(self) -> UsageStats:
        """Get stats for the last 30 days"""
        return self.get_stats(24 * 30)

    def print_summary(self, stats: UsageStats):
        """Print a human-readable summary of usage stats"""
        print(f"\n📊 Usage Summary ({stats.period_start.strftime('%Y-%m-%d %H:%M')} - {stats.period_end.strftime('%Y-%m-%d %H:%M')})")
        print("=" * 80)
        print(f"Total Calls: {stats.total_calls}")
        print(f"Successful: {stats.successful_calls} ({stats.successful_calls/max(1, stats.total_calls)*100:.1f}%)")
        print(f"Failed: {stats.failed_calls}")
        print(f"Total Cost: ${stats.total_cost_usd:.4f}")
        print(f"Total Tokens: {stats.total_tokens:,}")
        print(f"Average Duration: {stats.average_duration:.2f}s")

        if stats.provider_breakdown:
            print("\n🏢 Provider Breakdown:")
            for provider, provider_stats in stats.provider_breakdown.items():
                success_rate = provider_stats['successful_calls'] / max(1, provider_stats['calls']) * 100
                print(f"  {provider.upper()}: {provider_stats['calls']} calls, "
                      f"${provider_stats['cost_usd']:.4f}, "
                      f"{success_rate:.1f}% success")

        if stats.top_endpoints:
            print("\n🔝 Top Endpoints:")
            for i, endpoint in enumerate(stats.top_endpoints[:5], 1):
                print(f"  {i}. {endpoint['endpoint']}: {endpoint['calls']} calls")

    def export_to_csv(self, filename: str, period_hours: int = 24):
        """Export usage data to CSV file"""
        import csv

        period_start = datetime.now() - timedelta(hours=period_hours)
        period_calls = [
            call for call in self.calls
            if call.timestamp >= period_start
        ]

        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'provider', 'endpoint', 'duration', 'success',
                         'cost_usd', 'tokens_used', 'error_message']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for call in period_calls:
                writer.writerow({
                    'timestamp': call.timestamp.isoformat(),
                    'provider': call.provider.value,
                    'endpoint': call.endpoint,
                    'duration': call.duration,
                    'success': call.success,
                    'cost_usd': call.cost_usd,
                    'tokens_used': call.tokens_used,
                    'error_message': call.error_message or ''
                })

        print(f"📁 Exported {len(period_calls)} calls to {filename}")


# Global usage tracker instance
usage_tracker = UsageTracker()


def track_api_call(provider: APIProvider, endpoint: str, duration: float,
                  success: bool = True, tokens_used: int = 0,
                  error_message: str | None = None, metadata: dict | None = None):
    """Convenience function to track API calls"""
    usage_tracker.track_call(
        provider=provider,
        endpoint=endpoint,
        duration=duration,
        success=success,
        tokens_used=tokens_used,
        error_message=error_message,
        metadata=metadata
    )


class UsageTrackerDecorator:
    """Decorator for tracking function calls"""

    def __init__(self, provider: APIProvider, endpoint: str):
        self.provider = provider
        self.endpoint = endpoint

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None
            tokens_used = 0
            result = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                duration = time.time() - start_time

                # Try to extract tokens from result if it's an LLM call
                if success and result:
                    try:
                        if hasattr(result, 'usage'):
                            # OpenAI-style usage
                            tokens_used = result.usage.get('total_tokens', 0)
                        elif isinstance(result, dict) and 'usage' in result:
                            tokens_used = result.get('usage', {}).get('total_tokens', 0)
                    except Exception:
                        pass

                track_api_call(
                    provider=self.provider,
                    endpoint=self.endpoint,
                    duration=duration,
                    success=success,
                    tokens_used=tokens_used,
                    error_message=error_message
                )

        return wrapper
