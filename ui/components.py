import html

from models.fact_checker import FactCheckResult
from models.ner_extractor import Citation


def create_highlighted_text(
    text: str, citations: list[Citation], fact_check_results: list[FactCheckResult]
) -> str:
    """
    Create HTML with highlighted citations and associated fact-check results

    Args:
        text: Original text
        citations: List of citations found in text
        fact_check_results: Fact-check results for the citations

    Returns:
        HTML string with highlighted citations
    """
    if not citations:
        return html.escape(text)

    # Create mapping of citations to fact-check results
    citation_results = {}
    for result in fact_check_results:
        citation_key = f"{result.citation.start}_{result.citation.end}"
        citation_results[citation_key] = result

    # Sort citations by start position (reverse order for processing)
    sorted_citations = sorted(citations, key=lambda c: c.start, reverse=True)

    highlighted_text = text
    citation_ids = {}

    # Process citations from end to start to maintain positions
    for i, citation in enumerate(sorted_citations):
        citation_id = f"citation_{len(sorted_citations) - i}"
        citation_key = f"{citation.start}_{citation.end}"

        # Get fact-check result
        fact_result = citation_results.get(citation_key)
        status_class = _get_status_class(
            fact_result.verification_status if fact_result else "unknown"
        )

        # Create highlighted span
        citation_text = citation.text
        escaped_text = html.escape(citation_text)

        highlight_html = (
            f'<span class="citation-highlight {status_class}" '
            f'id="{citation_id}" '
            f'data-citation-id="{citation_id}" '
            f'title="Click to see fact-check details">'
            f"{escaped_text}"
            f"</span>"
        )

        # Replace in text
        highlighted_text = (
            highlighted_text[: citation.start] + highlight_html + highlighted_text[citation.end :]
        )

        citation_ids[citation_id] = {"citation": citation, "result": fact_result}

    return highlighted_text


def create_fact_check_panel(fact_check_results: list[FactCheckResult]) -> str:
    """
    Create HTML for the fact-check panel showing all results

    Args:
        fact_check_results: List of fact-check results

    Returns:
        HTML string for the fact-check panel
    """
    if not fact_check_results:
        return """
        <div class="fact-check-empty" style="color: #666666 !important;">
            <p>No citations detected in this message.</p>
            <p>Academic citations will be automatically fact-checked and appear here.</p>
        </div>
        """

    comments_html = ""
    for i, result in enumerate(fact_check_results):
        citation_id = f"citation_{i + 1}"
        comment_html = _create_citation_comment(citation_id, result)
        comments_html += comment_html

    panel_html = f"""
    <div class="fact-check-panel" style="color: #333333 !important;">
        <div class="fact-check-results">
            {comments_html}
        </div>
    </div>
    """

    return panel_html


def _create_citation_comment(citation_id: str, result: FactCheckResult) -> str:
    """Create HTML for a single citation comment"""

    # Truncate citation text for display
    citation_display = result.citation.text
    if len(citation_display) > 60:
        citation_display = citation_display[:57] + "..."

    status_class = _get_status_class(result.verification_status)
    status_display = _get_status_display(result.verification_status)

    # Create sources HTML
    sources_html = ""
    if result.sources_found:
        sources_html = '<div class="comment-sources">'
        sources_html += '<div class="sources-title">Sources Found:</div>'

        for source in result.sources_found[:3]:  # Show max 3 sources
            title = html.escape(source.get("title", "Untitled")[:50])
            url = html.escape(source.get("url", ""))

            sources_html += f"""
            <div class="source-item">
                <a href="{url}" target="_blank" class="source-title" rel="noopener noreferrer">
                    {title}
                </a>
                <div class="source-url">{url}</div>
            </div>
            """

        sources_html += "</div>"
    elif result.verification_status == "not_found":
        sources_html = (
            '<div class="comment-sources"><div class="sources-title">No sources found</div></div>'
        )

    # Confidence score
    confidence_html = f"""
    <div class="confidence-score">
        Confidence: {result.confidence:.1%}
    </div>
    """

    comment_html = f"""
    <div class="citation-comment" data-citation-id="{citation_id}">
        <div class="comment-header" onclick="toggleComment('{citation_id}')">
            <div class="comment-citation-text">{html.escape(citation_display)}</div>
            <div class="comment-status">
                <span class="status-badge {status_class}">{status_display}</span>
                <span class="expand-icon" id="icon_{citation_id}">▼</span>
            </div>
        </div>
        <div class="comment-content" id="content_{citation_id}">
            <div class="comment-explanation">
                {html.escape(result.explanation)}
            </div>
            {sources_html}
            {confidence_html}
        </div>
    </div>
    """

    return comment_html


