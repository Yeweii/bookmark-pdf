"""Unit tests for fetcher.py using mocked HTTP responses."""
import json
from unittest.mock import MagicMock, patch

import pytest

from bookmark_pdf.fetcher import (
    DEFAULT_API_URL,
    BookMeta,
    FetchError,
    fetch_bookmarks,
)


# ---------------------------------------------------------------------------
# Sample API response (simplified, based on real response from ssid=13284383)
# ---------------------------------------------------------------------------

SAMPLE_PAYLOAD = {
    "code": "200",
    "message": "成功",
    "data": {
        "dxSsid": "13284383",
        "dxDxid": "000007934743",
        "dxIsbn": "7020084319",
        "dxTitle": "国朝闺秀诗柳絮集校补  1",
        "dxImg": "https://example.com/cover.jpg",
        "dxAuthor": "（清）黄秩模编辑；付琼校补",
        "dxPublish": "北京：人民文学出版社",
        "dxPublishTime": "2011",
        "dxPage": "410",
        "dxDirectory": [
            {"p": 1, "c": "前言&付琼", "i": 0},
            {"p": 1, "c": "卷一", "i": 0},
            {"p": 1, "c": "一东", "i": 1},
            {"p": 1, "c": "童凤  四首", "i": 2},
            {"p": 3, "c": "寒食舟中感怀", "i": 3},
            {"p": 3, "c": "秋日次天津怀云妹", "i": 3},
            {"p": 4, "c": "熊琏  八首", "i": 2},
            {"p": 5, "c": "凉夜", "i": 3},
        ],
    },
}


def _mock_urlopen(payload=None, status=200, side_effect=None):
    """Create a context manager mock that returns the given payload."""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8") if payload else b""
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ---------------------------------------------------------------------------
# 1. Success path
# ---------------------------------------------------------------------------


class TestFetchSuccess:
    def test_returns_meta_and_nodes(self):
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(SAMPLE_PAYLOAD)):
            meta, nodes = fetch_bookmarks("13284383")

        assert isinstance(meta, BookMeta)
        assert meta.ssid == "13284383"
        assert meta.title == "国朝闺秀诗柳絮集校补  1"
        assert meta.author == "（清）黄秩模编辑；付琼校补"
        assert meta.publish == "北京：人民文学出版社"
        assert meta.publish_time == "2011"
        assert meta.total_pages == 410
        assert meta.cover_url == "https://example.com/cover.jpg"
        assert len(nodes) >= 2  # 前言, 卷一, etc.

    def test_tree_hierarchy(self):
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(SAMPLE_PAYLOAD)):
            meta, nodes = fetch_bookmarks("13284383")

        # 卷一 should be a top-level node with children
        juan1 = next(n for n in nodes if n.title == "卷一")
        assert juan1.page == 1
        assert len(juan1.children) >= 1
        # 一东 is a child of 卷一
        yidong = next(c for c in juan1.children if c.title == "一东")
        # 童凤  四首 is a child of 一东
        tongfeng = next(c for c in yidong.children if "童凤" in c.title)
        # 寒食舟中感怀 is a child of 童凤
        han = next(c for c in tongfeng.children if c.title == "寒食舟中感怀")
        assert han.page == 3

    def test_api_url_construction(self):
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(SAMPLE_PAYLOAD)) as m:
            fetch_bookmarks("abc123")

        called_url = m.call_args[0][0].full_url
        assert called_url.startswith(DEFAULT_API_URL)
        assert "ssid=abc123" in called_url

    def test_spaces_in_ssid_stripped(self):
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(SAMPLE_PAYLOAD)) as m:
            fetch_bookmarks("  abc123  ")
        assert "ssid=abc123" in m.call_args[0][0].full_url


# ---------------------------------------------------------------------------
# 2. Error handling
# ---------------------------------------------------------------------------


class TestFetchErrors:
    def test_empty_ssid_raises_value_error(self):
        with pytest.raises(ValueError):
            fetch_bookmarks("")
        with pytest.raises(ValueError):
            fetch_bookmarks("   ")

    def test_http_error_raises_fetch_error(self):
        import urllib.error
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(url="x", code=404, msg="Not Found", hdrs=None, fp=None),
        ):
            with pytest.raises(FetchError, match="HTTP"):
                fetch_bookmarks("123")

    def test_url_error_raises_fetch_error(self):
        import urllib.error
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("dns fail"),
        ):
            with pytest.raises(FetchError, match="网络"):
                fetch_bookmarks("123")

    def test_timeout_raises_fetch_error(self):
        with patch("urllib.request.urlopen", side_effect=TimeoutError("slow")):
            with pytest.raises(FetchError, match="超时"):
                fetch_bookmarks("123")

    def test_non_200_status_raises_fetch_error(self):
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(SAMPLE_PAYLOAD, status=500)):
            with pytest.raises(FetchError, match="500"):
                fetch_bookmarks("123")

    def test_bad_json_raises_fetch_error(self):
        bad_resp = _mock_urlopen()
        bad_resp.read.return_value = b"<html>not json</html>"
        with patch("urllib.request.urlopen", return_value=bad_resp):
            with pytest.raises(FetchError, match="解析"):
                fetch_bookmarks("123")

    def test_api_error_code_raises_fetch_error(self):
        bad = {"code": "500", "message": "SSID 不存在", "data": None}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(bad)):
            with pytest.raises(FetchError, match="SSID 不存在"):
                fetch_bookmarks("123")

    def test_empty_directory_raises_fetch_error(self):
        empty = {"code": "200", "message": "成功", "data": {"dxDirectory": []}}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(empty)):
            with pytest.raises(FetchError, match="无目录"):
                fetch_bookmarks("123")

    def test_missing_data_field_raises_fetch_error(self):
        no_data = {"code": "200", "message": "成功", "data": None}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(no_data)):
            with pytest.raises(FetchError, match="无目录"):
                fetch_bookmarks("123")


# ---------------------------------------------------------------------------
# 3. Integration with parser (round-trip)
# ---------------------------------------------------------------------------


class TestFetcherIntegration:
    def test_fetched_tree_can_be_serialized(self):
        from bookmark_pdf.parser import to_indent_dot

        with patch("urllib.request.urlopen", return_value=_mock_urlopen(SAMPLE_PAYLOAD)):
            _, nodes = fetch_bookmarks("13284383")

        text = to_indent_dot(nodes)
        assert "卷一" in text
        assert "寒食舟中感怀" in text
        # Children of 卷一 should be indented
        assert "\n  一东" in text or text.startswith("  ")