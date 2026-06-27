# Proposal: 书签文本编辑工具集（v1.4）

> 日期：2026-06-27
> 关联 Plan：v1.4 增量

---

## 1. 背景与目标

### 1.1 当前痛点

v1.2 引入了「书签文本（可编辑）」section，用户可手动编辑书签。但缺乏**批量处理工具**：

- 复制了一份书签后想"全部页码 +5"或"-5"，必须逐行手动改
- 标题含多余空白、重复条目、异常页码需手工清理
- 无法批量重命名、添加前缀、归一化编号
- 工具散布在外部脚本里，用户得切走编辑

### 1.2 目标

新增一组**书签文本编辑工具**，覆盖最常见的批量操作：

1. **页码批量偏移**（用户明确要求）：所有页码 +/- N
2. **其他实用工具**：归一化、裁剪、去重、Trim、展平、按页排序、前缀、移除异常等
3. **不破坏现有数据流**：所有工具作用于 BookmarkNode 列表 → 写回文本 → 重解析

### 1.3 非目标

- 不替代外部脚本（只覆盖最常见操作）
- 不支持自定义工具（用户可写 Python 脚本）
- 不修改解析器或挂载器

---

## 2. 候选工具列表

按优先级划分（先做 P0 + P1，P2 留待后续）：

| 优先级 | 工具 | 类别 | 说明 |
|--------|------|------|------|
| **P0** | `shift_pages(offset)` | 页码 | 所有页码 +/- N（None 不变） |
| **P0** | `normalize_pages(start=1)` | 页码 | 从 start 开始按出现顺序重新编号 |
| **P0** | `cap_pages(max_page)` | 页码 | 超过 max 的设为 None |
| **P0** | `sort_by_page(descending=False)` | 树形 | 按页码升/降序排列，保留层级 |
| **P1** | `remove_duplicates()` | 清理 | title + page 相同的去重（保留首次） |
| **P1** | `remove_invalid_pages()` | 清理 | 移除 page=None 的条目 |
| **P1** | `trim_titles()` | 文本 | 去除标题首尾空白 |
| **P1** | `flatten()` | 树形 | 移除所有缩进，所有条目同级（深度 0） |
| **P2** | `prefix_titles(prefix)` | 文本 | 所有标题加前缀 |
| **P2** | `remove_titles_matching(regex)` | 文本 | 标题匹配正则的移除 |
| **P2** | `fix_negative_pages()` | 页码 | < 1 的设为 None |

**首版交付**：P0 + P1（共 8 个工具）。

---

## 3. 候选布局方案

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| **A. 工具栏 + 工具弹窗（推荐）** | 常用工具直接按钮；高级工具放弹窗 | 平衡易触达与可扩展 | 略复杂 |
| B. 仅工具栏 | 8 个按钮横排 | 简单 | 占空间，难扩展 |
| C. 仅工具弹窗 | 一个 `🔧 工具` 按钮 | 紧凑 | 每次多点一下 |
| D. 右键菜单 | Text 右键弹菜单 | 不占 UI | 发现性差 |

**决策**：A。

**主工具栏**（直接在 section 内）：

```
[📥 从 PDF 读取书签] [🔄 解析文本] [+/- 页码: [N] [应用]] [🔧 工具 ▼] [📋 清空] [💾 导出 TXT]
```

**工具弹窗**（点 `🔧 工具` → Toplevel 窗口）：

```
┌─ 书签文本工具 ─────────────────────┐
│ [页码]    [文本]    [树形]   [清理] │  ← 分类
│ ──────────────────────────────────│
│ ○ 归一化（从 1 开始重新编号）      │
│ ○ 裁剪到最大页 [_]                 │
│ ○ 修复负页码                      │
│ ──────────────────────────────────│
│ ○ 去除重复条目                    │
│ ○ 移除异常页码条目                │
│ ○ 去除标题首尾空白                │
│ ○ 所有标题加前缀 [_]              │
│ ○ 删除匹配正则 [_]                │
│ ──────────────────────────────────│
│ ○ 展平（移除层级）                │
│ ○ 按页码升序 / 降序               │
│ ──────────────────────────────────│
│           [执行]  [取消]          │
└────────────────────────────────────┘
```

---

## 4. 模块设计

### 4.1 新增 `bookmark_pdf/transforms.py`

