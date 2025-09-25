import json
import os
import re
from dataclasses import dataclass

import dspy


@dataclass
class StructuredCitation:
    """Structured representation of a parsed citation"""

    original_text: str
    authors: list[str]
    first_author: str
    title: str
    year: str
    journal: str | None = None
    conference: str | None = None
    book_title: str | None = None
    publisher: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    pmid: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    citation_type: str = "unknown"
    confidence: float = 0.0
    extraction_method: str = "llm"  # "llm" or "regex"


class ParseCitationSignature(dspy.Signature):
    """Parse a citation text into structured components using LLM"""

    citation_text = dspy.InputField(desc="The raw citation text to parse")
    structured_citation = dspy.OutputField(
        desc="JSON object with parsed citation components: authors, first_author, title, year, journal, doi, arxiv_id, citation_type, confidence"
    )


class CitationParser:
    """Advanced citation parser using LLM for better component extraction"""

    def __init__(self):
        """Initialize the citation parser"""
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.parser_model_name = os.getenv("FACT_CHECK_MODEL", "openai/gpt-3.5-turbo")

        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        # Configure DSPy with OpenRouter
        self.lm = dspy.LM(
            model=self.parser_model_name,
            api_key=self.openrouter_api_key,
            api_base="https://openrouter.ai/api/v1",
            max_tokens=1024,
            temperature=0.1,  # Low temperature for consistent parsing
        )

        # Initialize DSPy parser
        with dspy.context(lm=self.lm):
            self.citation_parser = dspy.ChainOfThought(ParseCitationSignature)

        # Fallback regex patterns for quick extraction
        self._compile_regex_patterns()

    def _compile_regex_patterns(self):
        """Compile regex patterns for fallback parsing"""
        self.patterns = {
            "doi": re.compile(r"doi:\s*10\.\d+/[^\s,]+", re.IGNORECASE),
            "arxiv": re.compile(r"arXiv:\s*(\d+\.\d+)", re.IGNORECASE),
            "pmid": re.compile(r"pmid:\s*(\d+)", re.IGNORECASE),
            "year": re.compile(r"\b(19|20)\d{2}\b"),
            "authors_et_al": re.compile(
                r"([A-Z][a-zA-Z\-]+)(?:,\s*[A-Z]\.?)*\s+et al\.?", re.IGNORECASE
            ),
            "pages": re.compile(r"(\d+)\s*[-–]\s*(\d+|\w+)"),
            "volume_issue": re.compile(r"(\d+)\s*\((\d+)\)"),
        }

    def parse_citation(self, citation_text: str, use_llm: bool = True) -> StructuredCitation:
        """
        Parse a citation text into structured components

        Args:
            citation_text: Raw citation text to parse
            use_llm: Whether to use LLM parsing (fallback to regex if False)

        Returns:
            StructuredCitation object with parsed components
        """
        if use_llm:
            try:
                return self._parse_with_llm(citation_text)
            except Exception as e:
                print(f"LLM parsing failed for '{citation_text[:50]}...': {e}")
                print("Falling back to regex parsing")
                return self._parse_with_regex(citation_text)
        else:
            return self._parse_with_regex(citation_text)

    def _parse_with_llm(self, citation_text: str) -> StructuredCitation:
        """Parse citation using LLM"""


        try:
            with dspy.context(lm=self.lm):
                result = self.citation_parser(citation_text=citation_text)

            # Parse the JSON response
            try:
                parsed_data = json.loads(result.structured_citation)
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                json_match = re.search(r"\{.*\}", result.structured_citation, re.DOTALL)
                if json_match:
                    parsed_data = json.loads(json_match.group())
                else:
                    raise ValueError("No valid JSON found in LLM response") from None

            # Parse confidence score safely
            try:
                confidence = float(parsed_data.get("confidence", 0.8))
            except (ValueError, TypeError):
                confidence = 0.8

            # Convert to StructuredCitation
            structured_citation = StructuredCitation(
                original_text=citation_text,
                authors=parsed_data.get("authors", []),
                first_author=parsed_data.get("first_author", ""),
                title=parsed_data.get("title", ""),
                year=parsed_data.get("year", ""),
                journal=parsed_data.get("journal"),
                conference=parsed_data.get("conference"),
                book_title=parsed_data.get("book_title"),
                publisher=parsed_data.get("publisher"),
                doi=parsed_data.get("doi"),
                arxiv_id=parsed_data.get("arxiv_id"),
                pmid=parsed_data.get("pmid"),
                volume=parsed_data.get("volume"),
                issue=parsed_data.get("issue"),
                pages=parsed_data.get("pages"),
                citation_type=parsed_data.get("citation_type", "unknown"),
                confidence=confidence,
                extraction_method="llm",
            )

            # Validate and clean the parsed data
            return self._validate_and_clean(structured_citation)

        except Exception as e:
            print(f"LLM parsing error: {e}")
            raise

    def _parse_with_regex(self, citation_text: str) -> StructuredCitation:
        """Parse citation using regex patterns as fallback"""

        # Enhanced patterns for URL extraction
        arxiv_url_match = re.search(r"arxiv\.org/abs/(\d+\.\d+)", citation_text)
        doi_url_match = re.search(r"doi\.org/(10\.\d+/[^\s\)]+)", citation_text)

        # Extract basic components
        doi_match = self.patterns["doi"].search(citation_text)
        arxiv_match = self.patterns["arxiv"].search(citation_text)
        pmid_match = self.patterns["pmid"].search(citation_text)
        year_match = self.patterns["year"].search(citation_text)
        authors_match = self.patterns["authors_et_al"].search(citation_text)
        pages_match = self.patterns["pages"].search(citation_text)
        volume_issue_match = self.patterns["volume_issue"].search(citation_text)

        # Extract title from quoted text (common pattern in our test cases)
        title_match = re.search(r'"([^"]+)"', citation_text)
        title = title_match.group(1) if title_match else ""

        # If no quoted title, try to extract between year and journal/publisher
        if not title and year_match:
            year_pos = year_match.start()
            # Look for journal/publisher indicators after year
            journal_indicators = [r"\.", r"\s+[A-Z]", r",\s", r"\s+-\s+"]
            for pattern in journal_indicators:
                match = re.search(pattern, citation_text[year_pos + 4 :])
                if match:
                    title_end = year_pos + 4 + match.start()
                    title = citation_text[year_pos + 4 : title_end].strip(". ,")
                    break

        # Extract authors from common patterns
        first_author = ""
        authors = []
        if authors_match:
            first_author = authors_match.group(1)
            authors = [first_author]
        else:
            # Try to extract author from "by Author" pattern
            author_by_match = re.search(r"by\s+([A-Z][a-zA-Z\-]+)", citation_text)
            if author_by_match:
                first_author = author_by_match.group(1)
                authors = [first_author]

        # Determine citation type
        citation_type = "unknown"
        if arxiv_match or arxiv_url_match:
            citation_type = "preprint"
        elif doi_match or doi_url_match:
            if any(word in citation_text.lower() for word in ["journal", "proceedings"]):
                citation_type = "journal"
            else:
                citation_type = "article"
        elif any(word in citation_text.lower() for word in ["conference", "symposium"]):
            citation_type = "conference"
        elif any(
            word in citation_text.lower() for word in ["book", "press", "publishing", "textbook"]
        ):
            citation_type = "book"

        # Use URL matches if available, otherwise use pattern matches
        arxiv_id = None
        if arxiv_url_match:
            arxiv_id = f"arXiv:{arxiv_url_match.group(1)}"
        elif arxiv_match:
            arxiv_id = f"arXiv:{arxiv_match.group(1)}"

        doi = None
        if doi_url_match:
            doi = f"doi:{doi_url_match.group(1)}"
        elif doi_match:
            doi = doi_match.group()

        # Calculate confidence based on data quality
        confidence = 0.3  # Base confidence for regex
        if title:
            confidence += 0.2
        if first_author:
            confidence += 0.2
        if year_match:
            confidence += 0.1
        if arxiv_id or doi:
            confidence += 0.2  # Boost for having identifiers

        structured_citation = StructuredCitation(
            original_text=citation_text,
            authors=authors,
            first_author=first_author,
            title=title,
            year=year_match.group() if year_match else "",
            journal="",  # Would need more sophisticated extraction
            citation_type=citation_type,
            confidence=min(0.8, confidence),  # Cap at 0.8 for regex
            extraction_method="regex",
            doi=doi,
            arxiv_id=arxiv_id,
            pmid=pmid_match.group(1) if pmid_match else None,
            pages=f"{pages_match.group(1)}-{pages_match.group(2)}" if pages_match else None,
            volume=volume_issue_match.group(1) if volume_issue_match else None,
            issue=volume_issue_match.group(2) if volume_issue_match else None,
        )

        return self._validate_and_clean(structured_citation)

    def _validate_and_clean(self, citation: StructuredCitation) -> StructuredCitation:
        """Validate and clean parsed citation data"""

        # Clean up strings
        citation.title = citation.title.strip(". ") if citation.title else ""
        citation.first_author = citation.first_author.strip() if citation.first_author else ""
        citation.year = citation.year.strip() if citation.year else ""

        # Clean up authors list
        citation.authors = [author.strip() for author in citation.authors if author.strip()]

        # Validate year format
        if citation.year and not re.match(r"^(19|20)\d{2}$", citation.year):
            citation.year = ""

        # Validate DOI format
        if citation.doi and not citation.doi.lower().startswith("doi:"):
            citation.doi = f"doi:{citation.doi}"

        # Validate arXiv ID
        if citation.arxiv_id and not citation.arxiv_id.lower().startswith("arxiv:"):
            citation.arxiv_id = f"arXiv:{citation.arxiv_id}"

        # Adjust confidence based on data quality
        if citation.title and citation.first_author and citation.year:
            citation.confidence = min(1.0, citation.confidence + 0.2)
        elif not citation.title:
            citation.confidence = max(0.1, citation.confidence - 0.3)

        return citation

    def extract_citations_from_text(self, text: str) -> list[StructuredCitation]:
        """
        Extract and parse all citations from a larger text

        Args:
            text: Text containing citations

        Returns:
            List of StructuredCitation objects
        """
        # First use the existing NER extractor to find citation boundaries
        from .ner_extractor import AcademicNER

        ner = AcademicNER()
        raw_citations = ner.extract_citations(text)

        structured_citations = []
        for raw_citation in raw_citations:
            try:
                # Parse each found citation
                structured = self.parse_citation(raw_citation.text)
                # Preserve the position information from NER
                structured.original_text = raw_citation.text
                structured_citations.append(structured)
            except Exception as e:
                print(f"Failed to parse citation '{raw_citation.text}': {e}")
                # Create a minimal structured citation
                structured = StructuredCitation(
                    original_text=raw_citation.text,
                    authors=[],
                    first_author="",
                    title="",
                    year="",
                    confidence=0.3,
                    extraction_method="fallback",
                )
                structured_citations.append(structured)

        return structured_citations

    def generate_search_queries(self, citation: StructuredCitation) -> list[str]:
        """
        Generate effective search queries from a structured citation

        Args:
            citation: StructuredCitation object

        Returns:
            List of search query strings
        """
        queries = []

        # Strategy 1: Direct DOI/arXiv search
        if citation.doi:
            queries.append(citation.doi)
        if citation.arxiv_id:
            queries.append(citation.arxiv_id)

        # Strategy 2: First author + year + title snippet
        if citation.first_author and citation.year and citation.title:
            title_snippet = citation.title.split()[:5]  # First 5 words
            queries.append(f"{citation.first_author} {citation.year} {' '.join(title_snippet)}")

        # Strategy 3: Title search
        if citation.title:
            queries.append(f'"{citation.title}"')

        # Strategy 4: Author + year
        if citation.first_author and citation.year:
            queries.append(f"{citation.first_author} {citation.year}")

        # Strategy 5: Journal/conference + year + title keywords
        if citation.journal and citation.year:
            title_keywords = citation.title.split()[:3] if citation.title else []
            query = f"{citation.journal} {citation.year}"
            if title_keywords:
                query += f" {' '.join(title_keywords)}"
            queries.append(query)

        # Remove duplicates and empty queries
        queries = [q.strip() for q in queries if q.strip()]
        return list(dict.fromkeys(queries))[:5]  # Return unique queries, max 5

    def validate_setup(self) -> bool:
        """Validate that the citation parser is properly configured"""
        try:
            test_citation = "Vaswani et al. (2017). Attention is all you need. Advances in neural information processing systems, 30."
            parsed = self.parse_citation(test_citation)
            return parsed.title and parsed.first_author and parsed.year
        except Exception as e:
            print(f"Citation parser validation failed: {e}")
            return False


# Factory function for easy import
def create_citation_parser() -> CitationParser:
    """Create and return a configured CitationParser instance"""
    return CitationParser()
