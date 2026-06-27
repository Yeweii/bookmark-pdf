"""Unit tests for parser.py (TXT + MD templates)."""
from pathlib import Path

import pytest

from bookmark_pdf.parser import BookmarkNode, ParseError, ParseRule, Parser


# ---------------------------------------------------------------------------
# 1. TXT flat 模板
# ---------------------------------------------------------------------------

class TestTXTFlat:
    def test_basic_flat(self):
        text = "1 第一章\n2 第二章\n3 第三章\n"
        rule = Parser.BUILTIN_RULES["flat"]
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 3
        assert nodes[0].title == "第一章"
        assert nodes[0].page == 1
        assert nodes[1].title == "第二章"
        assert nodes[1].page == 2
        assert nodes[2].title == "第三章"
        assert nodes[2].page == 3
        assert all(n.children == [] for n in nodes)

    def test_flat_line_no_tracking(self):
        text = "\n\n# 注释\n1 标题\n"
        rule = Parser.BUILTIN_RULES["flat"]
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 1
        assert nodes[0].title == "标题"
        assert nodes[0].page == 1
        # line_no 指向源文件中匹配的行（含前导空行/注释）
        assert nodes[0].line_no == 4

    def test_flat_unicode(self):
        text = "1 引言 🚀\n2 背景\n"
        rule = Parser.BUILTIN_RULES["flat"]
        nodes = Parser(rule).parse(text)

        assert nodes[0].title == "引言 🚀"

    def test_flat_no_match_lines_skipped(self):
        text = "1 标题\n无效行\n2 标题二\n"
        rule = Parser.BUILTIN_RULES["flat"]
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 2


# ---------------------------------------------------------------------------
# 2. TXT indent-dot 模板
# ---------------------------------------------------------------------------

class TestTXTIndent:
    def test_indent_basic(self):
        text = (
            "第一章 .......... 1\n"
            "  1.1 引言 ... 2\n"
            "  1.2 背景 ... 3\n"
            "第二章 .......... 10\n"
        )
        rule = Parser.BUILTIN_RULES["indent-dot"]
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 2
        assert nodes[0].title == "第一章"
        assert nodes[0].page == 1
        assert len(nodes[0].children) == 2
        assert nodes[0].children[0].title == "1.1 引言"
        assert nodes[0].children[0].page == 2
        assert nodes[1].title == "第二章"
        assert nodes[1].children == []

    def test_indent_three_levels(self):
        text = (
            "A .... 1\n"
            "  B .... 2\n"
            "    C .... 3\n"
        )
        rule = Parser.BUILTIN_RULES["indent-dot"]
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 1
        a = nodes[0]
        assert a.title == "A"
        assert len(a.children) == 1
        b = a.children[0]
        assert b.title == "B"
        assert len(b.children) == 1
        c = b.children[0]
        assert c.title == "C"


# ---------------------------------------------------------------------------
# 3. TXT chapter 模板
# ---------------------------------------------------------------------------

class TestTXTChapter:
    def test_chapter_basic(self):
        text = (
            "第一章 引言 1\n"
            "第二章 背景 5\n"
            "第三章 方法 10\n"
        )
        rule = Parser.BUILTIN_RULES["chapter"]
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 3
        assert nodes[0].title == "第一章 引言"
        assert nodes[0].page == 1

    def test_chapter_complex_number(self):
        text = "第二十三章 复杂章节 99\n"
        rule = Parser.BUILTIN_RULES["chapter"]
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 1
        assert nodes[0].page == 99


# ---------------------------------------------------------------------------
# 4. MD header-suffix 模板
# ---------------------------------------------------------------------------

