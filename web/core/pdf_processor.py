"""
PDF processing utilities for Paper Companion.
Extract text, metadata, outlines, and figures from PDF files using PyMuPDF.
"""

import hashlib
import io
from pathlib import Path
from typing import Any, Optional

import fitz  # PyMuPDF


class PDFProcessor:
    """
    Process PDF files to extract content and metadata.

    Features:
    - Full text extraction
    - Metadata extraction (title, authors, etc.)
    - Outline/TOC extraction
    - PDF hashing for deduplication
    - Figure extraction (future enhancement)
    """

    @staticmethod
    async def extract_text(pdf_path: str) -> str:
        """
        Extract full text content from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text as single string

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: If PDF cannot be processed
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            text_parts = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                # Add page marker for reference
                text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

            doc.close()

            full_text = "\n\n".join(text_parts)
            return full_text.strip()

        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {e}") from e

    @staticmethod
    async def extract_text_by_page(pdf_path: str) -> list[dict[str, Any]]:
        """
        Extract text with page numbers preserved.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of dicts with 'page_number' and 'text' keys

        Example:
            [
                {"page_number": 1, "text": "First page content..."},
                {"page_number": 2, "text": "Second page content..."},
            ]
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            pages = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                pages.append({
                    "page_number": page_num + 1,
                    "text": text.strip()
                })

            doc.close()
            return pages

        except Exception as e:
            raise Exception(f"Failed to extract text by page: {e}") from e

    @staticmethod
    async def extract_metadata(pdf_path: str) -> dict[str, Any]:
        """
        Extract metadata from PDF document properties.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with metadata fields:
            - title: Document title
            - author: Author(s)
            - subject: Subject/description
            - keywords: Keywords
            - creator: Creating application
            - producer: PDF producer
            - creation_date: Creation date
            - modification_date: Last modified date
            - page_count: Number of pages
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)

            # Extract PDF metadata
            metadata = doc.metadata or {}

            # Build clean metadata dict
            result = {
                "title": metadata.get("title", "").strip() or None,
                "author": metadata.get("author", "").strip() or None,
                "subject": metadata.get("subject", "").strip() or None,
                "keywords": metadata.get("keywords", "").strip() or None,
                "creator": metadata.get("creator", "").strip() or None,
                "producer": metadata.get("producer", "").strip() or None,
                "creation_date": metadata.get("creationDate", "").strip() or None,
                "modification_date": metadata.get("modDate", "").strip() or None,
                "page_count": len(doc),
            }

            doc.close()
            return result

        except Exception as e:
            raise Exception(f"Failed to extract metadata: {e}") from e

    @staticmethod
    async def extract_outline(pdf_path: str) -> list[dict[str, Any]]:
        """
        Extract document outline/table of contents.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of outline items with:
            - level: Heading level (1, 2, 3, etc.)
            - title: Heading text
            - page: Page number

        Example:
            [
                {"level": 1, "title": "Introduction", "page": 1},
                {"level": 2, "title": "Background", "page": 2},
                {"level": 1, "title": "Methods", "page": 5},
            ]
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            toc = doc.get_toc()  # Returns list of [level, title, page]

            outline = []
            for item in toc:
                level, title, page = item
                outline.append({
                    "level": level,
                    "title": title.strip(),
                    "page": page
                })

            doc.close()
            return outline

        except Exception as e:
            raise Exception(f"Failed to extract outline: {e}") from e

    @staticmethod
    async def get_pdf_hash(pdf_path: str) -> str:
        """
        Generate SHA-256 hash of PDF file for deduplication.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Hex string of SHA-256 hash
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            sha256_hash = hashlib.sha256()

            with open(pdf_path, "rb") as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(chunk)

            return sha256_hash.hexdigest()

        except Exception as e:
            raise Exception(f"Failed to hash PDF: {e}") from e

    @staticmethod
    async def get_page_count(pdf_path: str) -> int:
        """
        Get number of pages in PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Number of pages
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count

        except Exception as e:
            raise Exception(f"Failed to get page count: {e}") from e

    @staticmethod
    async def extract_figures(pdf_path: str) -> list[dict[str, Any]]:
        """
        Extract figures/images from PDF (future enhancement).

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of figures with metadata:
            - page: Page number
            - bbox: Bounding box coordinates
            - image_data: Image bytes
            - caption: Extracted caption (if available)

        Note: This is a placeholder for future implementation.
        Full figure extraction with caption matching requires more
        sophisticated document analysis.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            figures = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    xref = img[0]

                    # Get image metadata
                    base_image = doc.extract_image(xref)

                    figures.append({
                        "page": page_num + 1,
                        "index": img_index,
                        "width": base_image.get("width"),
                        "height": base_image.get("height"),
                        "colorspace": base_image.get("colorspace"),
                        "ext": base_image.get("ext"),  # image format (png, jpeg, etc.)
                        # Note: Not including image_data by default to save memory
                        # Can be retrieved on-demand using xref
                        "xref": xref,
                    })

            doc.close()
            return figures

        except Exception as e:
            raise Exception(f"Failed to extract figures: {e}") from e

    @staticmethod
    async def process_pdf(pdf_path: str) -> dict[str, Any]:
        """
        Comprehensive PDF processing - extract all information.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary containing:
            - text: Full text content
            - metadata: PDF metadata
            - outline: Table of contents
            - hash: PDF file hash
            - page_count: Number of pages
        """
        return {
            "text": await PDFProcessor.extract_text(pdf_path),
            "metadata": await PDFProcessor.extract_metadata(pdf_path),
            "outline": await PDFProcessor.extract_outline(pdf_path),
            "hash": await PDFProcessor.get_pdf_hash(pdf_path),
            "page_count": await PDFProcessor.get_page_count(pdf_path),
        }


# Convenience functions for direct import
async def extract_text(pdf_path: str) -> str:
    """Extract full text from PDF."""
    return await PDFProcessor.extract_text(pdf_path)


async def extract_metadata(pdf_path: str) -> dict[str, Any]:
    """Extract metadata from PDF."""
    return await PDFProcessor.extract_metadata(pdf_path)


async def extract_outline(pdf_path: str) -> list[dict[str, Any]]:
    """Extract outline/TOC from PDF."""
    return await PDFProcessor.extract_outline(pdf_path)


async def get_pdf_hash(pdf_path: str) -> str:
    """Generate SHA-256 hash of PDF."""
    return await PDFProcessor.get_pdf_hash(pdf_path)


async def process_pdf(pdf_path: str) -> dict[str, Any]:
    """Process PDF and extract all information."""
    return await PDFProcessor.process_pdf(pdf_path)
