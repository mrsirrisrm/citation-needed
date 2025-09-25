"""
Type definitions for internal data structures using NamedTuple
Provides type safety and better documentation for dict-based data
"""

from typing import (  # For backwards compatibility during transition
    Any,
    NamedTuple,
)


class SearchResult(NamedTuple):
    """Result from search operations across all search clients"""

    title: str
    url: str
    content: str
    source: str = "unknown"
    description: str = ""
    markdown: str = ""
    metadata: dict[str, Any] | None = None
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backwards compatibility"""
        result = {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "source": self.source,
            "description": self.description,
            "markdown": self.markdown,
            "confidence": self.confidence,
        }
        if self.metadata is not None:
            result["metadata"] = self.metadata
        return result


class CitationComponents(NamedTuple):
    """Structured components extracted from citation text"""

    authors: list[str] = []
    title: str | None = None
    year: str | None = None
    journal: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    pmid: str | None = None
    isbn: str | None = None
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backwards compatibility"""
        return {
            "authors": list(self.authors),
            "title": self.title,
            "year": self.year,
            "journal": self.journal,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "pmid": self.pmid,
            "isbn": self.isbn,
            "url": self.url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CitationComponents":
        """Create from dictionary for backwards compatibility"""
        return cls(
            authors=data.get("authors", []),
            title=data.get("title"),
            year=data.get("year"),
            journal=data.get("journal"),
            doi=data.get("doi"),
            arxiv_id=data.get("arxiv_id"),
            pmid=data.get("pmid"),
            isbn=data.get("isbn"),
            url=data.get("url"),
        )


class VerificationStatus(NamedTuple):
    """Internal verification result from fact checker"""

    status: str  # "verified", "not_found", "disputed", "unreliable"
    confidence: float
    explanation: str
    sources_count: int = 0
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backwards compatibility"""
        result = {
            "status": self.status,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "sources_count": self.sources_count,
        }
        if self.details is not None:
            result["details"] = self.details
        return result


class TaskStatus(NamedTuple):
    """Status result for async task operations"""

    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: float = 0.0
    message: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses"""
        response = {"task_id": self.task_id, "status": self.status, "progress": self.progress}
        if self.message is not None:
            response["message"] = self.message
        if self.result is not None:
            response["result"] = self.result
        if self.error is not None:
            response["error"] = self.error
        return response


class ProviderStats(NamedTuple):
    """Statistics for API provider usage"""

    provider: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    total_cost: float
    average_duration: float
    success_rate: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for display"""
        return {
            "provider": self.provider,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "total_cost": self.total_cost,
            "average_duration": self.average_duration,
            "success_rate": self.success_rate,
        }


class EndpointStats(NamedTuple):
    """Statistics for specific API endpoint usage"""

    endpoint: str
    calls: int
    average_duration: float
    success_rate: float
    total_cost: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for display"""
        return {
            "endpoint": self.endpoint,
            "calls": self.calls,
            "average_duration": self.average_duration,
            "success_rate": self.success_rate,
            "total_cost": self.total_cost,
        }
