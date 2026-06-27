"""Mount parsed bookmarks onto a PDF outline."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Literal

from pypdf import PdfReader, PdfWriter

from bookmark_pdf.parser import BookmarkNode, to_indent_dot


class PageOutOfRangeError(Exception):
    """Raised when a bookmark references a page outside the PDF."""

    def __init__(self, line_no: int, page: int, page_count: int) -> None:
        super().__init__(
            f"Line {line_no}: page {page} out of range "
            f"(PDF has {page_count} pages, indices 0..{page_count - 1})"
        )
        self.line_no = line_no
        self.page = page
        self.page_count = page_count


def mount_bookmarks(
    pdf_path: Path,
    nodes: list[BookmarkNode],
    output_path: Path,
    *,
    mode: Literal["replace", "append", "merge"] = "replace",
    page_offset: int = -1,
    on_progress: Callable[[int, int], None] | None = None,
) -> None:
    """Mount bookmark nodes onto a PDF.

    Args:
        pdf_path: Source PDF path.
        nodes: Bookmark tree from Parser.
        output_path: Destination PDF path (will be created/overwritten).
        mode: How to combine with existing outline.
            - replace: clear existing outline, write new
            - append:  keep existing, add new at top level
            - merge:   keep existing, add new (titles may overlap)
        page_offset: Added to each node.page before mapping to PDF index.
            Default -1 (TXT/MD page numbers are 1-based, PDF pages are 0-indexed).
        on_progress: Optional ``(current, total)`` callback.
    """
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    page_count = len(reader.pages)
    valid_count = _count_valid(nodes)
    total_steps = page_count + max(valid_count, 1)

    # 1. Copy pages
    for i, page in enumerate(reader.pages):
        writer.add_page(page)
        _progress(on_progress, i + 1, total_steps)

    # 2. Copy existing outline for append/merge modes
    if mode in ("append", "merge"):
        for src in _walk(reader.outline):
            _clone_item(reader, writer, src, parent=None)

    # 3. Add new bookmarks
    for node in nodes:
        _add_node(
            writer, node, parent=None,
            page_offset=page_offset, page_count=page_count,
        )

    # 4. Write
    with open(output_path, "wb") as f:
        writer.write(f)

    _progress(on_progress, total_steps, total_steps)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _progress(
    cb: Callable[[int, int], None] | None,
    current: int,
    total: int,
) -> None:
    if cb is not None:
        cb(current, total)


def _count_valid(nodes: list[BookmarkNode]) -> int:
    n = 0
    for node in nodes:
        if node.page is not None:
            n += 1
        n += _count_valid(node.children)
    return n


def _walk(items):
    """Recursively yield individual outline items (skipping nested list wrappers)."""
    for item in items:
        if isinstance(item, list):
            yield from _walk(item)
        else:
            yield item


def _clone_item(
    reader: PdfReader,
    writer: PdfWriter,
    src_item,
    parent,
) -> None:
    """Re-create a source outline item in the writer."""
    try:
        page_index = reader.get_destination_page_number(src_item.page)
    except Exception:
        return  # unresolvable destination; skip
    new_item = writer.add_outline_item(
        src_item.title, page_index, parent=parent
    )
    children = list(getattr(src_item, "children", None) or [])
    for child in children:
        if isinstance(child, list):
            for c in child:
                _clone_item(reader, writer, c, parent=new_item)
        else:
            _clone_item(reader, writer, child, parent=new_item)


def _add_node(
    writer: PdfWriter,
    node: BookmarkNode,
    parent,
    *,
    page_offset: int,
    page_count: int,
) -> None:
    """Add a node + its children. Skips nodes with page=None; raises on out-of-range."""
    if node.page is not None:
        pdf_idx = node.page + page_offset
        if pdf_idx < 0 or pdf_idx >= page_count:
            raise PageOutOfRangeError(node.line_no, node.page, page_count)
        item = writer.add_outline_item(node.title, pdf_idx, parent=parent)
        child_parent = item
    else:
        # Skip this node but keep its children attached to the same parent
        child_parent = parent

    for child in node.children:
        _add_node(
            writer, child, parent=child_parent,
            page_offset=page_offset, page_count=page_count,
        )


# ---------------------------------------------------------------------------
# TXT export (round-trippable with indent-dot parser template)
# ---------------------------------------------------------------------------


def save_bookmarks_txt(
    nodes: list[BookmarkNode],
    output_path: Path,
    *,
    indent_spaces: int = 2,
) -> Path:
    """Save a bookmark tree as indent-dot format TXT.

    The output can be re-parsed by ``Parser.BUILTIN_RULES["indent-dot"]``.

    Args:
        nodes: Top-level bookmark nodes.
        output_path: Destination .txt path (will be overwritten).
        indent_spaces: Number of spaces per nesting level.

    Returns:
        The same output_path for convenience.
    """
    output_path.write_text(
        to_indent_dot(nodes, indent_spaces=indent_spaces),
        encoding="utf-8",
    )
    return output_path


def default_txt_path_for(pdf_path: Path) -> Path:
    """Compute the default bookmark TXT path for a given PDF.

    Example: ``foo.pdf`` → ``foo_bookmarks.txt`` in the same directory.
    """
    return pdf_path.with_name(pdf_path.stem + "_bookmarks.txt")