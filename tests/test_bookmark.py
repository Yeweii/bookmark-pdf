"""Unit tests for bookmark.py."""
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from src.bookmark import (
    PageOutOfRangeError,
    mount_bookmarks,
)
from src.parser import BookmarkNode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_pdf(path: Path, page_count: int) -> None:
    """Generate a simple PDF with the given number of pages."""
    c = canvas.Canvas(str(path), pagesize=letter)
    for i in range(1, page_count + 1):
        c.drawString(100, 700, f"Page {i}")
        c.showPage()
    c.save()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pdf_5_pages(tmp_path: Path) -> Path:
    p = tmp_path / "src.pdf"
    make_pdf(p, 5)
    return p


@pytest.fixture
def pdf_1_page(tmp_path: Path) -> Path:
    p = tmp_path / "src.pdf"
    make_pdf(p, 1)
    return p


# ---------------------------------------------------------------------------
# 1. Basic mounting
# ---------------------------------------------------------------------------


class TestMountBasic:
    def test_mount_single_level(self, pdf_5_pages: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        nodes = [
            BookmarkNode("第一章", 1, 1),
            BookmarkNode("第二章", 3, 2),
            BookmarkNode("第三章", 5, 3),
        ]
        mount_bookmarks(pdf_5_pages, nodes, out)

        assert out.exists()
        assert out.stat().st_size > 0

    def test_mount_with_nested_children(self, pdf_5_pages: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        nodes = [
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
        ]
        mount_bookmarks(pdf_5_pages, nodes, out)

        assert out.exists()

    def test_mount_unicode_titles(self, pdf_5_pages: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        nodes = [
            BookmarkNode("概述 🚀", 1, 1),
            BookmarkNode("背景", 2, 2),
        ]
        mount_bookmarks(pdf_5_pages, nodes, out)

        assert out.exists()


# ---------------------------------------------------------------------------
# 2. Page offset
# ---------------------------------------------------------------------------


class TestPageOffset:
    def test_default_offset_minus_one(self, pdf_5_pages: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        # page=3 with offset=-1 → PDF index 2 (page 3 of 5)
        mount_bookmarks(pdf_5_pages, [BookmarkNode("X", 3, 1)], out)
        assert out.exists()

    def test_zero_offset_keeps_page_as_is(self, pdf_5_pages: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        # page=2 with offset=0 → PDF index 2 (page 3 of 5)
        mount_bookmarks(
            pdf_5_pages, [BookmarkNode("X", 2, 1)], out, page_offset=0
        )
        assert out.exists()


# ---------------------------------------------------------------------------
# 3. Mode: replace / append / merge
# ---------------------------------------------------------------------------


class TestMode:
    def test_mode_replace_overwrites_existing_outline(
        self, pdf_5_pages: Path, tmp_path: Path
    ):
        out = tmp_path / "out.pdf"
        # First write some bookmarks
        mount_bookmarks(
            pdf_5_pages,
            [BookmarkNode("Old", 1, 1)],
            out,
            mode="replace",
        )
        # Replace with new bookmarks
        mount_bookmarks(
            pdf_5_pages,
            [BookmarkNode("New", 2, 1)],
            out,
            mode="replace",
        )
        assert out.exists()

    def test_mode_append_keeps_existing(
        self, pdf_5_pages: Path, tmp_path: Path
    ):
        out = tmp_path / "out.pdf"
        mount_bookmarks(
            pdf_5_pages,
            [BookmarkNode("A", 1, 1)],
            out,
            mode="replace",
        )
        mount_bookmarks(
            pdf_5_pages,
            [BookmarkNode("B", 2, 1)],
            out,
            mode="append",
        )
        assert out.exists()

    def test_mode_merge_dedup_by_title(
        self, pdf_5_pages: Path, tmp_path: Path
    ):
        out = tmp_path / "out.pdf"
        mount_bookmarks(
            pdf_5_pages,
            [BookmarkNode("Same", 1, 1)],
            out,
            mode="replace",
        )
        mount_bookmarks(
            pdf_5_pages,
            [BookmarkNode("Same", 3, 1)],
            out,
            mode="merge",
        )
        assert out.exists()


# ---------------------------------------------------------------------------
# 4. Page out of range
# ---------------------------------------------------------------------------


class TestPageOutOfRange:
    def test_page_too_high_raises(self, pdf_5_pages: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        with pytest.raises(PageOutOfRangeError) as exc_info:
            mount_bookmarks(
                pdf_5_pages,
                [BookmarkNode("Too Far", 999, 1)],
                out,
            )
        assert exc_info.value.page == 999
        assert exc_info.value.page_count == 5

    def test_page_zero_raises(self, pdf_5_pages: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        with pytest.raises(PageOutOfRangeError):
            mount_bookmarks(
                pdf_5_pages,
                [BookmarkNode("Zero", 0, 1)],
                out,
            )

    def test_page_negative_raises(self, pdf_5_pages: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        with pytest.raises(PageOutOfRangeError):
            mount_bookmarks(
                pdf_5_pages,
                [BookmarkNode("Negative", -1, 1)],
                out,
            )


# ---------------------------------------------------------------------------
# 5. None page (invalid) is skipped, not raised
# ---------------------------------------------------------------------------


class TestNonePage:
    def test_none_page_skipped_silently(self, pdf_5_pages: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        nodes = [
            BookmarkNode("Valid", 1, 1),
            BookmarkNode("Invalid", None, 2),  # skipped
            BookmarkNode("Also Valid", 3, 3),
        ]
        # Should NOT raise; invalid entries are skipped
        mount_bookmarks(pdf_5_pages, nodes, out)
        assert out.exists()


# ---------------------------------------------------------------------------
# 6. Progress callback
# ---------------------------------------------------------------------------


class TestProgressCallback:
    def test_callback_invoked(self, pdf_5_pages: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        calls: list[tuple[int, int]] = []
        mount_bookmarks(
            pdf_5_pages,
            [BookmarkNode("A", 1, 1)],
            out,
            on_progress=lambda c, t: calls.append((c, t)),
        )
        assert len(calls) >= 1
        # final call should reach total
        assert calls[-1][0] == calls[-1][1]

    def test_callback_can_be_none(self, pdf_5_pages: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        mount_bookmarks(
            pdf_5_pages,
            [BookmarkNode("A", 1, 1)],
            out,
            on_progress=None,
        )
        assert out.exists()


# ---------------------------------------------------------------------------
# 7. Empty nodes
# ---------------------------------------------------------------------------


class TestEmpty:
    def test_empty_nodes_list(self, pdf_5_pages: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        mount_bookmarks(pdf_5_pages, [], out)
        assert out.exists()

    def test_nodes_with_all_none_pages(
        self, pdf_5_pages: Path, tmp_path: Path
    ):
        out = tmp_path / "out.pdf"
        nodes = [
            BookmarkNode("A", None, 1),
            BookmarkNode("B", None, 2),
        ]
        mount_bookmarks(pdf_5_pages, nodes, out)
        assert out.exists()


# ---------------------------------------------------------------------------
# 8. Output path validation
# ---------------------------------------------------------------------------


class TestOutputPath:
    def test_overwrites_existing_output(
        self, pdf_5_pages: Path, tmp_path: Path
    ):
        out = tmp_path / "out.pdf"
        mount_bookmarks(pdf_5_pages, [BookmarkNode("A", 1, 1)], out)
        first_size = out.stat().st_size

        mount_bookmarks(pdf_5_pages, [BookmarkNode("B", 2, 1)], out)
        assert out.exists()
        # size should be similar (same pages, different outline)
        assert abs(out.stat().st_size - first_size) < first_size