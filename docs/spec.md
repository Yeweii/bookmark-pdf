# Spec: TXT/MD 书签挂载到 PDF

> 规范驱动开发（SDD）规格文档
> 版本：v1.5 · 日期：2026-06-27
> 涵盖变更：v1.0 核心 / v1.1 在线获取 / v1.2 文本编辑 / v1.3 弹框保存 / v1.4 工具集

---

## 1. 概述

本项目实现一个 Python 工具，读取 **TXT** 或 **MD（Markdown）** 格式的书签文件，将其解析为层级树，并写入 PDF 的 outline（书签）字段，生成可跳转的导航。同时提供 Tkinter GUI 供用户操作。

---

## 2. 目标与非目标

### 2.1 目标
- ✅ 解析 TXT 三种常见格式（扁平 / 缩进 / 章节）
- ✅ 解析 MD 三种常见格式（标题行内附页码 / HTML 注释页码 / TOC 链接）
- ✅ 支持自定义正则解析规则
- ✅ 将解析结果挂载为 PDF outline，保留层级
- ✅ GUI 可视化操作：选择文件 → 配置规则 → 预览 → 执行
- ✅ 单元测试覆盖核心解析与挂载逻辑

### 2.2 非目标
- ❌ PDF 内容修改（文字、图片编辑）
- ❌ 加密 / DRM PDF 处理
- ❌ 多语言 GUI（仅中文界面）
- ❌ 跨平台打包（.exe / .app / .dmg），需要时另行 PyInstaller 处理
- ❌ PDF outline 之外的注释、表单字段处理

---

## 3. 功能需求（FR）

| ID | 描述 |
|----|------|
| FR-1 | 解析 TXT 文件，输出 `list[BookmarkNode]` 树形结构 |
| FR-2 | 解析 MD 文件，输出 `list[BookmarkNode]` 树形结构 |
| FR-3 | 提供 6 种内置解析模板（3 TXT + 3 MD） |
| FR-4 | 允许用户自定义正则，命名组必须含 `title`、`page` |
| FR-5 | 解析空行、注释行（`#` / `//` / `<!--` 开头）跳过 |
| FR-6 | 解析页码非数字 → `page=None`，不抛错但预览标红 |
| FR-7 | 解析标题缺失 → 抛 `ParseError` |
| FR-8 | 挂载书签到 PDF：3 种 mode（replace / append / merge） |
| FR-9 | 页码越界 → 抛 `PageOutOfRangeError` |
| FR-10 | GUI：文件选择、规则编辑、预览、执行一体化 |
| FR-11 | GUI：Treeview 预览，异常条目标红 |
| FR-12 | GUI：进度回调驱动进度条，防止主线程阻塞 |
| FR-13 | GUI：输出策略可切换（新文件 / 原位覆盖） |

---

## 4. 非功能需求（NFR）

| ID | 描述 |
|----|------|
| NFR-1 | Python ≥ 3.10，仅依赖 `pypdf>=4.0`（运行） |
| NFR-2 | GUI 框架：Tkinter 标准库，零额外 GUI 依赖 |
| NFR-3 | 单元测试覆盖 ≥ 80% 行覆盖（parser + bookmark） |
| NFR-4 | 解析 1000 行 TXT 耗时 < 100ms |
| NFR-5 | 跨平台：macOS / Linux / Windows 均可运行 |
| NFR-6 | Unicode 标题支持（中文 / emoji） |

---

## 5. 数据结构

### 5.1 `BookmarkNode`

```python
from dataclasses import dataclass, field

@dataclass
class BookmarkNode:
    title: str
    page: int | None          # 1-based；None 表示异常
    line_no: int              # 源文件行号（1-based），用于错误定位
    children: list["BookmarkNode"] = field(default_factory=list)
```

**不变量**：
- `title` 始终为非空字符串（标题缺失会抛 `ParseError`）
- `page` 为 `None` 或 `>= 1` 的整数
- `children` 列表保持源文件中的顺序

### 5.2 `ParseRule`

```python
from typing import Literal

@dataclass(frozen=True)
class ParseRule:
    name: str
    line_pattern: str                                  # 正则字符串
    level_mode: Literal["flat", "indent", "md_header"] = "flat"
    indent_spaces: int = 2                             # 仅 indent 模式
```