每个工具都是**纯函数**：接受 `list[BookmarkNode]` → 返回 `list[BookmarkNode]`。

```python
"""Bookmark node transforms — pure functions for batch editing."""
from __future__ import annotations

import re
from typing import Callable

from bookmark_pdf.parser import BookmarkNode


Transform = Callable[[list[BookmarkNode]], list[BookmarkNode]]


def shift_pages(nodes: list[BookmarkNode], offset: int) -> list[BookmarkNode]:
    """Shift all page numbers by `offset`. None pages stay None."""
    def walk(n: BookmarkNode) -> BookmarkNode:
        new_page = (n.page + offset) if n.page is not None else None
        return BookmarkNode(
            title=n.title, page=new_page, line_no=n.line_no,
            children=[walk(c) for c in n.children],
        )
    return [walk(n) for n in nodes]


def normalize_pages(nodes: list[BookmarkNode], start: int = 1) -> list[BookmarkNode]:
    """Reassign pages 1..N by DFS order."""
    counter = [start - 1]
    def walk(n: BookmarkNode) -> BookmarkNode:
        counter[0] += 1
        return BookmarkNode(
            title=n.title, page=counter[0], line_no=n.line_no,
            children=[walk(c) for c in n.children],
        )
    return [walk(n) for n in nodes]


def cap_pages(nodes: list[BookmarkNode], max_page: int) -> list[BookmarkNode]:
    """Set page=None for entries exceeding max_page."""
    def walk(n: BookmarkNode) -> BookmarkNode:
        new_page = n.page if (n.page is not None and n.page <= max_page) else None
        return BookmarkNode(
            title=n.title, page=new_page, line_no=n.line_no,
            children=[walk(c) for c in n.children],
        )
    return [walk(n) for n in nodes]


def sort_by_page(
    nodes: list[BookmarkNode],
    descending: bool = False,
) -> list[BookmarkNode]:
    """Sort by page; entries with page=None go last regardless of order."""
    key = lambda n: (n.page is None, -(n.page or 0) if descending else (n.page or 0))
    sorted_nodes = sorted(nodes, key=key)
    # Recurse into children
    return [
        BookmarkNode(
            title=n.title, page=n.page, line_no=n.line_no,
            children=sort_by_page(n.children, descending),
        )
        for n in sorted_nodes
    ]


def remove_duplicates(nodes: list[BookmarkNode]) -> list[BookmarkNode]:
    """Remove entries with duplicate (title, page). Keep first occurrence."""
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
    """Remove entries with page=None (recursively)."""
    result: list[BookmarkNode] = []
    for n in nodes:
        if n.page is not None:
            result.append(BookmarkNode(
                title=n.title, page=n.page, line_no=n.line_no,
                children=remove_invalid_pages(n.children),
            ))
    return result


def trim_titles(nodes: list[BookmarkNode]) -> list[BookmarkNode]:
    """Strip whitespace from titles."""
    def walk(n: BookmarkNode) -> BookmarkNode:
        return BookmarkNode(
            title=n.title.strip(), page=n.page, line_no=n.line_no,
            children=[walk(c) for c in n.children],
        )
    return [walk(n) for n in nodes]


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


# --- P2 (not in v1.4 first cut) ---

def prefix_titles(nodes: list[BookmarkNode], prefix: str) -> list[BookmarkNode]:
    ...

def remove_titles_matching(nodes: list[BookmarkNode], pattern: str) -> list[BookmarkNode]:
    ...

def fix_negative_pages(nodes: list[BookmarkNode]) -> list[BookmarkNode]:
    ...
```

### 4.2 GUI 改动

**新增内联 Spinbox（页码 +/- 直接显示）**：

```python
# 在 _build_text_section 按钮区
ttk.Label(btn_frame, text="页码 +/-").pack(side=tk.LEFT, padx=(8, 2))
self._page_shift_var = tk.IntVar(value=0)
ttk.Spinbox(
    btn_frame, from_=-9999, to=9999, textvariable=self._page_shift_var,
    width=6,
).pack(side=tk.LEFT, padx=2)
ttk.Button(
    btn_frame, text="应用", command=self._do_shift_pages,
).pack(side=tk.LEFT, padx=2)
ttk.Button(
    btn_frame, text="🔧 工具 ▼", command=self._open_tools_window,
).pack(side=tk.LEFT, padx=(8, 2))
```

