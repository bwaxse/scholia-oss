"""
Metadata extraction service for Paper Companion.
Retrieves paper metadata from CrossRef, PubMed, and AI as fallback.
"""

import asyncio
import re
from typing import Optional, Dict, Any, List
import logging
import httpx

logger = logging.getLogger(__name__)


class MetadataService:
    """
    Extract and enrich paper metadata from multiple sources.

    Extraction priority:
    1. DOI from PDF metadata → CrossRef API
    2. DOI/PMID manual entry → CrossRef/PubMed API
    3. AI extraction from PDF (fallback)
    4. User manual entry (last resort)

    Features:
    - CrossRef API for DOI-based metadata
    - PubMed E-utilities for biomedical papers
    - AI fallback for papers without DOI
    - Structured metadata schema
    """

    def __init__(self, contact_email: str = "https://github.com/bwaxse/scholia-oss/issues"):
        """
        Initialize metadata service.

        Args:
            contact_email: Email for polite CrossRef API usage
        """
        self.contact_email = contact_email
        self.crossref_base = "https://api.crossref.org/works"
        self.pubmed_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def _extract_doi_from_text(self, text: str) -> Optional[str]:
        """
        Extract DOI from text using regex.

        Matches patterns like:
        - 10.1234/example
        - doi:10.1234/example
        - https://doi.org/10.1234/example

        Args:
            text: Text to search for DOI

        Returns:
            DOI string (normalized) or None
        """
        # Common DOI patterns
        patterns = [
            r'doi:\s*([10]\.\d{4,}(?:\.\d+)?/\S+)',  # doi:10.xxxx/...
            r'https?://(?:dx\.)?doi\.org/([10]\.\d{4,}(?:\.\d+)?/\S+)',  # https://doi.org/...
            r'\b([10]\.\d{4,}(?:\.\d+)?/\S+)\b',  # Bare DOI
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                doi = match.group(1).strip()
                # Clean up trailing punctuation
                doi = re.sub(r'[,;.\s]+$', '', doi)
                return doi

        return None

    def _extract_pmid_from_text(self, text: str) -> Optional[str]:
        """
        Extract PMID from text using regex.

        Matches patterns like:
        - PMID: 12345678
        - PMID:12345678
        - pubmed/12345678

        Args:
            text: Text to search for PMID

        Returns:
            PMID string or None
        """
        patterns = [
            r'PMID:\s*(\d{7,8})',
            r'pubmed[:/](\d{7,8})',
            r'www\.ncbi\.nlm\.nih\.gov/pubmed/(\d{7,8})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    async def get_metadata_from_crossref(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve metadata from CrossRef API using DOI.

        Args:
            doi: Digital Object Identifier

        Returns:
            Metadata dictionary or None if not found
        """
        try:
            url = f"{self.crossref_base}/{doi}"
            headers = {
                "User-Agent": f"ScholarlyApp/1.0 (mailto:{self.contact_email})"
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

            # Extract relevant fields from CrossRef response
            work = data.get("message", {})

            # Parse authors
            authors = []
            for author in work.get("author", []):
                given = author.get("given", "")
                family = author.get("family", "")
                if family:
                    authors.append(f"{family}, {given}".strip(", "))

            # Parse publication date
            pub_date = work.get("published", {}) or work.get("published-print", {})
            date_parts = pub_date.get("date-parts", [[]])[0]
            pub_year = str(date_parts[0]) if date_parts else None
            pub_date_str = "-".join(str(x) for x in date_parts) if date_parts else None

            # Build structured metadata
            metadata = {
                "title": work.get("title", [""])[0] if work.get("title") else None,
                "authors": authors,
                "doi": work.get("DOI"),
                "abstract": work.get("abstract"),
                "publication_date": pub_date_str,
                "year": pub_year,
                "journal": work.get("container-title", [""])[0] if work.get("container-title") else None,
                "journal_abbr": work.get("short-container-title", [""])[0] if work.get("short-container-title") else None,
                "volume": work.get("volume"),
                "issue": work.get("issue"),
                "pages": work.get("page"),
                "publisher": work.get("publisher"),
                "type": work.get("type"),
                "source": "crossref"
            }

            logger.info(f"Retrieved metadata from CrossRef for DOI: {doi}")
            return metadata

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"DOI not found in CrossRef: {doi}")
            else:
                logger.error(f"CrossRef API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve metadata from CrossRef: {e}")
            return None

    async def get_metadata_from_pubmed(self, identifier: str, is_pmid: bool = True) -> Optional[Dict[str, Any]]:
        """
        Retrieve metadata from PubMed E-utilities.

        Args:
            identifier: PMID or DOI
            is_pmid: True if identifier is PMID, False if DOI

        Returns:
            Metadata dictionary or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # If DOI, first convert to PMID using esearch
                if not is_pmid:
                    search_url = f"{self.pubmed_base}/esearch.fcgi"
                    params = {
                        "db": "pubmed",
                        "term": f"{identifier}[DOI]",
                        "retmode": "json"
                    }
                    response = await client.get(search_url, params=params)
                    response.raise_for_status()
                    search_data = response.json()

                    pmid_list = search_data.get("esearchresult", {}).get("idlist", [])
                    if not pmid_list:
                        logger.warning(f"DOI not found in PubMed: {identifier}")
                        return None
                    pmid = pmid_list[0]
                else:
                    pmid = identifier

                # Get metadata using esummary
                summary_url = f"{self.pubmed_base}/esummary.fcgi"
                params = {
                    "db": "pubmed",
                    "id": pmid,
                    "retmode": "json"
                }
                response = await client.get(summary_url, params=params)
                response.raise_for_status()
                data = response.json()

            # Extract relevant fields
            result = data.get("result", {}).get(pmid, {})

            # Parse authors
            authors = []
            for author in result.get("authors", []):
                authors.append(author.get("name", ""))

            # Parse publication date
            pub_date = result.get("pubdate", "")
            pub_year = result.get("pubdate", "").split()[0] if result.get("pubdate") else None

            # Build structured metadata
            metadata = {
                "title": result.get("title"),
                "authors": authors,
                "pmid": pmid,
                "doi": result.get("elocationid", "").replace("doi: ", "") if "doi:" in result.get("elocationid", "") else None,
                "abstract": None,  # Need efetch for abstract
                "publication_date": pub_date,
                "year": pub_year,
                "journal": result.get("fulljournalname"),
                "journal_abbr": result.get("source"),
                "volume": result.get("volume"),
                "issue": result.get("issue"),
                "pages": result.get("pages"),
                "type": "journal-article",
                "source": "pubmed"
            }

            logger.info(f"Retrieved metadata from PubMed for PMID: {pmid}")
            return metadata

        except Exception as e:
            logger.error(f"Failed to retrieve metadata from PubMed: {e}")
            return None

    async def extract_metadata_hybrid(
        self,
        pdf_metadata: Optional[Dict[str, Any]] = None,
        doi: Optional[str] = None,
        pmid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract metadata using hybrid approach.

        Priority:
        1. Provided DOI/PMID → CrossRef/PubMed
        2. DOI from PDF metadata → CrossRef
        3. Empty metadata (AI will fill in during initial_analysis)

        Args:
            pdf_metadata: Metadata extracted from PDF file
            doi: Manual DOI entry
            pmid: Manual PMID entry

        Returns:
            Metadata dictionary (may be partial)
        """
        # Try manual DOI first
        if doi:
            logger.info(f"Using provided DOI: {doi}")
            metadata = await self.get_metadata_from_crossref(doi)
            if metadata:
                return metadata

        # Try manual PMID
        if pmid:
            logger.info(f"Using provided PMID: {pmid}")
            metadata = await self.get_metadata_from_pubmed(pmid, is_pmid=True)
            if metadata:
                return metadata

        # Try extracting DOI from PDF metadata
        if pdf_metadata:
            # Check subject/keywords field for DOI
            subject = pdf_metadata.get("subject", "") or ""
            keywords = pdf_metadata.get("keywords", "") or ""
            combined_text = f"{subject} {keywords}"

            extracted_doi = self._extract_doi_from_text(combined_text)
            if extracted_doi:
                logger.info(f"Extracted DOI from PDF metadata: {extracted_doi}")
                metadata = await self.get_metadata_from_crossref(extracted_doi)
                if metadata:
                    return metadata

            # Check for PMID in PDF metadata
            extracted_pmid = self._extract_pmid_from_text(combined_text)
            if extracted_pmid:
                logger.info(f"Extracted PMID from PDF metadata: {extracted_pmid}")
                metadata = await self.get_metadata_from_pubmed(extracted_pmid, is_pmid=True)
                if metadata:
                    return metadata

        # Return basic metadata from PDF if available
        if pdf_metadata:
            return {
                "title": pdf_metadata.get("title"),
                "authors": [pdf_metadata.get("author")] if pdf_metadata.get("author") else [],
                "source": "pdf_metadata"
            }

        # Return empty metadata - will be filled by AI
        logger.info("No DOI/PMID found, metadata will be extracted by AI")
        return {
            "source": "ai_pending"
        }


# Global instance
_metadata_service: Optional[MetadataService] = None


def get_metadata_service() -> MetadataService:
    """Get global metadata service instance (singleton)."""
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = MetadataService()
    return _metadata_service