**约束**：
- `line_pattern` 必须包含命名组 `title`、`page`
- `level_mode == "indent"` 时正则应可选包含 `indent` 命名组
- `level_mode == "md_header"` 时正则应包含 `hashes` 命名组

---

## 6. 接口契约（API）

### 6.1 `parser.Parser`

```python
class Parser:
    BUILTIN_RULES: dict[str, ParseRule]   # 6 个内置模板

    def __init__(self, rule: ParseRule) -> None: ...

    def parse(self, text: str) -> list[BookmarkNode]:
        """
        解析文本，返回顶层书签节点列表。
        Raises:
            ParseError: 标题缺失或正则错误
        """

    def parse_file(self, path: Path) -> list[BookmarkNode]:
        """便捷方法：读取文件后 parse()。"""
```

**异常**：
```python
class ParseError(Exception):
    line_no: int
    content: str
    reason: str
```

### 6.2 `bookmark.mount_bookmarks`

```python
from typing import Callable, Literal
from pathlib import Path

def mount_bookmarks(
    pdf_path: Path,
    nodes: list[BookmarkNode],
    output_path: Path,
    *,
    mode: Literal["replace", "append", "merge"] = "replace",
    page_offset: int = -1,                                  # 默认 1-based → 0-based
    on_progress: Callable[[int, int], None] | None = None,  # (current, total)
) -> None:
    """
    将书签节点挂载到 PDF。
    Raises:
        PageOutOfRangeError: 页码越界
        PdfReadError: PDF 读取失败
        OSError: 文件写入失败
    """
```

**异常**：
```python
class PageOutOfRangeError(Exception):
    line_no: int
    page: int
    page_count: int
```

### 6.3 `app.BookmarkApp`（GUI）

```python
import tkinter as tk

class BookmarkApp(tk.Tk):
    def __init__(self) -> None: ...
    def run(self) -> None: ...
```

GUI 调用 `Parser` 与 `mount_bookmarks`，所有耗时操作在 `threading.Thread` 中执行，通过 `queue.Queue` 与主线程通信。

### 6.4 `bookmark.read_bookmarks`（v1.2 新增）

```python
from pathlib import Path
from bookmark_pdf.parser import BookmarkNode

def read_bookmarks(pdf_path: Path) -> list[BookmarkNode]:
    """
    读取 PDF 现有 outline，返回顶层 BookmarkNode 列表。

    - 页码：1-based（与 parser 一致）
    - 嵌套：递归处理 pypdf 的 nested-list 结构
    - 异常页：page=None 而非抛错
    - line_no：按 DFS 顺序分配
    - 无 outline：返回 []

    Raises:
        FileNotFoundError: PDF 不存在
        pypdf.errors.PdfReadError: PDF 损坏 / 加密
    """
```

### 6.5 `parser.to_indent_dot`（v1.1 新增）

```python
def to_indent_dot(nodes: list[BookmarkNode], *, indent_spaces: int = 2) -> str:
    """将 BookmarkNode 树序列化为 indent-dot 格式文本。
    输出可被 BUILTIN_RULES["indent-dot"] 重新解析（round-trip）。"""
```

### 6.6 `bookmark.save_bookmarks_txt`（v1.1 新增）

```python
def save_bookmarks_txt(
    nodes: list[BookmarkNode],
    output_path: Path,
    *,
    indent_spaces: int = 2,
) -> Path:
    """保存为 indent-dot 格式 TXT，返回写入路径。"""
```

### 6.7 GUI「书签文本」section（v1.2 新增）

GUI 在「1. 选择文件」与「3. 解析规则」之间新增「2. 书签文本（可编辑）」section：

