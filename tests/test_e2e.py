"""End-to-end integration test: parse fixtures → mount → verify outline."""
from pathlib import Path

import pytest
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from bookmark_pdf.bookmark import mount_bookmarks, read_bookmarks
from bookmark_pdf.parser import BookmarkNode, Parser, to_indent_dot


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


# ---------------------------------------------------------------------------
# v1.2: text area → parse → mount → re-read
# ---------------------------------------------------------------------------


def test_e2e_paste_text_parse_mount(big_pdf: Path, tmp_path: Path):
    """Simulate user pasting indent-dot text → parse → mount → verify outline."""
    pasted = (
        "第一章 引言 ...... 1\n"
        "  1.1 背景 ...... 2\n"
        "  1.2 动机 ...... 3\n"
        "第二章 方法 ...... 5\n"
        "第三章 实验 ...... 8\n"
    )
    # Step 1: parse the pasted text (this is what the GUI does)
    nodes = Parser(Parser.BUILTIN_RULES["indent-dot"]).parse(pasted)
    assert len(nodes) == 3
    assert len(nodes[0].children) == 2

    # Step 2: serialize to indent-dot (this is what the GUI does on sync)
    text = to_indent_dot(nodes)
    assert "1.1 背景" in text

    # Step 3: re-parse the serialized text (round-trip)
    reparsed = Parser(Parser.BUILTIN_RULES["indent-dot"]).parse(text)
    assert len(reparsed) == len(nodes)

    # Step 4: mount to PDF
    out = tmp_path / "out.pdf"
    mount_bookmarks(big_pdf, nodes, out)

    # Step 5: verify outline by re-reading
    reader = PdfReader(str(out))
    flat = _flat_outline(reader.outline)
    titles = [item.title for item in flat]
    assert "1.1 背景" in titles
    assert "1.2 动机" in titles
    assert "第三章 实验" in titles


def test_e2e_read_pdf_bookmarks_remount(big_pdf: Path, tmp_path: Path):
    """Simulate user clicking '📥 从 PDF 读取书签' → mount → verify."""
    # Step 1: write some outline to a source PDF
    src_pdf = tmp_path / "src.pdf"
    make_pdf(src_pdf, 80)
    source_nodes = [
        BookmarkNode(
            title="概述", page=1, line_no=1,
            children=[
                BookmarkNode("背景", 2, 2),
                BookmarkNode("动机", 3, 3),
            ],
        ),
        BookmarkNode("方法", 5, 4),
        BookmarkNode("结论", 10, 5),
    ]
    mount_bookmarks(src_pdf, source_nodes, src_pdf, mode="replace", page_offset=-1)

    # Step 2: read back via read_bookmarks (this is what the GUI does)
    read_back = read_bookmarks(src_pdf)
    assert len(read_back) == 3
    assert read_back[0].title == "概述"
    assert len(read_back[0].children) == 2

    # Step 3: serialize to indent-dot (this is what the GUI puts in text area)
    text = to_indent_dot(read_back)
    assert "概述 ...... 1" in text
    assert "背景 ...... 2" in text

    # Step 4: re-mount to a different PDF (simulates user editing then mounting)
    out_pdf = tmp_path / "out.pdf"
    mount_bookmarks(big_pdf, read_back, out_pdf, page_offset=-1)

    # Step 5: verify final outline
    final = read_bookmarks(out_pdf)
    final_titles = [n.title for n in final]
    assert "概述" in final_titles
    assert "方法" in final_titles
    assert "结论" in final_titles