"""Bookmark node transforms — pure functions for batch editing.

Each function takes a list of BookmarkNode and returns a new list, leaving
the input untouched. Page=None entries are preserved by all transforms
that operate on page numbers (None stays None unless explicitly changed).
"""
from __future__ import annotations

import re
from typing import Callable

from bookmark_pdf.parser import BookmarkNode


Transform = Callable[[list[BookmarkNode]], list[BookmarkNode]]


# ---------------------------------------------------------------------------
# Page operations
# ---------------------------------------------------------------------------


def shift_pages(nodes: list[BookmarkNode], offset: int) -> list[BookmarkNode]:
    """Shift all page numbers by ``offset``. None pages stay None."""
    def walk(n: BookmarkNode) -> BookmarkNode:
        new_page = (n.page + offset) if n.page is not None else None
        return BookmarkNode(
            title=n.title, page=new_page, line_no=n.line_no,
            children=[walk(c) for c in n.children],
        )
    return [walk(n) for n in nodes]


def normalize_pages(nodes: list[BookmarkNode], start: int = 1) -> list[BookmarkNode]:
    """Reassign pages 1..N in DFS order starting from ``start``."""
    counter = [start - 1]

    def walk(n: BookmarkNode) -> BookmarkNode:
        counter[0] += 1
        return BookmarkNode(
            title=n.title, page=counter[0], line_no=n.line_no,
            children=[walk(c) for c in n.children],
        )
    return [walk(n) for n in nodes]


def cap_pages(nodes: list[BookmarkNode], max_page: int) -> list[BookmarkNode]:
    """Set page=None for entries with page > max_page. None stays None."""
    def walk(n: BookmarkNode) -> BookmarkNode:
        if n.page is not None and n.page > max_page:
            new_page: int | None = None
        else:
            new_page = n.page
        return BookmarkNode(
            title=n.title, page=new_page, line_no=n.line_no,
            children=[walk(c) for c in n.children],
        )
    return [walk(n) for n in nodes]


# ---------------------------------------------------------------------------
# Tree operations
# ---------------------------------------------------------------------------


def sort_by_page(
    nodes: list[BookmarkNode],
    descending: bool = False,
) -> list[BookmarkNode]:
    """Sort top-level entries by page; None pages always go last.

    Recursively sorts children. Stable sort preserves input order for equal keys.
    """
    def key(n: BookmarkNode) -> tuple[int, int]:
        # (is_none, page_or_zero) — None sorts last in ascending order
        if n.page is None:
            return (1, 0)
        return (0, -n.page if descending else n.page)

    return [
        BookmarkNode(
            title=n.title, page=n.page, line_no=n.line_no,
            children=sort_by_page(n.children, descending),
        )
        for n in sorted(nodes, key=key)
    ]


def flatten(nodes: list[BookmarkNode]) -> list[BookmarkNode]:
    """Remove all nesting; move children to top level in DFS order."""
    flat: list[BookmarkNode] = []

    def walk(ns: list[BookmarkNode]) -> None:
        for n in ns:
            flat.append(BookmarkNode(
                title=n.title, page=n.page, line_no=n.line_no,
                children=[],
            ))
            walk(n.children)

    walk(nodes)
    return flat


# ---------------------------------------------------------------------------
# Cleanup operations
# ---------------------------------------------------------------------------


def remove_duplicates(nodes: list[BookmarkNode]) -> list[BookmarkNode]:
    """Remove entries with duplicate (title, page); keep first occurrence."""
    seen: set[tuple[str, int | None]] = set()
    result: list[BookmarkNode] = []
    for n in nodes:
        key = (n.title, n.page)
        if key in seen:
            continue
        seen.add(key)
        result.append(BookmarkNode(
            title=n.title, page=n.page, line_no=n.line_no,
            children=remove_duplicates(n.children),
        ))
    return result


def remove_invalid_pages(nodes: list[BookmarkNode]) -> list[BookmarkNode]:
    """Remove entries whose page is None (recursively)."""
    result: list[BookmarkNode] = []
    for n in nodes:
        if n.page is None:
            continue
        result.append(BookmarkNode(
            title=n.title, page=n.page, line_no=n.line_no,
            children=remove_invalid_pages(n.children),
        ))
    return result


# ---------------------------------------------------------------------------
# Text operations
# ---------------------------------------------------------------------------


def trim_titles(nodes: list[BookmarkNode]) -> list[BookmarkNode]:
    """Strip leading/trailing whitespace (incl. unicode) from titles."""
    def walk(n: BookmarkNode) -> BookmarkNode:
        return BookmarkNode(
            title=n.title.strip(), page=n.page, line_no=n.line_no,
            children=[walk(c) for c in n.children],
        )
    return [walk(n) for n in nodes]


# ---------------------------------------------------------------------------
# (P2 — not in v1.4 first cut; stubs for reference)
# ---------------------------------------------------------------------------


def prefix_titles(nodes: list[BookmarkNode], prefix: str) -> list[BookmarkNode]:
    """Prepend ``prefix`` to every title."""
    def walk(n: BookmarkNode) -> BookmarkNode:
        return BookmarkNode(
            title=prefix + n.title, page=n.page, line_no=n.line_no,
            children=[walk(c) for c in n.children],
        )
    return [walk(n) for n in nodes]


def remove_titles_matching(
    nodes: list[BookmarkNode],
    pattern: str,
) -> list[BookmarkNode]:
    """Remove entries whose title matches ``pattern`` (regex)."""
    regex = re.compile(pattern)
    result: list[BookmarkNode] = []
    for n in nodes:
        if regex.search(n.title):
            continue
        result.append(BookmarkNode(
            title=n.title, page=n.page, line_no=n.line_no,
            children=remove_titles_matching(n.children, pattern),
        ))
    return result


def fix_negative_pages(nodes: list[BookmarkNode]) -> list[BookmarkNode]:
    """Set page=None for entries with page < 1. None stays None."""
    def walk(n: BookmarkNode) -> BookmarkNode:
        if n.page is not None and n.page < 1:
            new_page: int | None = None
        else:
            new_page = n.page
        return BookmarkNode(
            title=n.title, page=new_page, line_no=n.line_no,
            children=[walk(c) for c in n.children],
        )
    return [walk(n) for n in nodes]