| 控件 | 行为 |
|------|------|
| `Text` 多行编辑区 | indent-dot 格式，高度 8 行，自动横向滚动 |
| `📥 从 PDF 读取书签` 按钮 | 调用 `read_bookmarks(pdf_path)` → `to_indent_dot` → 填入文本区 |
| `🔄 解析文本` 按钮 | 用 `BUILTIN_RULES["indent-dot"]` 解析当前文本 → `_last_nodes` → 刷新 Treeview |
| `页码 +/- Spinbox` + `应用` 按钮 | 调用 `shift_pages(nodes, offset)` |
| `🔧 工具 ▼` 按钮 | 弹 `Toplevel` 工具弹窗（见 §6.8） |
| `📋 清空` 按钮 | 清空文本、`_last_nodes`、Treeview |
| `💾 导出 TXT` 按钮 | 写入 `_source_path`（若为 .txt/.md）或弹窗另存为 |

**自动解析**：Text `<KeyRelease>` 事件触发 500ms 节流 → 自动调用 `_do_parse_text(silent=True)`。

**双向同步**：
- 解析成功后调用 `_sync_text_from_nodes(nodes)` → 仅在文本区为空或未脏时覆盖
- 解析失败不清空已有 `_last_nodes`（避免误丢用户工作）

### 6.7.1 在线获取后保存弹框（v1.3 新增）

| 触发 | 时机 | 行为 |
|------|------|------|
| `_poll_fetch` 处理 `"ok"` 分支后 | 调 `self.after(0, ...)` 调度 | 弹 `messagebox.askyesno("是否保存书签", ...)` |

`_prompt_save_after_fetch(meta)`：
1. 若 `_last_nodes` 为空 → 直接返回
2. `askyesno` 询问「已获取《{title}》的书签。是否保存为 TXT 文件？」
3. 选「否」→ 返回
4. 选「是」→ `filedialog.askdirectory(title="选择保存文件夹", mustexist=True)`
5. 取消文件夹 → 返回
6. 默认文件名 = `_suggest_default_filename()`（见 §6.7.2）
7. `save_bookmarks_txt(self._last_nodes, target)` → 写入
8. 日志 + 状态栏 + `messagebox.showinfo("完成", ...)`

**为何用 `after(0, ...)`**：避免在 `_poll_fetch` 主循环里阻塞 messagebox 模态循环。

### 6.7.2 文件名工具（v1.3 新增）

```python
from bookmark_pdf.app import BookmarkApp

@staticmethod
def _sanitize_filename(name: str, max_len: int = 80) -> str:
    """替换 OS 非法字符为单空格，折叠空白，截断到 max_len 字符。
    结果为空时回退到 'bookmarks'。"""

def _suggest_default_filename(self) -> str:
    """生成默认 .txt 文件名。优先级：
        1. _book_meta.title (sanitize)
        2. _book_meta.ssid (sanitize)
        3. _source_path.stem (sanitize)
        4. 'bookmarks'
    若 sanitize 结果已以 'bookmarks' 结尾（不区分大小写），不再追加 '_bookmarks'。
    """
```

**非法字符集**：`\ / : * ? " < > |` 以及 `\r \n \t`。

**使用位置**：
- `_prompt_save_after_fetch` → 用户选文件夹后的默认文件名
- `_do_export_txt` → Save As 弹窗的 `initialfile`（与 `_book_meta` 联动；书签源后缀为 `.txt/.md` 时仍走原路径）

### 6.7.3 书签源可为空（v1.3 行为）

- `_do_mount` 仅校验 `_last_nodes` 与 PDF 路径，不校验 `_source_path`
- `_update_run_button`：`ok = bool(self._last_nodes) and bool(self._pdf_path)`
- 在线获取成功后 `_last_nodes` 已被填充 → 「⚙ 执行挂载」自动启用
- 「0. 在线获取」区显示 hint：`提示：获取后可点「⚙ 执行挂载」直接挂到 PDF，无需先选书签源文件。`

### 6.8 `transforms` 模块（v1.4 新增）

```python
from bookmark_pdf.transforms import (
    shift_pages, normalize_pages, cap_pages,
    sort_by_page, remove_duplicates, remove_invalid_pages,
    trim_titles, flatten,
)

Transform = Callable[[list[BookmarkNode]], list[BookmarkNode]]

# 每个函数都是纯函数：输入 list[BookmarkNode] → 返回新 list[BookmarkNode]
def shift_pages(nodes, offset: int) -> list[BookmarkNode]
def normalize_pages(nodes, start: int = 1) -> list[BookmarkNode]
def cap_pages(nodes, max_page: int) -> list[BookmarkNode]
def sort_by_page(nodes, descending: bool = False) -> list[BookmarkNode]
def remove_duplicates(nodes) -> list[BookmarkNode]
def remove_invalid_pages(nodes) -> list[BookmarkNode]
def trim_titles(nodes) -> list[BookmarkNode]
def flatten(nodes) -> list[BookmarkNode]
```