def _get_status_class(status: str) -> str:
    """Get CSS class for verification status"""
    status_classes = {
        "verified": "status-verified citation-verified",
        "not_found": "status-not-found citation-not-found",
        "contradicted": "status-contradicted citation-contradicted",
        "error": "status-error citation-error",
        "partial": "status-not-found citation-not-found",
    }
    return status_classes.get(status, "status-error citation-error")


def _get_status_display(status: str) -> str:
    """Get display text for verification status"""
    status_displays = {
        "verified": "Verified",
        "not_found": "Not Found",
        "contradicted": "Contradicted",
        "error": "Error",
        "partial": "Partial",
    }
    return status_displays.get(status, "Unknown")


def create_loading_panel() -> str:
    """Create HTML for loading state"""
    return """
    <div class="fact-check-loading">
        <div class="loading-spinner"></div>
        <span>Fact-checking citations...</span>
    </div>
    """


def create_javascript_components() -> str:
    """Create JavaScript for interactive components"""
    return """
    <script>
    function toggleComment(citationId) {
        const content = document.getElementById('content_' + citationId);
        const icon = document.getElementById('icon_' + citationId);

        if (content.classList.contains('expanded')) {
            content.classList.remove('expanded');
            icon.classList.remove('expanded');
            icon.textContent = '▼';
        } else {
            content.classList.add('expanded');
            icon.classList.add('expanded');
            icon.textContent = '▲';
        }
    }

    function highlightCitation(citationId) {
        // Remove previous highlights
        document.querySelectorAll('.citation-highlight').forEach(el => {
            el.classList.remove('active-highlight');
        });

        // Highlight selected citation
        const citation = document.getElementById(citationId);
        if (citation) {
            citation.classList.add('active-highlight');
            citation.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    // Add click handlers to citations
    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('.citation-highlight').forEach(el => {
            el.addEventListener('click', function() {
                const citationId = this.getAttribute('data-citation-id');
                highlightCitation(citationId);

                // Scroll to corresponding comment
                const comment = document.querySelector(`[data-citation-id="${citationId}"]`);
                if (comment) {
                    comment.scrollIntoView({ behavior: 'smooth', block: 'start' });

                    // Expand comment if not already expanded
                    const content = document.getElementById('content_' + citationId);
                    if (content && !content.classList.contains('expanded')) {
                        toggleComment(citationId);
                    }
                }
            });
        });
    });
    </script>

    <style>
    .active-highlight {
        box-shadow: 0 0 0 2px #2196F3 !important;
        z-index: 10;
        position: relative;
    }
    </style>
    """


def format_message_with_citations(
    message: str, fact_check_results: list[FactCheckResult]
) -> tuple[str, str]:
    """
    Format a message with citations and return both highlighted text and fact-check panel

    Args:
        message: Original message text
        fact_check_results: Fact-check results

    Returns:
        Tuple of (highlighted_message_html, fact_check_panel_html)
    """
    # Extract citations from results
    citations = [result.citation for result in fact_check_results] if fact_check_results else []

    # Create highlighted text
    highlighted_text = create_highlighted_text(message, citations, fact_check_results)

    # Create fact-check panel
    fact_check_panel = create_fact_check_panel(fact_check_results)

    # Wrap highlighted text in container
    message_html = f"""
    <div class="message-with-citations" style="color: #333333 !important;">
        {highlighted_text}
    </div>
    {create_javascript_components()}
    """

    return message_html, fact_check_panel
