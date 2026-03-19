"""
Unit tests for parse_title_from_analysis in session_manager.
"""

import pytest
from web.services.session_manager import parse_title_from_analysis


class TestParseTitleFromAnalysis:
    """Tests for the parse_title_from_analysis function."""

    def test_happy_path_all_fields_present(self):
        """All four header fields parsed correctly."""
        analysis = (
            "TITLE: Deep Learning for NLP\n"
            "AUTHORS: Smith, John; Doe, Jane\n"
            "JOURNAL: Nature\n"
            "YEAR: 2023\n"
            "- KEY FINDING: This paper is great.\n"
            "- METHODOLOGY: Used transformers.\n"
        )
        metadata, body = parse_title_from_analysis(analysis)

        assert metadata["title"] == "Deep Learning for NLP"
        assert metadata["authors"] == ["Smith, John", "Doe, Jane"]
        assert metadata["journal"] == "Nature"
        assert metadata["year"] == "2023"
        assert "KEY FINDING" in body
        assert "METHODOLOGY" in body

    def test_partial_fields_only_title(self):
        """Only TITLE present; others default to None/[]."""
        analysis = (
            "TITLE: Some Paper\n"
            "AUTHORS: Unknown\n"
            "JOURNAL: Unknown\n"
            "YEAR: Unknown\n"
            "- SUMMARY: Content here.\n"
        )
        metadata, body = parse_title_from_analysis(analysis)

        assert metadata["title"] == "Some Paper"
        assert metadata["authors"] == []
        assert metadata["journal"] is None
        assert metadata["year"] is None
        assert "SUMMARY" in body

    def test_no_headers_pure_body(self):
        """When analysis has no header fields, body is the full text."""
        analysis = "- FINDING: Something interesting.\n- METHOD: Used science.\n"
        metadata, body = parse_title_from_analysis(analysis)

        assert metadata["title"] is None
        assert metadata["authors"] == []
        assert metadata["journal"] is None
        assert metadata["year"] is None
        assert "FINDING" in body

    def test_headers_only_no_body(self):
        """When only header fields exist (no bullet points), body is empty."""
        analysis = (
            "TITLE: Headers Only Paper\n"
            "AUTHORS: Author One\n"
            "JOURNAL: Some Journal\n"
            "YEAR: 2021\n"
        )
        metadata, body = parse_title_from_analysis(analysis)

        assert metadata["title"] == "Headers Only Paper"
        assert metadata["authors"] == ["Author One"]
        assert metadata["journal"] == "Some Journal"
        assert metadata["year"] == "2021"
        assert body == ""

    def test_year_with_non_digit_characters_rejected(self):
        r"""Year strings that don't match ^\d{4}$ are rejected."""
        analysis = (
            "TITLE: A Paper\n"
            "AUTHORS: Unknown\n"
            "JOURNAL: Unknown\n"
            "YEAR: 2024 (estimated)\n"
            "- POINT: Some point.\n"
        )
        metadata, _ = parse_title_from_analysis(analysis)
        assert metadata["year"] is None

    def test_year_partial_digit_rejected(self):
        """Year with fewer than 4 digits is rejected."""
        analysis = (
            "TITLE: Old Paper\n"
            "AUTHORS: Unknown\n"
            "JOURNAL: Unknown\n"
            "YEAR: 99\n"
            "- NOTE: Old.\n"
        )
        metadata, _ = parse_title_from_analysis(analysis)
        assert metadata["year"] is None

    def test_authors_multiple_semicolons_and_whitespace(self):
        """Authors with multiple semicolons and extra whitespace are trimmed."""
        analysis = (
            "TITLE: Multi-Author Paper\n"
            "AUTHORS:  Smith, A. ;  Jones, B. ;  Lee, C.  \n"
            "JOURNAL: Unknown\n"
            "YEAR: 2020\n"
            "- KEY: Point.\n"
        )
        metadata, _ = parse_title_from_analysis(analysis)
        assert metadata["authors"] == ["Smith, A.", "Jones, B.", "Lee, C."]

    def test_blank_lines_between_headers_skipped(self):
        """Blank lines between header fields don't break parsing."""
        analysis = (
            "TITLE: Spaced Paper\n"
            "\n"
            "AUTHORS: Author X\n"
            "\n"
            "JOURNAL: A Journal\n"
            "YEAR: 2022\n"
            "- BODY: Content.\n"
        )
        metadata, body = parse_title_from_analysis(analysis)

        assert metadata["title"] == "Spaced Paper"
        assert metadata["authors"] == ["Author X"]
        assert metadata["journal"] == "A Journal"
        assert metadata["year"] == "2022"
        assert "BODY" in body

    def test_case_insensitive_field_matching(self):
        """Field prefixes are matched case-insensitively."""
        analysis = (
            "title: Case Test\n"
            "authors: One Author\n"
            "journal: Some Venue\n"
            "year: 2019\n"
            "- Point: here.\n"
        )
        metadata, _ = parse_title_from_analysis(analysis)
        assert metadata["title"] == "Case Test"
        assert metadata["authors"] == ["One Author"]
        assert metadata["journal"] == "Some Venue"
        assert metadata["year"] == "2019"

    def test_empty_string_returns_empty_metadata_and_body(self):
        """Empty analysis produces empty metadata and empty body."""
        metadata, body = parse_title_from_analysis("")
        assert metadata["title"] is None
        assert metadata["authors"] == []
        assert metadata["journal"] is None
        assert metadata["year"] is None
        assert body == ""
