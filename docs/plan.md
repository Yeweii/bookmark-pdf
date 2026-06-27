# Plan: TXT/MD 书签挂载到 PDF（Python + Tkinter）

> 最后更新：2026-06-27

## 1. 目标

将 **TXT** 或 **MD（Markdown）** 格式的书签文件解析为层级树，并挂载到 PDF 的 outline（书签）中，生成可跳转的导航。
提供 **Tkinter GUI**：选择源文件 → 选择解析规则 → 预览 → 执行 → 输出 PDF。

## 2. 关键决策（已确认）

| 项 | 选择 | 备注 |
|----|------|------|
| 源文件格式 | TXT + MD 双支持 | GUI 文件过滤 `.txt` / `.md` |
| 解析规则 | 用户自定义 | 提供内置模板 + 自定义正则 |
| TXT 层级策略 | 缩进 / 扁平 / 章节点引导 | 详见 §4 |
| MD 层级策略 | **按 `#` 数量直接映射**（`#`=1 级、`##`=2 级、…） | 已确认 |
| PDF 库 | **pypdf** ≥ 4.0 | 读写 outline |
| GUI 框架 | **Tkinter**（标准库 + ttk） | 零额外依赖 |
| 输出策略 | GUI 中由用户选择，默认「保存为新文件」 | `*_bookmarked.pdf` |

## 3. 技术栈

- Python ≥ 3.10
- 运行时依赖：`pypdf>=4.0`
- 开发依赖：`pytest`、`reportlab`（测试时生成 PDF 夹具）
- GUI：标准库 `tkinter` + `tkinter.ttk`

## 4. 解析模板设计

### 4.1 通用数据结构

```python
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class BookmarkNode:
    title: str
    page: int | None          # 1-based；None 表示异常，需标红
    line_no: int              # 用于错误定位
    children: list["BookmarkNode"] = field(default_factory=list)

@dataclass
class ParseRule:
    name: str
    line_pattern: str                                  # 正则；命名组：title、page、(indent 可选)
    level_mode: Literal["flat", "indent", "md_header"] = "flat"
    indent_spaces: int = 2                             # 仅 indent 模式生效
```

### 4.2 TXT 内置模板

| 模板名 | 正则 | 层级 |
|--------|------|------|
| `flat` | `^(?P<page>\d+)\s+(?P<title>.+)$` | 无层级（flat） |
| `indent-dot` | `^(?P<indent>\s*)(?P<title>.+?)\s*[.\s]+(?P<page>\d+)\s*$` | 按缩进空格数 ÷ `indent_spaces` |
| `chapter` | `^第[一二三四五六七八九十百]+章\s+(?P<title>.+?)\s+(?P<page>\d+)\s*$` | flat（按章节语义） |

### 4.3 MD 内置模板

| 模板名 | 正则 | 层级 |
|--------|------|------|
| `md-header-suffix` | `^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*[.\s…]+(?P<page>\d+)\s*$` | `#` 数量 → level |
| `md-header-comment` | `^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*<!--\s*(?P<page>\d+)\s*-->\s*$` | `#` 数量 → level |
| `md-toc-link` | `^(?P<indent>\s*)[-*]\s+\[(?P<title>[^\]]+)\]\([^)]+\)\s+(?P<page>\d+)\s*$` | 缩进 ÷ `indent_spaces` |

**MD 层级规则（`md_header` 模式）**：
- 匹配时取 `hashes` 命名组：`#` 长度 1 → level 1，依此类推
- 标题内的 `#` 不计入（只看行首）
- `#` 长度 0 或 ≥7 → 视为非标题行，跳过

### 4.4 自定义正则

- 用户在 GUI 中编辑 `line_pattern`
- 必须包含命名组 `title` 与 `page`
- `level_mode` 通过下拉框选择
- 「重新解析」按钮触发即时校验与刷新预览

### 4.5 解析行为约定

- 空行 / 注释行（`#` `//` `<!--` 开头）→ 跳过
- 页码非数字或缺失 → `BookmarkNode(page=None)`，预览中**标红**，但允许执行（生成的书签可能无法跳转）
- 标题缺失 → 抛 `ParseError(line_no, content)`
- Unicode 标题直接支持
- 解析失败抛 `ParseError`，GUI 在日志区展示

## 5. 模块设计

### 5.1 `src/parser.py` — TXT/MD 解析器

```python
class Parser:
    BUILTIN_RULES: dict[str, ParseRule]   # 上述 6 个模板

    def __init__(self, rule: ParseRule): ...
    def parse(self, text: str) -> list[BookmarkNode]: ...
    def parse_file(self, path: Path) -> list[BookmarkNode]: ...
```

异常类型：
- `ParseError(Exception)`：含 `line_no`、`content`、`reason`

### 5.2 `src/bookmark.py` — pypdf 包装

```python
def mount_bookmarks(
    pdf_path: Path,
    nodes: list[BookmarkNode],
    output_path: Path,
    *,
    mode: Literal["replace", "append", "merge"] = "replace",
    on_progress: Callable[[int, int], None] | None = None,
) -> None
```

要点：
- `PdfReader` 读入、`PdfWriter` 写出
- 遍历页面拷贝，保留原内容
- 树形调用 `writer.add_outline_item(title, page_index, parent=...)`
- 三种 mode：
  - `replace`：清空原 outline 后写入
  - `append`：保留原 outline，新书签挂到顶层
  - `merge`：按标题去重，保留 page 更可靠者
- 页码校验：`page ∈ [1, page_count]`；越界抛 `PageOutOfRangeError(line_no, page)`
- `page=None` → 跳过该节点并在日志中警告

### 5.3 `src/app.py` — Tkinter GUI