**新增 `_open_tools_window`**：弹 Toplevel，列出其他工具。

**新增抽象方法 `_apply_transform`**：
```python
def _apply_transform(self, transform: Transform) -> None:
    """Apply a node-list transform and refresh text + preview."""
    if not self._last_nodes:
        messagebox.showwarning("提示", "请先解析书签")
        return
    try:
        new_nodes = transform(self._last_nodes)
    except Exception as e:
        messagebox.showerror("工具失败", f"{type(e).__name__}: {e}")
        return
    self._last_nodes = new_nodes
    self._set_text_content(to_indent_dot(new_nodes))
    self._refresh_preview(new_nodes)
    self._update_run_button()
    self._log_append(f"✓ 已应用工具: {transform.__name__}")
```

**新增 `_do_shift_pages`**：
```python
def _do_shift_pages(self) -> None:
    offset = self._page_shift_var.get()
    self._apply_transform(lambda nodes: shift_pages(nodes, offset))
```

### 4.3 GUI 工具弹窗

点 `🔧 工具` → 弹 `Toplevel`：
- 左侧分类（页码 / 文本 / 树形 / 清理）
- 右侧工具列表（Radiobutton + 参数输入框）
- 底部 [执行] [取消]

参数输入框：
- `cap_pages`: Spinbox (1-9999)
- `prefix_titles`: Entry (P2)
- `remove_titles_matching`: Entry (P2)

---

## 5. 错误处理

| 场景 | 处理 |
|------|------|
| `_last_nodes` 为空 | `messagebox.showwarning` 提示先解析 |
| transform 抛错 | `messagebox.showerror` 显示异常 |
| Spinbox offset 为 0 | 允许（no-op） |
| 工具参数非法（如 cap_pages=-1） | 输入时校验 |

---

## 6. 测试策略

### 6.1 单元测试 `tests/test_transforms.py` 新增

每个 transform ≥ 2 用例：

- `shift_pages` /  `shift_pages_with_none` / `shift_pages_nested`
- `normalize_pages` / `normalize_pages_with_start_5`
- `cap_pages` / `cap_pages_nested`
- `sort_by_page_asc` / `sort_by_page_desc` / `sort_by_page_with_none`
- `remove_duplicates` / `remove_duplicates_nested`
- `remove_invalid_pages` / `remove_invalid_pages_keeps_children`
- `trim_titles` / `trim_titles_nested`
- `flatten` / `flatten_already_flat`
- Round-trip：to_indent_dot → parse → 结构等价（除归一化等改变语义的操作）

### 6.2 GUI 手动验收

- 输入文本 → 点页码 Spinbox +5 + 应用 → 文本自动更新 + 预览刷新
- 点 🔧 工具 → 弹窗 → 选"归一化" → 执行 → 文本从 1 开始重新编号
- 选"按页码降序" → 文本顺序改变

---

## 7. 风险与权衡

| 风险 | 缓解 |
|------|------|
| 工具按钮挤占 UI | 主工具栏只放页码 +/-；其他工具放弹窗 |
| transform 误删数据 | 先存 `_last_nodes` 在 transform 前；可加"撤销"按钮（v1.4 后） |
| 大量工具难以发现 | 弹窗分类展示，命名清晰 |
| 页码归一化与 PDF 实际页数不匹配 | 用户自行保证；如需校验，可加 cap_pages |

---

## 8. 验收标准

- [ ] 8 个 P0+P1 transform 函数全部实现并通过单测
- [ ] `transforms.py` 模块导出清晰
- [ ] 主工具栏页码 +/- Spinbox 工作
- [ ] 🔧 工具弹窗可打开，列出其余工具
- [ ] 执行 transform 后文本、预览、_last_nodes 三者同步
- [ ] 81 个旧测试 + 新增 transforms 测试全部通过
- [ ] README 补充「书签文本工具」用法
- [ ] GUI 启动 < 1s（不显著退化）

---

## 9. 工作量预估

| 模块 | 工作量 |
|------|--------|
| `transforms.py` 模块（8 个 P0+P1）+ 单测 | 1.5h |
| GUI：页码 Spinbox + 应用按钮 + 工具弹窗 | 1.5h |
| `_apply_transform` 抽象 | 0.3h |
| README + spec + plan/tasks 更新 | 0.5h |
| 手动验收 + commit | 0.2h |
| **总计** | **4h** |