class TestMDHeaderSuffix:
    def test_basic(self):
        text = "# 第一章 .......... 1\n## 1.1 引言 ........... 2\n### 1.1.1 详细 ... 3\n## 1.2 背景 ........ 4\n# 第二章 ........ 10\n"
        rule = Parser.BUILTIN_RULES["md-header-suffix"]
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 2
        assert nodes[0].title == "第一章"
        assert nodes[0].page == 1
        assert len(nodes[0].children) == 2
        assert nodes[0].children[0].title == "1.1 引言"
        assert nodes[0].children[0].page == 2
        assert len(nodes[0].children[0].children) == 1
        assert nodes[0].children[0].children[0].title == "1.1.1 详细"
        assert nodes[0].children[0].children[0].page == 3
        assert nodes[1].title == "第二章"
        assert nodes[1].page == 10

    def test_level_from_hash_count(self):
        text = "## 2级标题 ... 1\n#### 4级标题 ... 2\n"
        rule = Parser.BUILTIN_RULES["md-header-suffix"]
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 1
        # ## 是 2 级，#### 是 4 级（#### 是 ## 的子节点）
        assert nodes[0].title == "2级标题"
        assert len(nodes[0].children) == 1
        assert nodes[0].children[0].title == "4级标题"

    def test_h6_max_level(self):
        text = "###### 第6级 ... 1\n"
        rule = Parser.BUILTIN_RULES["md-header-suffix"]
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 1
        assert nodes[0].title == "第6级"

    def test_h7_or_more_not_header(self):
        # 7+ 个 # 不视为标题
        text = "####### 非标题行 ... 1\n"
        rule = Parser.BUILTIN_RULES["md-header-suffix"]
        nodes = Parser(rule).parse(text)

        assert nodes == []


# ---------------------------------------------------------------------------
# 5. MD header-comment 模板
# ---------------------------------------------------------------------------

class TestMDHeaderComment:
    def test_basic(self):
        text = (
            "# 概述 <!-- 1 -->\n"
            "## 背景 <!-- 3 -->\n"
            "## 方法 <!-- 5 -->\n"
            "# 结论 <!-- 20 -->\n"
        )
        rule = Parser.BUILTIN_RULES["md-header-comment"]
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 2
        assert nodes[0].title == "概述"
        assert nodes[0].page == 1
        assert len(nodes[0].children) == 2
        assert nodes[1].title == "结论"
        assert nodes[1].page == 20


# ---------------------------------------------------------------------------
# 6. MD toc-link 模板
# ---------------------------------------------------------------------------

class TestMDTocLink:
    def test_basic(self):
        text = (
            "- [第一章](#ch1) 1\n"
            "  - [1.1 引言](#ch1-1) 2\n"
            "  - [1.2 背景](#ch1-2) 3\n"
            "- [第二章](#ch2) 10\n"
        )
        rule = Parser.BUILTIN_RULES["md-toc-link"]
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 2
        assert nodes[0].title == "第一章"
        assert nodes[0].page == 1
        assert len(nodes[0].children) == 2
        assert nodes[1].title == "第二章"

    def test_toc_star_bullet(self):
        text = "* [标题](#x) 5\n"
        rule = Parser.BUILTIN_RULES["md-toc-link"]
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 1
        assert nodes[0].page == 5


# ---------------------------------------------------------------------------
# 7. 异常页码 / 跳过行 / 错误处理
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_invalid_page_becomes_none(self):
        text = "1 标题一\nabc 无效页码\n3 标题三\n"
        rule = Parser.BUILTIN_RULES["flat"]
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 3
        assert nodes[0].page == 1
        assert nodes[1].page is None
        assert nodes[1].title == "无效页码"
        assert nodes[2].page == 3

    def test_skip_blank_and_comment_lines(self):
        text = "\n# 注释\n// 另一注释\n<!-- 注释 -->\n1 实际标题\n"
        rule = Parser.BUILTIN_RULES["flat"]
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 1
        assert nodes[0].title == "实际标题"

    def test_empty_title_raises_parse_error(self):
        # 模拟：行能匹配但 title 捕获组为空
        rule = ParseRule(
            name="custom",
            line_pattern=r"^(?P<page>\d+)\s*(?P<title>.*)$",
        )
        text = "1 \n"  # 只有页码，title 是空字符串
        with pytest.raises(ParseError) as exc_info:
            Parser(rule).parse(text)
        assert exc_info.value.line_no == 1
        assert "empty" in exc_info.value.reason.lower() or "标题" in exc_info.value.reason

    def test_custom_rule_missing_named_group_raises(self):
        with pytest.raises(ValueError, match="title"):
            ParseRule(
                name="bad",
                line_pattern=r"^(?P<page>\d+)$",  # 没有 title
            )

    def test_custom_rule_missing_page_group_raises(self):
        with pytest.raises(ValueError, match="page"):
            ParseRule(
                name="bad",
                line_pattern=r"^(?P<title>.+)$",  # 没有 page
            )