布局（ttk）：

```
┌─────────────────────────────────────────────────────┐
│ [源文件] path/to/bookmarks.txt   [浏览] 格式: TXT ▾  │
│ [PDF]    path/to/file.pdf        [浏览]             │
├─────────────────────────────────────────────────────┤
│ 解析规则: [模板 ▾]  层级: [flat/indent/md_header ▾] │
│ 正则:    [_______________________________]          │
│ 缩进空格=1层: [2]   [↻ 重新解析]                    │
├─────────────────────────────────────────────────────┤
│ 预览 (Treeview):                                    │
│  ├ 第一章 .......... 12                             │
│  │  ├ 1.1 引言 ... 3                                │
│  │  └ 1.2 背景 ... 5   ← 页码异常(标红)              │
│  └ 第二章 .......... 20                             │
│ 状态: 共 3 个顶层节点, 8 条书签, 1 条异常            │
├─────────────────────────────────────────────────────┤
│ 输出: ○ 新文件(默认)  ○ 原位覆盖                    │
│ 页码 -1 转换: ☑ (TXT/MD 页码 → PDF 0-based)        │
│ 输出路径: [auto/path/to/file_bookmarked.pdf] [浏览] │
│ [⚙ 执行挂载]                                         │
├─────────────────────────────────────────────────────┤
│ 进度: [▓▓▓▓░░░░] 60%   日志 (scrolledtext)         │
└─────────────────────────────────────────────────────┘
```

关键交互：
- 选完两个文件 → 自动解析一次
- 切换模板或修改正则 → 实时重解析并刷新预览
- 预览中页码异常条目标红（`tags = ("error",)`）
- 「执行挂载」→ 禁用按钮 → 进度回调驱动进度条 → 完成弹 `messagebox.showinfo`，附「打开输出文件夹」按钮

## 6. 项目结构

```
bookmark_pdf/
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── parser.py            # TXT + MD 解析
│   ├── bookmark.py          # pypdf 书签挂载
│   └── app.py               # Tkinter GUI 入口
├── tests/
│   ├── __init__.py
│   ├── test_parser.py       # TXT + MD 模板测试
│   ├── test_bookmark.py     # 3 种 mode + 边界
│   └── fixtures/
│       ├── txt_flat.txt
│       ├── txt_indent.txt
│       ├── txt_chapter.txt
│       ├── md_header_suffix.md
│       ├── md_header_comment.md
│       ├── md_toc_link.md
│       └── (reportlab 动态生成 PDF)
├── docs/
│   └── plan.md
└── examples/
    ├── sample_bookmarks.md
    └── sample_bookmarks.txt
```

## 7. 执行步骤（Tasks）

| ID | 任务 | 工作量 | 依赖 |
|----|------|--------|------|
| T1 | 项目脚手架：目录、`requirements*.txt`、`.gitignore`、最小入口 | 0.5h | — |
| T2 | `bookmark.py`：pypdf 包装 + 异常类型 | 1.5h | T1 |
| T3 | `bookmark.py` 单元测试（reportlab 造 PDF） | 1h | T2 |
| T4 | `parser.py`：6 种模板（3 TXT + 3 MD）+ 自定义正则 | 2h | T1 |
| T5 | `parser.py` 单元测试（TXT + MD 夹具） | 1h | T4 |
| T6 | GUI 主框架：布局、文件选择（过滤 .txt/.md）、规则下拉 | 2h | T4, T2 |
| T7 | GUI 预览面板（Treeview + 异常标红 + 状态栏） | 1h | T6 |
| T8 | GUI 执行 + 进度 + 输出策略 + 错误提示 | 1h | T6, T2 |
| T9 | 端到端联调：真实 PDF + TXT/MD 各跑一遍 | 1h | T7, T8, T3, T5 |

**总计：约 11h**

## 8. 测试策略

- **parser**：6 种模板各 ≥3 用例；空行、Unicode、异常页码、非法正则
- **bookmark**：3 种 mode × 单层/多层 × 越界页码 × Unicode 标题
- **端到端**：人工用真实 PDF 验收（Preview、Adobe Reader、Sumatra）
- **GUI**：手动验收为主

## 9. 风险与权衡

1. **pypdf outline 限制**：极复杂 PDF（加密 / 损坏 / 受 DRM 保护）可能写入失败 → 捕获 `PdfReadError` 友好提示
2. **页码语义**：TXT/MD 中的「页码」通常是印刷页码（1-based），PDF 内部索引是 0-based → GUI 提供「页码 -1」开关，默认开启
3. **大文件性能**：数百页 PDF 整本拷贝较慢 → 进度回调 + 多线程（`threading`）防 GUI 卡顿
4. **MD 嵌套列表**：若 MD 用 `1. 2. 3.` 而非 `-` 开头，`md-toc-link` 模板不覆盖 → 用户可切到自定义正则
5. **跨平台打包**：本计划暂不产出 `.exe` / `.app`，需要时用 PyInstaller 二次处理

## 10. 验收标准

- [ ] TXT 三种模板均能正确解析
- [ ] MD 三种模板均能正确解析，层级由 `#` 数量决定
- [ ] 自定义正则可正常解析并预览
- [ ] 单层 / 多层书签均能正确挂载到 PDF
- [ ] 越界页码 / 非数字页码给出明确错误并在预览中标红
- [ ] 原位覆盖与新文件两种模式均工作
- [ ] 输出 PDF 在 Preview / Adobe Reader 中可显示书签树并正确跳转
- [ ] 单元测试全部通过
- [ ] 端到端流程跑通真实 PDF + TXT/MD 两种源

---

**下一步**：从 **T1（项目脚手架）** 开始执行。