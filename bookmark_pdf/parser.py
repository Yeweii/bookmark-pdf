"""Parser for TXT/MD bookmark files.

Public API:
    - ParseRule: dataclass describing a parsing rule
    - BookmarkNode: tree node representing a bookmark
    - ParseError: exception raised on unrecoverable parse failures
    - Parser: parses text/file into a list of root BookmarkNode
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class BookmarkNode:
    """A single bookmark entry in the parsed tree."""
    title: str
    page: int | None  # 1-based; None when page is missing/invalid
    line_no: int  # 1-based line number in source file
    children: list["BookmarkNode"] = field(default_factory=list)


@dataclass(frozen=True)
class ParseRule:
    """Definition of how to parse one line of input.

    Required named groups in line_pattern: `title`, `page`.
    Optional: `indent` (for level_mode="indent"), `hashes` (for level_mode="md_header").
    """
    name: str
    line_pattern: str
    level_mode: Literal["flat", "indent", "md_header"] = "flat"
    indent_spaces: int = 2

    def __post_init__(self) -> None:
        try:
            compiled = re.compile(self.line_pattern)
        except re.error as e:
            raise ValueError(
                f"ParseRule {self.name!r}: invalid regex: {e}"
            ) from e
        if "title" not in compiled.groupindex:
            raise ValueError(
                f"ParseRule {self.name!r}: line_pattern must contain 'title' named group"
            )
        if "page" not in compiled.groupindex:
            raise ValueError(
                f"ParseRule {self.name!r}: line_pattern must contain 'page' named group"
            )


class ParseError(Exception):
    """Raised when a line cannot be parsed (e.g. empty title)."""

    def __init__(self, line_no: int, content: str, reason: str) -> None:
        super().__init__(f"Line {line_no}: {reason} (content: {content!r})")
        self.line_no = line_no
        self.content = content
        self.reason = reason


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class Parser:
    """Parses TXT or MD bookmark text into a tree of BookmarkNode."""

    BUILTIN_RULES: dict[str, ParseRule] = {
        # --- TXT ---
        "flat": ParseRule(
            name="flat",
            # page allows letters too so invalid-page lines still parse (page=None)
            line_pattern=r"^(?P<page>[\dA-Za-z]+)\s+(?P<title>.+)$",
        ),
        "indent-dot": ParseRule(
            name="indent-dot",
            line_pattern=(
                r"^(?P<indent>\s*)(?P<title>.+?)"
                r"\s*[.\s]+(?P<page>\d+)\s*$"
            ),
            level_mode="indent",
        ),
        "chapter": ParseRule(
            name="chapter",
            # Preserve "第X章" prefix in the captured title
            line_pattern=(
                r"^(?P<title>第[一二三四五六七八九十百]+章\s+.+?)"
                r"\s+(?P<page>\d+)\s*$"
            ),
        ),
        # --- MD ---
        "md-header-suffix": ParseRule(
            name="md-header-suffix",
            line_pattern=(
                r"^(?P<hashes>#{1,6})\s+(?P<title>.+?)"
                r"\s*[.\s…]+(?P<page>\d+)\s*$"
            ),
            level_mode="md_header",
        ),
        "md-header-comment": ParseRule(
            name="md-header-comment",
            line_pattern=(
                r"^(?P<hashes>#{1,6})\s+(?P<title>.+?)"
                r"\s*<!--\s*(?P<page>\d+)\s*-->\s*$"
            ),
            level_mode="md_header",
        ),
        "md-toc-link": ParseRule(
            name="md-toc-link",
            line_pattern=(
                r"^(?P<indent>\s*)[-*]\s+"
                r"\[(?P<title>[^\]]+)\]\([^)]+\)"
                r"\s+(?P<page>\d+)\s*$"
            ),
            level_mode="indent",
        ),
    }

    def __init__(self, rule: ParseRule) -> None:
        self.rule = rule
        self._pattern = re.compile(rule.line_pattern)

    # -- public API ----------------------------------------------------------

    def parse(self, text: str) -> list[BookmarkNode]:
        """Parse text and return the list of root-level bookmarks."""
        flat: list[tuple[int, BookmarkNode]] = []
        for line_no, raw_line in enumerate(text.splitlines(), start=1):
            if self._is_blank(raw_line):
                continue
            m = self._pattern.match(raw_line)
            if not m:
                continue
            node, depth = self._build_node(line_no, raw_line, m)
            flat.append((depth, node))
        return self._build_tree(flat)

    def parse_file(self, path: Path) -> list[BookmarkNode]:
        """Read a file (UTF-8) and parse it."""
        return self.parse(path.read_text(encoding="utf-8"))

    # -- internals -----------------------------------------------------------

    @staticmethod
    def _is_blank(line: str) -> bool:
        return not line.strip()

    def _build_node(
        self,
        line_no: int,
        raw_line: str,
        m: re.Match,
    ) -> tuple[BookmarkNode, int]:
        groups = m.groupdict()
        title = (groups.get("title") or "").strip()
        if not title:
            raise ParseError(line_no, raw_line, "标题为空")

        page_raw = (groups.get("page") or "").strip()
        page: int | None = int(page_raw) if page_raw.isdigit() else None

        depth = self._compute_depth(groups)
        return BookmarkNode(title=title, page=page, line_no=line_no), depth

    def _compute_depth(self, groups: dict[str, str]) -> int:
        if self.rule.level_mode == "flat":
            return 0
        if self.rule.level_mode == "indent":
            indent = groups.get("indent") or ""
            return len(indent) // self.rule.indent_spaces
        if self.rule.level_mode == "md_header":
            hashes = groups.get("hashes") or ""
            return len(hashes)
        return 0

    @staticmethod
    def _build_tree(flat: list[tuple[int, BookmarkNode]]) -> list[BookmarkNode]:
        """Convert a flat list of (depth, node) into a tree.

        Maintains a stack of ancestor nodes; pops while top depth >= current depth,
        then attaches the current node as a child of the new top (or as a root).
        """
        roots: list[BookmarkNode] = []
        stack: list[tuple[int, BookmarkNode]] = []
        for depth, node in flat:
            while stack and stack[-1][0] >= depth:
                stack.pop()
            if stack:
                stack[-1][1].children.append(node)
            else:
                roots.append(node)
            stack.append((depth, node))
        return roots