# ---------------------------------------------------------------------------
# 8. 自定义正则
# ---------------------------------------------------------------------------

class TestCustomRegex:
    def test_custom_pattern_simple(self):
        rule = ParseRule(
            name="custom-bracket",
            line_pattern=r"^\[(?P<page>\d+)\]\s+(?P<title>.+)$",
        )
        text = "[1] 章节一\n[5] 章节二\n"
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 2
        assert nodes[0].title == "章节一"
        assert nodes[0].page == 1

    def test_custom_pattern_with_indent_mode(self):
        rule = ParseRule(
            name="custom-indent",
            line_pattern=r"^(?P<indent>\s*)>>>(?P<title>.+?)\s*\|\s*(?P<page>\d+)\s*$",
            level_mode="indent",
            indent_spaces=2,
        )
        text = ">>> 顶层 | 1\n  >>> 子层 | 2\n    >>> 孙层 | 3\n"
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 1
        assert len(nodes[0].children) == 1
        assert len(nodes[0].children[0].children) == 1
        assert nodes[0].children[0].children[0].title == "孙层"

    def test_custom_pattern_with_md_header_mode(self):
        rule = ParseRule(
            name="custom-md",
            line_pattern=r"^(?P<hashes>#+)\s+(?P<title>.+?)\s*=\s*(?P<page>\d+)$",
            level_mode="md_header",
        )
        text = "# 一级 = 1\n## 二级 = 2\n"
        nodes = Parser(rule).parse(text)

        assert len(nodes) == 1
        assert len(nodes[0].children) == 1


# ---------------------------------------------------------------------------
# 9. parse_file 便捷方法
# ---------------------------------------------------------------------------

class TestParseFile:
    def test_parse_txt_file(self, tmp_path: Path):
        f = tmp_path / "bookmarks.txt"
        f.write_text("1 第一章\n2 第二章\n", encoding="utf-8")
        rule = Parser.BUILTIN_RULES["flat"]
        nodes = Parser(rule).parse_file(f)

        assert len(nodes) == 2

    def test_parse_md_file(self, tmp_path: Path):
        f = tmp_path / "bookmarks.md"
        f.write_text("# 概述 <!-- 1 -->\n## 背景 <!-- 3 -->\n", encoding="utf-8")
        rule = Parser.BUILTIN_RULES["md-header-comment"]
        nodes = Parser(rule).parse_file(f)

        assert len(nodes) == 1
        assert len(nodes[0].children) == 1


# ---------------------------------------------------------------------------
# 10. 内置模板存在性
# ---------------------------------------------------------------------------

class TestBuiltinRules:
    def test_all_builtin_rules_have_required_named_groups(self):
        for name, rule in Parser.BUILTIN_RULES.items():
            assert "title" in rule.line_pattern, f"{name} missing title group"
            assert "page" in rule.line_pattern, f"{name} missing page group"
            assert rule.level_mode in ("flat", "indent", "md_header")

    def test_six_builtin_rules(self):
        expected = {
            "flat", "indent-dot", "chapter",
            "md-header-suffix", "md-header-comment", "md-toc-link",
        }
        assert set(Parser.BUILTIN_RULES.keys()) == expected