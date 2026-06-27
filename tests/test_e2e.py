"""End-to-end integration test: parse fixtures → mount → verify outline."""
from pathlib import Path

import pytest
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from src.bookmark import mount_bookmarks
from src.parser import Parser


FIXTURES = Path(__file__).parent / "fixtures"


def make_pdf(path: Path, page_count: int) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    for i in range(1, page_count + 1):
        c.drawString(100, 700, f"Page {i}")
        c.showPage()
    c.save()


@pytest.fixture
def big_pdf(tmp_path: Path) -> Path:
    """80-page PDF to satisfy page references up to ~75."""
    p = tmp_path / "doc.pdf"
    make_pdf(p, 80)
    return p


def _flat_outline(items) -> list:
    """Flatten the outline tree into a list of (title, page_index_or_None)."""
    out = []
    for item in items:
        if isinstance(item, list):
            out.extend(_flat_outline(item))
        else:
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# TXT fixtures
# ---------------------------------------------------------------------------


def test_e2e_txt_flat(big_pdf: Path, tmp_path: Path):
    src = FIXTURES / "txt_flat.txt"
    nodes = Parser(Parser.BUILTIN_RULES["flat"]).parse_file(src)
    assert len(nodes) == 6

    out = tmp_path / "out.pdf"
    mount_bookmarks(big_pdf, nodes, out)
    assert out.exists()

    reader = PdfReader(str(out))
    titles = [item.title for item in _flat_outline(reader.outline)]
    assert titles[0] == "第一章 引言"
    assert "第六章 结论" in titles


def test_e2e_txt_indent(big_pdf: Path, tmp_path: Path):
    src = FIXTURES / "txt_indent.txt"
    nodes = Parser(Parser.BUILTIN_RULES["indent-dot"]).parse_file(src)
    assert len(nodes) == 3
    assert len(nodes[0].children) == 3  # 第一章: 1.1, 1.2, 1.3

    out = tmp_path / "out.pdf"
    mount_bookmarks(big_pdf, nodes, out)

    reader = PdfReader(str(out))
    flat = _flat_outline(reader.outline)
    titles = [item.title for item in flat]
    assert "1.2.1 相关工作" in titles
    assert "1.2.2 动机" in titles


def test_e2e_txt_chapter(big_pdf: Path, tmp_path: Path):
    src = FIXTURES / "txt_chapter.txt"
    nodes = Parser(Parser.BUILTIN_RULES["chapter"]).parse_file(src)
    assert len(nodes) == 6
    # First title should preserve "第一章" prefix
    assert nodes[0].title.startswith("第一章")


# ---------------------------------------------------------------------------
# MD fixtures
# ---------------------------------------------------------------------------


def test_e2e_md_header_suffix(big_pdf: Path, tmp_path: Path):
    src = FIXTURES / "md_header_suffix.md"
    nodes = Parser(Parser.BUILTIN_RULES["md-header-suffix"]).parse_file(src)
    # 5 top-level: 概述 / 相关工作 / 方法 / 实验 / 结论
    assert len(nodes) == 5
    top_titles = [n.title for n in nodes]
    assert "概述" in top_titles

    out = tmp_path / "out.pdf"
    mount_bookmarks(big_pdf, nodes, out)

    reader = PdfReader(str(out))
    flat = _flat_outline(reader.outline)
    titles = [item.title for item in flat]
    assert "3.2.1 算法描述" in titles


def test_e2e_md_header_comment(big_pdf: Path, tmp_path: Path):
    src = FIXTURES / "md_header_comment.md"
    nodes = Parser(Parser.BUILTIN_RULES["md-header-comment"]).parse_file(src)
    assert len(nodes) == 4  # 概述 / 方法 / 实验 / 结论

    out = tmp_path / "out.pdf"
    mount_bookmarks(big_pdf, nodes, out)

    reader = PdfReader(str(out))
    flat = _flat_outline(reader.outline)
    titles = [item.title for item in flat]
    assert "算法" in titles


def test_e2e_md_toc_link(big_pdf: Path, tmp_path: Path):
    src = FIXTURES / "md_toc_link.md"
    nodes = Parser(Parser.BUILTIN_RULES["md-toc-link"]).parse_file(src)
    assert len(nodes) == 4
    assert len(nodes[0].children) == 2  # 概述: 背景, 动机

    out = tmp_path / "out.pdf"
    mount_bookmarks(big_pdf, nodes, out)

    reader = PdfReader(str(out))
    flat = _flat_outline(reader.outline)
    titles = [item.title for item in flat]
    assert "算法" in titles
    assert "实现" in titles


# ---------------------------------------------------------------------------
# Examples (used by humans + README)
# ---------------------------------------------------------------------------


def test_examples_parseable(big_pdf: Path, tmp_path: Path):
    """The two example files in /examples should both be parseable and mountable."""
    for fname, rule_name in [
        ("sample_bookmarks.txt", "indent-dot"),
        ("sample_bookmarks.md", "md-header-comment"),
    ]:
        src = Path(__file__).parent.parent / "examples" / fname
        if not src.exists():
            pytest.skip(f"example not found: {src}")

        nodes = Parser(Parser.BUILTIN_RULES[rule_name]).parse_file(src)
        assert len(nodes) > 0

        out = tmp_path / f"out_{fname}.pdf"
        mount_bookmarks(big_pdf, nodes, out)
        assert out.exists()