"""Unit tests for save_bookmarks_txt + default_txt_path_for."""
from pathlib import Path

from bookmark_pdf.bookmark import default_txt_path_for, save_bookmarks_txt
from bookmark_pdf.parser import BookmarkNode, Parser


def test_default_txt_path_for_pdf(tmp_path: Path):
    pdf = tmp_path / "doc.pdf"
    txt = default_txt_path_for(pdf)
    assert txt == tmp_path / "doc_bookmarks.txt"


def test_default_txt_path_preserves_directory(tmp_path: Path):
    pdf = tmp_path / "sub" / "book.pdf"
    pdf.parent.mkdir()
    txt = default_txt_path_for(pdf)
    assert txt.parent == tmp_path / "sub"
    assert txt.name == "book_bookmarks.txt"


def test_save_bookmarks_txt_basic(tmp_path: Path):
    nodes = [
        BookmarkNode(
            title="第一章",
            page=1,
            line_no=1,
            children=[BookmarkNode("1.1", 2, 2)],
        ),
    ]
    out = tmp_path / "out.txt"
    result = save_bookmarks_txt(nodes, out)

    assert result == out
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert content == "第一章 ...... 1\n  1.1 ...... 2"


def test_save_overwrites_existing(tmp_path: Path):
    out = tmp_path / "out.txt"
    out.write_text("OLD CONTENT", encoding="utf-8")
    save_bookmarks_txt([BookmarkNode("New", 5, 1)], out)
    assert out.read_text(encoding="utf-8") == "New ...... 5"


def test_save_round_trip(tmp_path: Path):
    """Saved TXT should be parseable by indent-dot rule, producing equivalent tree."""
    nodes = [
        BookmarkNode(
            title="A", page=1, line_no=1,
            children=[BookmarkNode("B", 2, 2)],
        ),
    ]
    out = tmp_path / "rt.txt"
    save_bookmarks_txt(nodes, out)

    parsed = Parser(Parser.BUILTIN_RULES["indent-dot"]).parse_file(out)
    assert len(parsed) == 1
    assert parsed[0].title == "A"
    assert parsed[0].page == 1
    assert len(parsed[0].children) == 1
    assert parsed[0].children[0].title == "B"
    assert parsed[0].children[0].page == 2