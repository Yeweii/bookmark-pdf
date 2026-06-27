"""Unit tests for BookmarkNode tree → indent-dot TXT serializer."""
from bookmark_pdf.parser import BookmarkNode, Parser, to_indent_dot


# ---------------------------------------------------------------------------
# 1. Basic serialization
# ---------------------------------------------------------------------------


class TestToIndentDot:
    def test_single_node(self):
        nodes = [BookmarkNode("第一章", 1, 1)]
        text = to_indent_dot(nodes)
        assert text == "第一章 ...... 1"

    def test_two_levels(self):
        nodes = [
            BookmarkNode(
                title="第一章",
                page=1,
                line_no=1,
                children=[
                    BookmarkNode("1.1", 2, 2),
                    BookmarkNode("1.2", 3, 3),
                ],
            ),
        ]
        text = to_indent_dot(nodes)
        lines = text.split("\n")
        assert lines[0] == "第一章 ...... 1"
        assert lines[1] == "  1.1 ...... 2"
        assert lines[2] == "  1.2 ...... 3"

    def test_three_levels(self):
        nodes = [
            BookmarkNode(
                title="A",
                page=1,
                line_no=1,
                children=[
                    BookmarkNode(
                        title="B",
                        page=2,
                        line_no=2,
                        children=[BookmarkNode("C", 3, 3)],
                    ),
                ],
            ),
        ]
        text = to_indent_dot(nodes)
        lines = text.split("\n")
        assert lines == [
            "A ...... 1",
            "  B ...... 2",
            "    C ...... 3",
        ]

    def test_unicode(self):
        nodes = [BookmarkNode("概述 🚀", 1, 1)]
        text = to_indent_dot(nodes)
        assert text == "概述 🚀 ...... 1"

    def test_none_page(self):
        nodes = [BookmarkNode("Invalid", None, 1)]
        text = to_indent_dot(nodes)
        # page=None rendered as "?"
        assert text == "Invalid ...... ?"

    def test_custom_indent_spaces(self):
        nodes = [
            BookmarkNode(
                title="A", page=1, line_no=1,
                children=[BookmarkNode("B", 2, 2)],
            ),
        ]
        text = to_indent_dot(nodes, indent_spaces=4)
        assert text == "A ...... 1\n    B ...... 2"

    def test_empty_nodes(self):
        assert to_indent_dot([]) == ""

    def test_multiple_roots(self):
        nodes = [
            BookmarkNode("A", 1, 1),
            BookmarkNode("B", 2, 2),
        ]
        text = to_indent_dot(nodes)
        assert text == "A ...... 1\nB ...... 2"


# ---------------------------------------------------------------------------
# 2. Round-trip: parse(serialize(parse(text))) == parse(text)
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_round_trip_simple(self):
        original = "第一章 .......... 1\n  1.1 引言 .... 2\n  1.2 背景 .... 3\n"
        nodes1 = Parser(Parser.BUILTIN_RULES["indent-dot"]).parse(original)
        text = to_indent_dot(nodes1)
        nodes2 = Parser(Parser.BUILTIN_RULES["indent-dot"]).parse(text)

        def shape(ns):
            return [(n.title, n.page, shape(n.children)) for n in ns]
        assert shape(nodes1) == shape(nodes2)

    def test_round_trip_complex(self):
        original = (
            "A .... 1\n"
            "  B .... 2\n"
            "    C .... 3\n"
            "D .... 10\n"
            "  E .... 11\n"
        )
        nodes1 = Parser(Parser.BUILTIN_RULES["indent-dot"]).parse(original)
        text = to_indent_dot(nodes1)
        nodes2 = Parser(Parser.BUILTIN_RULES["indent-dot"]).parse(text)

        def shape(ns):
            return [(n.title, n.page, shape(n.children)) for n in ns]
        assert shape(nodes1) == shape(nodes2)

    def test_round_trip_unicode(self):
        original = "概述 🚀 .... 1\n  引言 .... 2\n"
        nodes1 = Parser(Parser.BUILTIN_RULES["indent-dot"]).parse(original)
        text = to_indent_dot(nodes1)
        nodes2 = Parser(Parser.BUILTIN_RULES["indent-dot"]).parse(text)

        def shape(ns):
            return [(n.title, n.page, shape(n.children)) for n in ns]
        assert shape(nodes1) == shape(nodes2)