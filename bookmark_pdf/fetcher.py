"""Fetch bookmarks from the online API (api.pdfshuwu.com)."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Final

from bookmark_pdf.parser import BookmarkNode, Parser

DEFAULT_API_URL: Final = "https://api.pdfshuwu.com/api/front/duxiu/info"
DEFAULT_TIMEOUT: Final = 30.0
USER_AGENT: Final = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class BookMeta:
    """Metadata returned by the API for one book."""
    ssid: str
    dxid: str
    isbn: str
    title: str
    author: str
    publish: str
    publish_time: str
    total_pages: int | None
    cover_url: str | None


class FetchError(Exception):
    """Raised when fetching fails for any reason."""


def fetch_bookmarks(
    ssid: str,
    *,
    api_url: str = DEFAULT_API_URL,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[BookMeta, list[BookmarkNode]]:
    """Fetch metadata + bookmark tree for the given SSID.

    Args:
        ssid: The book's SSID (string).
        api_url: Override the API endpoint (mostly for testing).
        timeout: Network timeout in seconds.

    Returns:
        (BookMeta, top-level BookmarkNode list)

    Raises:
        FetchError: network error, non-200 response, JSON parse failure,
                    missing data, or empty directory.
        ValueError: empty ssid.
    """
    if not ssid or not ssid.strip():
        raise ValueError("ssid must not be empty")

    url = f"{api_url}?{urllib.parse.urlencode({'ssid': ssid.strip()})}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        raise FetchError(f"HTTP {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise FetchError(f"网络错误: {e.reason}") from e
    except TimeoutError as e:
        raise FetchError(f"请求超时 ({timeout}s)") from e
    except OSError as e:
        raise FetchError(f"网络异常: {e}") from e

    if status != 200:
        raise FetchError(f"HTTP {status}")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise FetchError(f"响应解析失败: {e}") from e

    if str(payload.get("code")) != "200":
        msg = payload.get("message", "未知错误")
        raise FetchError(f"API 返回错误: {msg}")

    data = payload.get("data") or {}
    directory = data.get("dxDirectory") or []
    if not directory:
        raise FetchError("该 SSID 无目录数据")

    meta = BookMeta(
        ssid=str(data.get("dxSsid", ssid)),
        dxid=str(data.get("dxDxid", "")),
        isbn=str(data.get("dxIsbn", "")),
        title=str(data.get("dxTitle", "")).strip(),
        author=str(data.get("dxAuthor", "")).strip(),
        publish=str(data.get("dxPublish", "")).strip(),
        publish_time=str(data.get("dxPublishTime", "")).strip(),
        total_pages=_to_int(data.get("dxPage")),
        cover_url=data.get("dxImg") or None,
    )

    nodes = _directory_to_tree(directory)
    return meta, nodes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _directory_to_tree(directory: list[dict]) -> list[BookmarkNode]:
    """Convert the flat API directory to a BookmarkNode tree using `i` as level."""
    flat: list[tuple[int, BookmarkNode]] = []
    for idx, item in enumerate(directory, start=1):
        try:
            level = int(item.get("i", 0))
        except (ValueError, TypeError):
            level = 0
        page = _to_int(item.get("p"))
        title = str(item.get("c", "")).strip()
        if not title:
            continue
        flat.append((
            level,
            BookmarkNode(title=title, page=page, line_no=idx),
        ))
    return Parser._build_tree(flat)