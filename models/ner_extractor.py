import spacy
import re
from typing import List, Dict, Any, NamedTuple
from dataclasses import dataclass


@dataclass
class Citation:
    """Represents an academic citation found in text"""
    text: str  # The full citation text
    start: int  # Character start position
    end: int  # Character end position
    citation_type: str  # Type of citation (journal, book, etc.)
    confidence: float  # Confidence score (0.0 to 1.0)
    authors: List[str] = None  # Extracted author names
    title: str = None  # Extracted title
    year: str = None  # Publication year
    journal: str = None  # Journal name
    doi: str = None  # DOI if found


class AcademicNER:
    """Named Entity Recognition for academic citations using spaCy"""

    def __init__(self):
        """Initialize the NER pipeline"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise OSError(
                "spaCy English model not found. "
                "Please install it with: python -m spacy download en_core_web_sm"
            )

        # Academic citation patterns
        self.citation_patterns = [
            # Author-year format: (Smith et al., 2023)
            r'\([^()]*(?:et al\.?|&|and)[^()]*, ?\d{4}[a-z]?\)',

            # Journal format: Smith, J. (2023). Title. Journal Name, 12(3), 45-67.
            r'[A-Z][a-zA-Z\-\']+(?:,\s*[A-Z]\.?)*\.?\s*\(\d{4}[a-z]?\)\.?\s*[^.]+\.\s*[^,.]+,?\s*\d+(?:\(\d+\))?,?\s*\d+[-–]\d+\.?',

            # Book format: Author, A. (Year). Book Title. Publisher.
            r'[A-Z][a-zA-Z\-\']+(?:,\s*[A-Z]\.?)*\.?\s*\(\d{4}[a-z]?\)\.?\s*[^.]+\.\s*[^.]+\.',

            # DOI pattern
            r'doi:\s*10\.\d+/[^\s]+',

            # arXiv pattern
            r'arXiv:\d+\.\d+',

            # ISBN pattern
            r'ISBN:?\s*(?:\d{1,5}[-\s]?\d{1,7}[-\s]?\d{1,6}[-\s]?[\dX]|\d{13})',

            # URL to academic sources
            r'https?://(?:www\.)?(?:doi\.org|arxiv\.org|pubmed\.ncbi\.nlm\.nih\.gov|scholar\.google\.com)[^\s]+',
        ]

        # Compile patterns
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.citation_patterns]

        # Academic keywords that boost confidence
        self.academic_keywords = {
            'journals': ['journal', 'proceedings', 'conference', 'symposium', 'review'],
            'publication_types': ['paper', 'article', 'study', 'research', 'publication'],
            'institutions': ['university', 'institute', 'laboratory', 'school', 'college'],
            'academic_terms': ['peer-reviewed', 'peer reviewed', 'published', 'citation', 'bibliography']
        }

    def extract_citations(self, text: str) -> List[Citation]:
        """
        Extract academic citations from text

        Args:
            text: Input text to analyze

        Returns:
            List of Citation objects
        """
        citations = []

        # Process with spaCy for entities
        doc = self.nlp(text)

        # Pattern-based extraction
        for i, pattern in enumerate(self.compiled_patterns):
            for match in pattern.finditer(text):
                citation_text = match.group().strip()
                start, end = match.span()

                # Calculate confidence based on pattern type and context
                confidence = self._calculate_confidence(citation_text, text, i)

                # Skip low-confidence matches
                if confidence < 0.3:
                    continue

                # Extract citation components
                components = self._extract_citation_components(citation_text)

                citation = Citation(
                    text=citation_text,
                    start=start,
                    end=end,
                    citation_type=self._classify_citation_type(citation_text),
                    confidence=confidence,
                    **components
                )

                citations.append(citation)

        # Remove overlapping citations (keep highest confidence)
        citations = self._remove_overlaps(citations)

        return sorted(citations, key=lambda c: c.start)

    def _calculate_confidence(self, citation_text: str, full_text: str, pattern_index: int) -> float:
        """Calculate confidence score for a citation match"""
        base_confidence = {
            0: 0.9,  # Author-year format
            1: 0.95, # Full journal format
            2: 0.85, # Book format
            3: 0.99, # DOI
            4: 0.99, # arXiv
            5: 0.8,  # ISBN
            6: 0.9,  # Academic URLs
        }.get(pattern_index, 0.5)

        # Boost confidence based on academic keywords in surrounding context
        context_window = 200
        start_pos = max(0, full_text.find(citation_text) - context_window)
        end_pos = min(len(full_text), full_text.find(citation_text) + len(citation_text) + context_window)
        context = full_text[start_pos:end_pos].lower()

        keyword_boost = 0.0
        for category, keywords in self.academic_keywords.items():
            for keyword in keywords:
                if keyword in context:
                    keyword_boost += 0.1

        # Citation format quality checks
        format_boost = 0.0
        if re.search(r'\d{4}', citation_text):  # Has year
            format_boost += 0.1
        if re.search(r'[A-Z][a-z]+', citation_text):  # Has proper names
            format_boost += 0.1
        if len(citation_text) > 20:  # Reasonable length
            format_boost += 0.1

        return min(1.0, base_confidence + keyword_boost + format_boost)

    def _classify_citation_type(self, citation_text: str) -> str:
        """Classify the type of citation"""
        text_lower = citation_text.lower()

        if 'doi:' in text_lower or 'doi.org' in text_lower:
            return 'doi'
        elif 'arxiv' in text_lower:
            return 'preprint'
        elif 'isbn' in text_lower:
            return 'book'
        elif any(word in text_lower for word in ['journal', 'proceedings', 'conference']):
            return 'journal'
        elif re.search(r'\([^()]*\d{4}[^()]*\)', citation_text):
            return 'author_year'
        else:
            return 'unknown'

    def _extract_citation_components(self, citation_text: str) -> Dict[str, Any]:
        """Extract structured components from citation text"""
        components = {
            'authors': [],
            'title': None,
            'year': None,
            'journal': None,
            'doi': None
        }

        # Extract year
        year_match = re.search(r'\b(19|20)\d{2}\b', citation_text)
        if year_match:
            components['year'] = year_match.group()

        # Extract DOI
        doi_match = re.search(r'10\.\d+/[^\s,]+', citation_text)
        if doi_match:
            components['doi'] = doi_match.group()

        # Basic author extraction (simplified)
        author_patterns = [
            r'([A-Z][a-z]+(?:,\s*[A-Z]\.?)*)',  # Last, F.
            r'([A-Z]\.\s*[A-Z][a-z]+)',  # F. Last
        ]

        for pattern in author_patterns:
            authors = re.findall(pattern, citation_text)
            if authors:
                components['authors'] = authors[:3]  # Limit to first 3 authors
                break

        return components

    def _remove_overlaps(self, citations: List[Citation]) -> List[Citation]:
        """Remove overlapping citations, keeping the highest confidence ones"""
        if not citations:
            return citations

        # Sort by confidence (descending)
        sorted_citations = sorted(citations, key=lambda c: c.confidence, reverse=True)
        filtered = []

        for citation in sorted_citations:
            # Check if this citation overlaps with any already selected
            overlaps = False
            for selected in filtered:
                if (citation.start < selected.end and citation.end > selected.start):
                    overlaps = True
                    break

            if not overlaps:
                filtered.append(citation)

        return filtered

    def validate_setup(self) -> bool:
        """Validate that the NER system is properly set up"""
        try:
            test_text = "Smith et al. (2023) published their findings in Nature."
            citations = self.extract_citations(test_text)
            return len(citations) > 0
        except Exception:
            return False


# Factory function for easy import
def create_ner_extractor() -> AcademicNER:
    """Create and return a configured AcademicNER instance"""
    return AcademicNER()