**约定**：
- 输入不修改（创建新节点）
- `page=None` 不被丢弃（除非 `remove_invalid_pages`）
- 嵌套递归处理
- 可独立使用（CLI、脚本）

**GUI 工具弹窗**：4 分组（页码 / 清理 / 文本 / 树形）共 8 个工具，点击「执行」调用 `_apply_transform` 抽象方法。

---

## 7. 错误处理矩阵

| 场景 | 检测时机 | 处理 |
|------|----------|------|
| TXT/MD 文件不存在 | GUI 选择文件时 | 提示「文件不存在」 |
| PDF 文件不存在 | GUI 选择文件时 | 提示「文件不存在」 |
| 正则无 `title` / `page` 命名组 | 解析时 | 抛 `ParseError(reason="missing_named_group")` |
| 标题为空 | 解析时 | 抛 `ParseError(reason="empty_title")` |
| 页码非数字 | 解析时 | `page=None`，预览标红，不阻断 |
| 页码越界 | 挂载时 | 抛 `PageOutOfRangeError`，GUI 弹错并阻止执行 |
| PDF 损坏 / 加密 | 挂载时 | 捕获 `PdfReadError`，GUI 友好提示 |
| 输出路径冲突 | 挂载时 | 询问覆盖 / 取消 |
| 输出目录无写权限 | 挂载时 | 捕获 `PermissionError`，提示 |

---

## 8. 测试规范

### 8.1 单元测试（`tests/`）

**`test_parser.py`**：每种模板 ≥3 用例
- 正常解析（含嵌套、Unicode）
- 空行、注释行跳过
- 页码非数字 → `page=None`
- 标题缺失 → `ParseError`
- 自定义正则（含 / 不含命名组）

**`test_bookmark.py`**：
- 3 种 mode × 单层 / 多层
- 越界页码 → `PageOutOfRangeError`
- Unicode 标题
- 进度回调被正确调用
- `page=None` 节点被跳过且日志记录

### 8.2 夹具
- `tests/fixtures/txt_*.txt`：3 个 TXT 模板样例
- `tests/fixtures/md_*.md`：3 个 MD 模板样例
- 测试 PDF：使用 `reportlab` 动态生成（无需文件夹具）

### 8.3 验收
- 所有单元测试通过
- 真实 PDF + TXT/MD 端到端跑通
- 输出 PDF 在 Preview / Adobe Reader 中书签树正确显示

---

## 9. 实现约束

1. **不引入超出 `pypdf` 之外的运行依赖**
2. **GUI 仅使用 `tkinter` + `tkinter.ttk`**，不引入 PyQt / Electron 等
3. **页面拷贝必须完整**：使用 `PdfWriter.add_page(reader.pages[i])`，不能仅修改 outline
4. **进度回调不能阻塞**：在耗时循环中调用 `on_progress(i, total)`，不传 None 时必须安全
5. **异常抛出包含上下文**：错误信息含文件名 / 行号 / 原因，便于 GUI 展示
6. **UTF-8 输入输出**：所有文本 I/O 使用 `encoding="utf-8"`
7. **dataclass 优先**：数据结构用 `@dataclass` 而非裸 dict

---

## 10. 版本演进

- **v1.0**（当前）：核心解析 + 挂载 + GUI
- **v1.1**（候选）：书签模板保存/加载（用户预设）
- **v1.2**（候选）：批量处理（多 PDF 队列）
- **v2.0**（候选）：PyInstaller 打包

---

## 11. 与 Plan 的关系

本文档（spec.md）与 `plan.md` 配套：
- **plan.md**：执行步骤、任务分解、工作量
- **spec.md**：接口契约、数据结构、错误处理（**代码必须遵循**）

实现过程中若发现 spec 不足，先更新 spec.md 再改代码。