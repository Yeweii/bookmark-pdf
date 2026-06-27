"""Unit tests for bookmark_pdf.transforms — batch editing operations."""
from pathlib import Path

from bookmark_pdf.parser import BookmarkNode, Parser, to_indent_dot
from bookmark_pdf.transforms import (
    cap_pages,
    flatten,
    normalize_pages,
    rebase_first_page,
    remove_duplicates,
    remove_invalid_pages,
    shift_pages,
    sort_by_page,
    trim_titles,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _titles(nodes: list[BookmarkNode]) -> list[str]:
    out: list[str] = []
    for n in nodes:
        out.append(n.title)
        out.extend(_titles(n.children))
    return out


def _pages(nodes: list[BookmarkNode]) -> list[int | None]:
    out: list[int | None] = []
    for n in nodes:
        out.append(n.page)
        out.extend(_pages(n.children))
    return out


def _parse(text: str) -> list[BookmarkNode]:
    return Parser(Parser.BUILTIN_RULES["indent-dot"]).parse(text)


def _roundtrip(transform, original_nodes: list[BookmarkNode]) -> None:
    """Apply ``transform``, serialize+reparse, verify titles unchanged."""
    text = to_indent_dot(original_nodes)
    reparsed = _parse(text)
    final = transform(reparsed)
    out_text = to_indent_dot(final)
    final_reparsed = _parse(out_text)
    assert _titles(final_reparsed) == _titles(final)


def _make_tree() -> list[BookmarkNode]:
    """Sample tree:
        A(1) -> A1(2) -> A1a(3)
        B(5)
        C(None)
    """
    return [
        BookmarkNode(
            title="A", page=1, line_no=1,
            children=[
                BookmarkNode(
                    title="A1", page=2, line_no=2,
                    children=[BookmarkNode("A1a", 3, 3)],
                ),
            ],
        ),
        BookmarkNode("B", 5, 4),
        BookmarkNode("C", None, 5),
    ]


# ---------------------------------------------------------------------------
# 1. shift_pages
# ---------------------------------------------------------------------------


class TestShiftPages:
    def test_shift_positive(self):
        nodes = [BookmarkNode("A", 1, 1), BookmarkNode("B", 3, 2)]
        result = shift_pages(nodes, 5)
        assert [n.page for n in result] == [6, 8]

    def test_shift_negative(self):
        nodes = [BookmarkNode("A", 10, 1), BookmarkNode("B", 20, 2)]
        result = shift_pages(nodes, -3)
        assert [n.page for n in result] == [7, 17]

    def test_shift_preserves_none(self):
        nodes = [BookmarkNode("A", None, 1), BookmarkNode("B", 5, 2)]
        result = shift_pages(nodes, 10)
        assert [n.page for n in result] == [None, 15]

    def test_shift_zero_is_noop(self):
        nodes = [BookmarkNode("A", 5, 1)]
        result = shift_pages(nodes, 0)
        assert result[0].page == 5

    def test_shift_nested(self):
        nodes = _make_tree()
        result = shift_pages(nodes, 10)
        assert _pages(result) == [11, 12, 13, 15, None]

    def test_shift_does_not_mutate_input(self):
        nodes = [BookmarkNode("A", 1, 1)]
        shift_pages(nodes, 5)
        assert nodes[0].page == 1


# ---------------------------------------------------------------------------
# 2. normalize_pages
# ---------------------------------------------------------------------------


class TestNormalizePages:
    def test_default_start_one(self):
        nodes = [BookmarkNode("A", 100, 1), BookmarkNode("B", 200, 2)]
        result = normalize_pages(nodes)
        assert [n.page for n in result] == [1, 2]

    def test_custom_start(self):
        nodes = [BookmarkNode("A", 100, 1), BookmarkNode("B", 200, 2)]
        result = normalize_pages(nodes, start=10)
        assert [n.page for n in result] == [10, 11]

    def test_normalize_dfs_order(self):
        nodes = _make_tree()
        result = normalize_pages(nodes)
        assert _pages(result) == [1, 2, 3, 4, 5]


# ---------------------------------------------------------------------------
# 3. cap_pages
# ---------------------------------------------------------------------------


class TestCapPages:
    def test_cap_clears_exceeding(self):
        nodes = [BookmarkNode("A", 5, 1), BookmarkNode("B", 100, 2)]
        result = cap_pages(nodes, 10)
        assert [n.page for n in result] == [5, None]

    def test_cap_keeps_at_boundary(self):
        nodes = [BookmarkNode("A", 10, 1)]
        result = cap_pages(nodes, 10)
        assert result[0].page == 10

    def test_cap_preserves_none(self):
        nodes = [BookmarkNode("A", None, 1), BookmarkNode("B", 100, 2)]
        result = cap_pages(nodes, 10)
        assert [n.page for n in result] == [None, None]

    def test_cap_nested(self):
        nodes = _make_tree()
        result = cap_pages(nodes, 2)
        # Original pages: 1, 2, 3, 5, None
        # After cap at 2: 1, 2, None, None, None
        assert _pages(result) == [1, 2, None, None, None]


# ---------------------------------------------------------------------------
# 4. sort_by_page
# ---------------------------------------------------------------------------


class TestSortByPage:
    def test_sort_ascending(self):
        nodes = [
            BookmarkNode("B", 5, 1),
            BookmarkNode("A", 1, 2),
            BookmarkNode("C", 3, 3),
        ]
        result = sort_by_page(nodes)
        assert [n.title for n in result] == ["A", "C", "B"]

    def test_sort_descending(self):
        nodes = [
            BookmarkNode("B", 5, 1),
            BookmarkNode("A", 1, 2),
            BookmarkNode("C", 3, 3),
        ]
        result = sort_by_page(nodes, descending=True)
        assert [n.title for n in result] == ["B", "C", "A"]

    def test_sort_none_goes_last(self):
        nodes = [
            BookmarkNode("B", None, 1),
            BookmarkNode("A", 1, 2),
            BookmarkNode("C", 3, 3),
        ]
        result_asc = sort_by_page(nodes)
        assert [n.title for n in result_asc] == ["A", "C", "B"]
        result_desc = sort_by_page(nodes, descending=True)
        assert [n.title for n in result_desc] == ["C", "A", "B"]

    def test_sort_recurses_into_children(self):
        nodes = [
            BookmarkNode(
                title="P", page=10, line_no=1,
                children=[
                    BookmarkNode("z", 12, 2),
                    BookmarkNode("a", 11, 3),
                ],
            ),
        ]
        result = sort_by_page(nodes)
        assert [c.title for c in result[0].children] == ["a", "z"]


# ---------------------------------------------------------------------------
# 5. remove_duplicates
# ---------------------------------------------------------------------------


class TestRemoveDuplicates:
    def test_remove_exact_duplicates(self):
        nodes = [
            BookmarkNode("A", 1, 1),
            BookmarkNode("A", 1, 2),  # dup
            BookmarkNode("B", 2, 3),
        ]
        result = remove_duplicates(nodes)
        assert [n.title for n in result] == ["A", "B"]

    def test_different_page_not_duplicate(self):
        nodes = [
            BookmarkNode("A", 1, 1),
            BookmarkNode("A", 2, 2),  # different page
        ]
        result = remove_duplicates(nodes)
        assert len(result) == 2

    def test_none_page_dedup(self):
        nodes = [
            BookmarkNode("A", None, 1),
            BookmarkNode("A", None, 2),
        ]
        result = remove_duplicates(nodes)
        assert len(result) == 1

    def test_remove_duplicates_nested(self):
        nodes = [
            BookmarkNode(
                title="P", page=1, line_no=1,
                children=[
                    BookmarkNode("A", 2, 2),
                    BookmarkNode("A", 2, 3),  # dup inside
                ],
            ),
        ]
        result = remove_duplicates(nodes)
        assert len(result[0].children) == 1


# ---------------------------------------------------------------------------
# 6. remove_invalid_pages
# ---------------------------------------------------------------------------


class TestRemoveInvalidPages:
    def test_remove_none_pages(self):
        nodes = [
            BookmarkNode("A", 1, 1),
            BookmarkNode("B", None, 2),
            BookmarkNode("C", 3, 3),
        ]
        result = remove_invalid_pages(nodes)
        assert [n.title for n in result] == ["A", "C"]

    def test_remove_recursively(self):
        nodes = [
            BookmarkNode(
                title="P", page=1, line_no=1,
                children=[
                    BookmarkNode("A", 2, 2),
                    BookmarkNode("B", None, 3),
                ],
            ),
            BookmarkNode("Q", None, 4),
        ]
        result = remove_invalid_pages(nodes)
        assert len(result) == 1
        assert result[0].title == "P"
        assert [c.title for c in result[0].children] == ["A"]


# ---------------------------------------------------------------------------
# 7. trim_titles
# ---------------------------------------------------------------------------


class TestTrimTitles:
    def test_trim_basic(self):
        nodes = [
            BookmarkNode("  A  ", 1, 1),
            BookmarkNode("B\t", 2, 2),
        ]
        result = trim_titles(nodes)
        assert [n.title for n in result] == ["A", "B"]

    def test_trim_nested(self):
        nodes = [
            BookmarkNode(
                title="  P  ", page=1, line_no=1,
                children=[BookmarkNode(" \t child \n ", 2, 2)],
            ),
        ]
        result = trim_titles(nodes)
        assert result[0].title == "P"
        assert result[0].children[0].title == "child"

    def test_trim_unicode_whitespace(self):
        nodes = [BookmarkNode("\u3000标题\u3000", 1, 1)]
        result = trim_titles(nodes)
        assert result[0].title == "标题"


# ---------------------------------------------------------------------------
# 8. flatten
# ---------------------------------------------------------------------------


class TestFlatten:
    def test_flatten_deep_tree(self):
        nodes = _make_tree()  # has 3 levels
        result = flatten(nodes)
        # All entries at top level, no children
        for n in result:
            assert n.children == []
        assert len(result) == 5  # A, A1, A1a, B, C

    def test_flatten_already_flat(self):
        nodes = [
            BookmarkNode("A", 1, 1),
            BookmarkNode("B", 2, 2),
        ]
        result = flatten(nodes)
        assert [n.title for n in result] == ["A", "B"]

    def test_flatten_dfs_order(self):
        nodes = [
            BookmarkNode(
                title="A", page=1, line_no=1,
                children=[BookmarkNode("A1", 2, 2)],
            ),
            BookmarkNode("B", 3, 3),
        ]
        result = flatten(nodes)
        assert [n.title for n in result] == ["A", "A1", "B"]


# ---------------------------------------------------------------------------
# 9. Round-trip tests (transform → to_indent_dot → parse → equivalent)
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Most transforms preserve structure when serialized + reparsed."""

    def test_round_trip_shift(self):
        nodes = _make_tree()
        _roundtrip(lambda n: shift_pages(n, 5), nodes)

    def test_round_trip_trim(self):
        nodes = _make_tree()
        _roundtrip(trim_titles, nodes)

    def test_round_trip_remove_invalid(self):
        nodes = _make_tree()
        _roundtrip(remove_invalid_pages, nodes)


class TestRebaseFirstPage:
    """Tests for rebase_first_page."""

    def test_rebase_basic(self):
        # First page 1 → target 5, offset=+4 applied to all non-None
        nodes = [
            BookmarkNode("A", page=1, line_no=1),
            BookmarkNode("B", page=3, line_no=2),
            BookmarkNode("C", page=10, line_no=3),
        ]
        result = rebase_first_page(nodes, target_first=5)
        assert _pages(result) == [5, 7, 14]

    def test_rebase_first_none_in_children(self):
        # First non-None page is inside children; rebase from there
        nodes = [
            BookmarkNode("A", page=None, line_no=1, children=[
                BookmarkNode("A1", page=3, line_no=2),
                BookmarkNode("A2", page=7, line_no=3),
            ]),
        ]
        result = rebase_first_page(nodes, target_first=1)
        # offset = 1 - 3 = -2, applied to A1 and A2
        assert _pages(result[0].children) == [1, 5]
        assert result[0].page is None  # A stays None

    def test_rebase_all_none(self):
        nodes = [
            BookmarkNode("A", page=None, line_no=1),
            BookmarkNode("B", page=None, line_no=2),
        ]
        result = rebase_first_page(nodes, target_first=5)
        assert _pages(result) == [None, None]

    def test_rebase_does_not_mutate_input(self):
        nodes = [
            BookmarkNode("A", page=1, line_no=1),
            BookmarkNode("B", page=5, line_no=2),
        ]
        original = _pages(nodes)
        rebase_first_page(nodes, target_first=10)
        assert _pages(nodes) == original

    def test_round_trip_rebase(self):
        nodes = _make_tree()
        _roundtrip(lambda n: rebase_first_page(n, 99), nodes)