"""Unit tests for bookmark.read_bookmarks — read existing PDF outline."""
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from bookmark_pdf.bookmark import mount_bookmarks, read_bookmarks
from bookmark_pdf.parser import BookmarkNode, Parser, to_indent_dot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_pdf(path: Path, page_count: int) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    for i in range(1, page_count + 1):
        c.drawString(100, 700, f"Page {i}")
        c.showPage()
    c.save()


def pdf_with_outline(path: Path, nodes: list[BookmarkNode]) -> None:
    """Generate a 10-page PDF then mount the given nodes as outline."""
    make_pdf(path, 10)
    # mount_bookmarks with page_offset=-1: pdf_idx = node.page - 1 (0-based).
    # nodes.page is 1-based, so the round-trip preserves visible page numbers.
    mount_bookmarks(path, nodes, path, mode="replace", page_offset=-1)


def _titles(nodes: list[BookmarkNode]) -> list[str]:
    out: list[str] = []
    for n in nodes:
        out.append(n.title)
        out.extend(_titles(n.children))
    return out


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pdf_no_outline(tmp_path: Path) -> Path:
    p = tmp_path / "no_outline.pdf"
    make_pdf(p, 5)
    return p


@pytest.fixture
def pdf_with_flat(tmp_path: Path) -> Path:
    p = tmp_path / "flat.pdf"
    pdf_with_outline(
        p,
        [
            BookmarkNode("第一章", 1, 1),
            BookmarkNode("第二章", 3, 2),
            BookmarkNode("第三章", 5, 3),
        ],
    )
    return p


@pytest.fixture
def pdf_with_nested(tmp_path: Path) -> Path:
    p = tmp_path / "nested.pdf"
    pdf_with_outline(
        p,
        [
            BookmarkNode(
                title="第一章",
                page=1,
                line_no=1,
                children=[
                    BookmarkNode("1.1 引言", 2, 2),
                    BookmarkNode("1.2 背景", 3, 3),
                ],
            ),
            BookmarkNode("第二章", 5, 4),
        ],
    )
    return p


# ---------------------------------------------------------------------------
# 1. Basic read
# ---------------------------------------------------------------------------


class TestReadBasic:
    def test_read_no_outline_returns_empty(self, pdf_no_outline: Path):
        nodes = read_bookmarks(pdf_no_outline)
        assert nodes == []

    def test_read_flat_outline(self, pdf_with_flat: Path):
        nodes = read_bookmarks(pdf_with_flat)
        assert len(nodes) == 3
        assert _titles(nodes) == ["第一章", "第二章", "第三章"]

    def test_read_pages_are_one_based(self, pdf_with_flat: Path):
        nodes = read_bookmarks(pdf_with_flat)
        # Source pages are 1,3,5 → node.page must be 1,3,5 (1-based)
        assert [n.page for n in nodes] == [1, 3, 5]


# ---------------------------------------------------------------------------
# 2. Nested outline
# ---------------------------------------------------------------------------


class TestReadNested:
    def test_read_nested_keeps_children(self, pdf_with_nested: Path):
        nodes = read_bookmarks(pdf_with_nested)
        assert len(nodes) == 2
        assert nodes[0].title == "第一章"
        assert len(nodes[0].children) == 2
        assert [c.title for c in nodes[0].children] == ["1.1 引言", "1.2 背景"]

    def test_read_nested_pages(self, pdf_with_nested: Path):
        nodes = read_bookmarks(pdf_with_nested)
        assert nodes[0].children[0].page == 2
        assert nodes[0].children[1].page == 3
        assert nodes[1].page == 5

    def test_read_line_no_assigned(self, pdf_with_nested: Path):
        nodes = read_bookmarks(pdf_with_nested)
        # line_no should be unique and > 0
        all_line_nos = [n.line_no for n in nodes] + [
            c.line_no for n in nodes for c in n.children
        ]
        assert len(all_line_nos) == len(set(all_line_nos))
        assert all(ln > 0 for ln in all_line_nos)


# ---------------------------------------------------------------------------
# 3. Round-trip: read → to_indent_dot → parse → equivalent structure
# ---------------------------------------------------------------------------


class TestReadRoundTrip:
    def test_round_trip_flat(self, pdf_with_flat: Path):
        original_nodes = read_bookmarks(pdf_with_flat)
        text = to_indent_dot(original_nodes)
        reparsed = Parser(Parser.BUILTIN_RULES["indent-dot"]).parse(text)
        assert _titles(reparsed) == _titles(original_nodes)
        assert _pages(reparsed) == _pages(original_nodes)

    def test_round_trip_nested(self, pdf_with_nested: Path):
        original_nodes = read_bookmarks(pdf_with_nested)
        text = to_indent_dot(original_nodes)
        reparsed = Parser(Parser.BUILTIN_RULES["indent-dot"]).parse(text)

        assert len(reparsed) == len(original_nodes)
        assert _titles(reparsed) == _titles(original_nodes)
        assert _pages(reparsed) == _pages(original_nodes)
        # structure preserved
        assert len(reparsed[0].children) == len(original_nodes[0].children)


def _pages(nodes: list[BookmarkNode]) -> list[int | None]:
    out: list[int | None] = []
    for n in nodes:
        out.append(n.page)
        out.extend(_pages(n.children))
    return out


# ---------------------------------------------------------------------------
# 4. Edge cases
# ---------------------------------------------------------------------------


class TestReadEdgeCases:
    def test_read_single_page_pdf(self, tmp_path: Path):
        p = tmp_path / "one.pdf"
        make_pdf(p, 1)
        nodes = read_bookmarks(p)
        assert nodes == []

    def test_read_unicode_titles(self, tmp_path: Path):
        p = tmp_path / "uni.pdf"
        pdf_with_outline(
            p,
            [
                BookmarkNode("概述 🚀", 1, 1),
                BookmarkNode("背景", 2, 2),
            ],
        )
        nodes = read_bookmarks(p)
        assert [n.title for n in nodes] == ["概述 🚀", "背景"]

    def test_read_returns_independent_tree(self, pdf_with_nested: Path):
        """Mutating the returned list must not affect a second read."""
        first = read_bookmarks(pdf_with_nested)
        first.clear()
        second = read_bookmarks(pdf_with_nested)
        assert len(second) == 2


# ---------------------------------------------------------------------------
# 5. Mount read-back as a new outline (re-mount)
# ---------------------------------------------------------------------------


class TestReadAndRemount:
    def test_read_remount_preserves_structure(
        self, pdf_with_nested: Path, tmp_path: Path
    ):
        nodes = read_bookmarks(pdf_with_nested)
        out = tmp_path / "out.pdf"
        mount_bookmarks(pdf_with_nested, nodes, out, page_offset=-1)
        assert out.exists()
        # Re-read the output and compare
        reread = read_bookmarks(out)
        assert _titles(reread) == _titles(nodes)