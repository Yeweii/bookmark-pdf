"""Unit tests for filename sanitization + default filename suggestion (v1.3)."""
from __future__ import annotations

import pytest

from bookmark_pdf.app import BookmarkApp
from bookmark_pdf.fetcher import BookMeta


# ---------------------------------------------------------------------------
# _sanitize_filename
# ---------------------------------------------------------------------------


def test_sanitize_filename_removes_illegal_chars():
    """All OS-illegal characters should be replaced by spaces."""
    raw = 'a/b\\c:d*e?f"g<h>i|j'
    out = BookmarkApp._sanitize_filename(raw)
    # The 9 illegal chars are replaced with single spaces
    assert "/" not in out
    assert "\\" not in out
    assert ":" not in out
    assert "*" not in out
    assert "?" not in out
    assert '"' not in out
    assert "<" not in out
    assert ">" not in out
    assert "|" not in out
    assert out == "a b c d e f g h i j"


def test_sanitize_filename_collapses_whitespace():
    raw = "   多   余   空  格  "
    out = BookmarkApp._sanitize_filename(raw)
    assert out == "多 余 空 格"


def test_sanitize_filename_truncates_at_max_len():
    raw = "a" * 200
    out = BookmarkApp._sanitize_filename(raw, max_len=10)
    assert len(out) == 10
    assert out == "a" * 10


def test_sanitize_filename_strips_control_chars():
    raw = "title\nwith\rcontrol\tchars"
    out = BookmarkApp._sanitize_filename(raw)
    # \n, \r, \t are in the illegal set
    assert "\n" not in out
    assert "\r" not in out
    assert "\t" not in out
    assert out == "title with control chars"


def test_sanitize_filename_empty_falls_back_to_bookmarks():
    """After cleaning, an empty string must fall back to a safe default."""
    # All illegal chars + only whitespace
    assert BookmarkApp._sanitize_filename("") == "bookmarks"
    assert BookmarkApp._sanitize_filename("///") == "bookmarks"
    assert BookmarkApp._sanitize_filename("   ") == "bookmarks"


def test_sanitize_filename_preserves_unicode():
    raw = "深度学习：神经网络"
    out = BookmarkApp._sanitize_filename(raw)
    assert out == "深度学习：神经网络"  # ： (fullwidth colon) is legal


# ---------------------------------------------------------------------------
# _suggest_default_filename
# ---------------------------------------------------------------------------


def _make_app_without_init():
    """Bypass tkinter __init__: create an uninitialized instance.

    We need to set attributes via __dict__ to avoid tkinter's __setattr__
    routing everything through self.tk (which doesn't exist without __init__).
    """
    return BookmarkApp.__new__(BookmarkApp)


def _meta(title: str = "", ssid: str = "12345") -> BookMeta:
    return BookMeta(
        ssid=ssid, dxid="", isbn="", title=title, author="",
        publish="", publish_time="", total_pages=300, cover_url=None,
    )


class _FakeStringVar:
    """Minimal stand-in for tk.StringVar that supports .get()."""
    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value


def test_suggest_default_filename_uses_book_meta_title():
    app = _make_app_without_init()
    app.__dict__["_book_meta"] = _meta(title="深度学习")
    assert app._suggest_default_filename() == "深度学习_bookmarks.txt"


def test_suggest_default_filename_falls_back_to_ssid_when_title_empty():
    app = _make_app_without_init()
    app.__dict__["_book_meta"] = _meta(title="", ssid="13284383")
    assert app._suggest_default_filename() == "13284383_bookmarks.txt"


def test_suggest_default_filename_sanitizes_title():
    app = _make_app_without_init()
    app.__dict__["_book_meta"] = _meta(title='a/b\\c')
    out = app._suggest_default_filename()
    # Illegal chars replaced by spaces, but suffix preserved
    assert out == "a b c_bookmarks.txt"
    # No illegal chars in the final name
    for c in '/\\:*?"<>|':
        assert c not in out


def test_suggest_default_filename_uses_source_path_stem():
    """When no book meta, fall back to the source file's stem."""
    app = _make_app_without_init()
    app.__dict__["_book_meta"] = None
    app.__dict__["_source_path"] = _FakeStringVar("/tmp/my_bookmarks.txt")
    assert app._suggest_default_filename() == "my_bookmarks.txt"


def test_suggest_default_filename_no_meta_no_source_uses_bookmarks():
    app = _make_app_without_init()
    app.__dict__["_book_meta"] = None
    app.__dict__["_source_path"] = _FakeStringVar("")
    assert app._suggest_default_filename() == "bookmarks.txt"


def test_suggest_default_filename_source_with_md_extension():
    """Source can be .md; the stem should still be used."""
    app = _make_app_without_init()
    app.__dict__["_book_meta"] = None
    app.__dict__["_source_path"] = _FakeStringVar("/x/y/index.md")
    assert app._suggest_default_filename() == "index_bookmarks.txt"
