# Plan: TXT/MD 书签挂载到 PDF（Python + Tkinter）

> 最后更新：2026-06-27

## 历史版本

- v1.0：核心解析 + 挂载 + GUI（[§1-11](#1-目标)）
- v1.1：在线书签获取接口 + 自动保存 TXT — 见 [§12](#12-增量-v11在线书签获取--自动保存-txt)
- v1.2：书签文本编辑区 — 见 [§13](#13-增量-v12书签文本编辑区)
- v1.3：在线获取 UX 增强 — 见 [§14](#14-增量-v13在线获取-ux-增强)
- **v1.4（当前增量）：书签文本编辑工具集** — 见 [§15](#15-增量-v14书签文本编辑工具集)
- 详细 proposal：[`proposal-bookmark-tools.md`](proposal-bookmark-tools.md)

---

## 14. 增量 v1.3：在线获取 UX 增强

### 14.1 目标

围绕"在线获取 → 直接挂载"流程做最小 UX 增强：

1. **不弹保存对话框**（v1.3 暂不做）：用户可通过现有的「💾 导出 TXT」按钮主动保存
2. **加提示让用户知道可直接挂载**：「0. 在线获取」区增加 hint 标签
3. **改进默认文件名**：当 `_source_path` 为空但 `_book_meta` 存在（即来自在线获取），`askdirectory` / `asksaveasfilename` 默认文件名用 `<title>_bookmarks.txt`

详细需求与方案对比见 [`proposal-save-after-fetch.md`](proposal-save-after-fetch.md)。

### 14.2 已确认决策

| 项 | 选择 |
|----|------|
| 弹框触发 | **v1.3 暂不做**（用户决定） |
| 默认文件名 | sanitize 后的 `<title>_bookmarks.txt`；空则用 SSID |
| 书签源为空 | **不改校验**，仅在「0. 在线获取」加 hint 提示 |
| 改动范围 | 仅 GUI 与 sanitize 工具函数；不改 parser/bookmark/fetcher |

### 14.3 模块改动

**`bookmark_pdf/app.py` 新增**：

```python
import re  # 用于 sanitize 正则

# 在 BookmarkApp 类内
@staticmethod
def _sanitize_filename(name: str, max_len: int = 80) -> str:
    """Sanitize a string for use as a filename (跨平台安全)。"""
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t]', ' ', name)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip()
    return cleaned or "bookmarks"

def _suggest_default_filename(self) -> str:
    """根据当前来源建议默认书签文件名。
    
    优先级：在线获取（_book_meta.title）> 书签源文件名 stem > 'bookmarks'
    """
    if self._book_meta is not None:
        base = (self._book_meta.title or "").strip() or self._book_meta.ssid
    else:
        source = self._source_path.get().strip()
        base = Path(source).stem if source else "bookmarks"
    return self._sanitize_filename(base) + "_bookmarks.txt"
```

**`bookmark_pdf/app.py` 修改**：

1. `_build_fetch_section` 加 hint：
```python
ttk.Label(
    frame,
    text="提示：获取后可直接点「⚙ 执行挂载」，无需先选书签源文件。",
    foreground="#888",
).grid(row=1, column=1, columnspan=3, sticky=tk.W, padx=4)
```
（已有类似灰色 hint，扩展一条即可）

2. `_do_export_txt` 改用 `_suggest_default_filename`：
```python
def _do_export_txt(self) -> None:
    content = self._get_text_content()
    if not content.strip():
        messagebox.showwarning("提示", "文本为空，无可导出内容")
        return
    source = self._source_path.get().strip()
    suggested = self._suggest_default_filename()
    if source and Path(source).suffix.lower() in (".txt", ".md"):
        out = Path(source)
    else:
        out = Path(filedialog.asksaveasfilename(
            title="导出书签为 TXT",
            defaultextension=".txt",
            initialfile=suggested,         # 新增
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        ))
        if not out:
            return
    try:
        out.write_text(content, encoding="utf-8")
    except OSError as e:
        messagebox.showerror("导出失败", str(e))
        return
    self._log_append(f"✓ 已导出书签: {out}")
    self._set_status(f"已导出: {out.name}")
```

### 14.4 GUI 改动

只改「0. 在线获取」区增加一行 hint：

```
0. 在线获取（可选）                                  ← 已存在
   SSID: [____]  [🌐 获取书签]  ✓ 已获取... 
   (从 api.pdfshuwu.com 拉取目录；成功后自动填入下方预览)   ← 已存在
   提示：获取后可直接点「⚙ 执行挂载」，无需先选书签源文件。  ← 新增
```

### 14.5 错误处理

| 场景 | 处理 |
|------|------|
| `_book_meta.title` 为空字符串 | 用 `_book_meta.ssid` 兜底 |
| sanitize 后仍为空（极端情况） | 用 `"bookmarks"` 兜底 |
| 导出对话框用户取消 | 无错误，不保存 |
| 写入失败 | `messagebox.showerror` |

### 14.6 测试策略

**单元测试 `tests/test_export_filename.py` 新增**：

- `test_sanitize_filename_removes_illegal_chars`：跨平台非法字符 `/\\:*?"<>|`
- `test_sanitize_filename_collapses_whitespace`
- `test_sanitize_filename_truncates`
- `test_sanitize_filename_empty_falls_back_to_bookmarks`
- `test_suggest_default_filename_uses_book_meta_title`（mock `_book_meta`）
- `test_suggest_default_filename_falls_back_to_ssid`
- `test_suggest_default_filename_uses_source_path_stem`
- `test_suggest_default_filename_no_source_uses_bookmarks`

**手动验收**：

- 在线获取后点「💾 导出 TXT」→ Save As 弹窗默认名为 `<书名>_bookmarks.txt`
- 文件名含 `/` 等非法字符时 sanitize 生效
- 「0. 在线获取」区 hint 显示
- 在线获取后不选书签源，直接挂载仍可用（已支持）

### 14.7 执行任务（v1.3 增量）

| ID | 任务 | 工作量 | 依赖 |
|----|------|--------|------|
| #25 | `_sanitize_filename` + `_suggest_default_filename` 实现 + 单测 | 0.5h | — |
| #26 | `_build_fetch_section` 加 hint + `_do_export_txt` 改用 suggested | 0.3h | #25 |
| #27 | README + spec 更新 + commit | 0.3h | #26 |

**v1.3 总计：约 1.1h**

### 14.8 验收标准

- [ ] `_sanitize_filename` 处理非法字符、连续空白、长度截断、空字符串
- [ ] `_suggest_default_filename` 在不同来源下返回正确默认名
- [ ] 「0. 在线获取」区显示 hint 标签
- [ ] 在线获取后点「💾 导出 TXT」→ 默认名为 `<书名>_bookmarks.txt`
- [ ] 81 个旧测试 + 新增单元测试全部通过
- [ ] GUI 启动正常，挂载流程不受影响

### 14.9 风险

| 风险 | 缓解 |
|------|------|
| 用户期望弹框但未实现 | 在 commit message 中说明 "v1.3 仅做 UX 增强，弹框留待后续" |
| sanitize 边界情况 | 单元测试覆盖；兜底用 `bookmarks` |

---

## 13. 增量 v1.2：书签文本编辑区

### 13.1 目标

新增「书签文本（可编辑）」section，作为书签的**直接编辑入口**：

1. **读 PDF 书签 → 显示 → 编辑 → 挂回**：把 PDF 现有 outline 转成 `indent-dot` 文本填入编辑区，用户编辑后挂载
2. **外部粘贴 → 编辑 → 挂载**：从任意来源（微信、网页、PDF 阅读器）拷来的目录文本直接粘贴进来，挂载到目标 PDF
3. 现有 TXT/MD 文件输入流、SSID 在线获取、模板解析系统**全部保留**

详细需求与方案对比见 [`proposal-bookmark-text-area.md`](proposal-bookmark-text-area.md)。

### 13.2 已确认决策

| 项 | 选择 |
|----|------|
| 文本区位置 | 独立 section，位于「1. 选择文件」与「2. 解析规则」之间 |
| 文本格式 | `indent-dot`（`Title ...... Page`）— 复用 `to_indent_dot` 序列化 |
| 读取 PDF 书签触发 | 显式按钮「📥 从 PDF 读取书签」 |
| 来源并存 | 4 种来源并存（TXT/MD / SSID / PDF 已有 / 外部粘贴），统一汇入 `_last_nodes` |
| 文本 → 节点触发 | 显式「🔄 解析文本」按钮 + 编辑停止 500ms 后自动解析 |
| 现有 v1.1 自动保存 TXT | 不变，仍按 `_last_nodes` 保存 |

### 13.3 数据流

```
┌──────────────────────────────────────────────────────────────────┐
│ 书签源（4 路并存）：                                                │
│   ① TXT/MD 文件 ───┐                                             │
│   ② 在线 SSID  ────┼──► _last_nodes (list[BookmarkNode])         │
│   ③ PDF 已有书签 ──┤     ▲                                       │
│   ④ 外部粘贴文本 ──┘     │                                       │
│                          │                                       │
│   ┌──────────────┐        │                                       │
│   │ Treeview 预览 │◄───────┘                                       │
│   └──────────────┘                                                │
│          ▲                                                        │
│   ┌──────────────┐                                                │
│   │ 文本编辑区    │ to_indent_dot(_last_nodes) ← 用户编辑          │
│   │ (indent-dot) │ Parser.parse(text) → _last_nodes              │
│   └──────────────┘                                                │
└──────────────────────────────────────────────────────────────────┘
```

### 13.4 模块改动

**`bookmark_pdf/bookmark.py` 新增**：

```python
def read_bookmarks(pdf_path: Path) -> list[BookmarkNode]:
    """Read existing outline from PDF → list[BookmarkNode].

    - 递归遍历 reader.outline（处理嵌套 list）
    - PDF page index 0-based → 节点 page 1-based
    - 无法解析页的项 page=None
    - line_no 按 DFS 顺序分配
    """
```

**`bookmark_pdf/app.py` 改造**：

- 新增 `_build_text_section()` 在「1. 选择文件」与「2. 解析规则」之间
- 文本控件：`tk.Text(height=8, wrap=tk.WORD)` + Scrollbar
- 四个按钮：
  - `📥 从 PDF 读取书签` → `_do_read_pdf()` → `read_bookmarks` → `to_indent_dot` → 填入 Text
  - `🔄 解析文本` → `_do_parse_text()` → Text → `Parser.parse()` → `_last_nodes` → 刷新 Treeview
  - `📋 清空` → 清空 Text + `_last_nodes` + Treeview
  - `💾 导出 TXT` → Text 内容写入 `_source_path`（或弹窗另存为）
- 同步逻辑：
  - `_do_parse()`（文件输入）成功后调用 `_sync_text_from_nodes(nodes)`
  - `_do_fetch()`（SSID）成功后调用 `_sync_text_from_nodes(nodes)`
  - `_do_read_pdf()` 成功后 `_sync_text_from_nodes(nodes)`
- 自动解析：`Text` 控件 `<KeyRelease>` + 500ms `after` 节流 → 自动调用 `_do_parse_text()`

### 13.5 GUI 新布局（v1.2）

```
0. 在线获取（SSID → 一键拉取目录）
1. 选择文件（书签源 + PDF）           ← 不变
3. 书签文本（可编辑）                  ← 新增
   ├ 多行 Text 控件（indent-dot）
   └ [📥 从 PDF 读取书签] [🔄 解析文本] [📋 清空] [💾 导出TXT]
2. 解析规则（模板 + 自定义正则）       ← 改编号为 2（原 2 → 2）
4. 预览（树形结构，页码异常标红）      ← 改编号为 4
5. 输出选项                           ← 改编号为 5
6. 进度与日志                         ← 改编号为 6
```

### 13.6 错误处理

| 场景 | 处理 |
|------|------|
| 文本区为空 | 「🔄 解析文本」按钮置灰；「执行挂载」已有防护 |
| 文本格式无法解析 | `messagebox.showerror`，列出错误行号；**不清空**已有 `_last_nodes` |
| 选择 PDF 后无 outline | `messagebox.showinfo`「该 PDF 没有书签」；Text 仍可手动编辑 |
| PDF 加密/损坏 | `messagebox.showerror`「PDF 读取失败」 |
| 文本区编辑后未解析就点挂载 | 仍按当前 `_last_nodes` 挂载（避免误挂脏数据） |
| 文本区编辑后切换模板 | 不自动重新解析，下次点「🔄 解析文本」时按当前规则 |

### 13.7 测试策略

**单元测试 `tests/test_bookmark.py` 新增**：

- `test_read_bookmarks_with_outline`：reportlab 造带 outline 的 PDF → 验证节点结构
- `test_read_bookmarks_no_outline`：无书签 PDF → 返回空列表
- `test_read_bookmarks_nested`：多层 outline → 正确建立 children
- `test_read_bookmarks_invalid_page`：某项指向不存在的页 → `page=None`
- `test_read_bookmarks_round_trip`：`read_bookmarks(pdf)` → `to_indent_dot(...)` → `Parser.parse(...)` → 结构等价

**GUI 手动验收**：

- 粘贴外部文本 → 解析 → Treeview 显示 → 挂载
- 选带书签 PDF → 「📥 读取」 → 文本区显示 → 编辑一行 → 解析 → 挂载
- 在线 SSID → 拉到预览 → 切到文本区 → 改一行 → 解析 → 挂载

### 13.8 执行任务（v1.2 增量）

| ID | 任务 | 工作量 | 依赖 |
|----|------|--------|------|
| #21 | `read_bookmarks` 实现 + 单测 + round-trip | 1h | parser, bookmark |
| #22 | GUI 新增「书签文本」section + 4 按钮 | 1.5h | #21 |
| #23 | 文本 ↔ Treeview 同步逻辑 + 自动解析节流 | 0.5h | #22 |
| #24 | 端到端 + README/spec 更新 + commit/push | 0.5h | #23 |

**v1.2 总计：约 3.5h**

### 13.9 验收标准

- [ ] PDF 有书签时「📥 读取」正确填充文本区
- [ ] PDF 无书签时不崩溃，友好提示
- [ ] 外部粘贴文本 → 解析 → Treeview 显示 → 挂载链路通
- [ ] 文本区编辑 → 解析 → 挂载链路通
- [ ] 现有 TXT/MD 文件输入流仍可用
- [ ] 现有 SSID 在线获取仍可用
- [ ] 文本区与 Treeview 双向同步
- [ ] 51 个旧测试仍全部通过
- [ ] 新增 `read_bookmarks` 测试通过
- [ ] round-trip 测试通过
- [ ] README 补充「书签文本区」用法说明

### 13.10 风险

| 风险 | 缓解 |
|------|------|
| 文本区与 Treeview 不同步导致挂错内容 | 解析后同步；状态栏始终显示当前节点数 |
| PDF outline 解析异常 | 复用 `_walk` 思路；异常页设 `page=None` 而非崩溃 |
| 占用屏幕高度 | 6 段变 7 段，可滚动容器或降低每段高度 |

---

## 12. 增量 v1.1：在线书签获取 + 自动保存 TXT

### 12.1 目标

在现有 `bookmark_pdf` 工具中新增：

1. **在线书签获取**：从 `api.pdfshuwu.com` 按 `ssid` 拉取目录结构并填充到预览区
2. **挂载后自动保存 TXT**：执行挂载成功后，把当前书签树以 `indent-dot` 格式写入 `<pdf>_bookmarks.txt`

### 12.2 已确认决策

| 项 | 选择 |
|----|------|
| API URL | `https://api.pdfshuwu.com/api/front/duxiu/info?ssid={ssid}` |
| 输入参数 | `ssid`（字符串） |
| 层级映射 | API 返回的 `i` 字段直接作为层级（0=顶层，1-3=嵌套） |
| TXT 保存 | 每次挂载成功后自动保存，与 PDF 同目录，文件名 `<原名>_bookmarks.txt` |
| GUI 集成 | 主区域顶部新增「在线获取」区（SSID 输入 + 按钮 + loading 状态） |

### 12.3 API 响应结构（已实测）

```json
{
  "code": "200",
  "message": "成功",
  "data": {
    "dxSsid": "13284383",
    "dxTitle": "国朝闺秀诗柳絮集校补  1",
    "dxAuthor": "（清）黄秩模编辑；付琼校补",
    "dxPage": "410",
    "dxDirectory": [
      { "p": 1, "c": "前言&付琼", "i": 0 },
      { "p": 1, "c": "卷一", "i": 0 },
      { "p": 1, "c": "一东", "i": 1 },
      { "p": 1, "c": "童凤  四首", "i": 2 },
      { "p": 3, "c": "寒食舟中感怀", "i": 3 }
    ]
  }
}
```

### 12.4 模块设计

**新增 `src/fetcher.py`**：
```python
@dataclass
class BookMeta:
    ssid: str; dxid: str; isbn: str
    title: str; author: str; publish: str
    publish_time: str; total_pages: int | None

class FetchError(Exception): ...

def fetch_bookmarks(ssid, *, api_url=..., timeout=30.0) -> tuple[BookMeta, list[BookmarkNode]]:
    """拉取书目元数据 + 目录树。
    
    使用 urllib.request 零依赖，按 i 字段建树（复用 parser 的 _build_tree 思路）。
    """
```

**`src/parser.py` 新增序列化函数**：
```python
def to_indent_dot(nodes: list[BookmarkNode], *, indent_spaces: int = 2) -> str:
    """序列化为 indent-dot 格式文本。"""
```

**`src/bookmark.py` 新增保存函数**：
```python
def save_bookmarks_txt(nodes, output_path, *, indent_spaces=2) -> Path:
    """保存为 TXT，返回写入路径。"""
```

**GUI 改造 (`src/app.py`)**：
- 顶部新增 section「0. 在线获取」（SSID 输入 + 按钮 + 状态）
- `_mount_worker` 成功后调用 `save_bookmarks_txt` 写 `<pdf>_bookmarks.txt`
- 日志追加「✓ 已保存书签文件」

### 12.5 错误处理

| 场景 | 处理 |
|------|------|
| 网络失败 | `FetchError` + GUI 弹窗 + 状态栏 |
| 非 200 响应 | `FetchError` + 显示 API message |
| 空目录 | `FetchError` + 「该 SSID 无目录数据」 |
| 空 SSID | GUI 层校验禁止提交 |
| TXT 写入失败 | 日志提示，不阻断挂载结果 |

### 12.6 测试策略

- **`test_fetcher.py`**：用 `unittest.mock` 模拟 HTTP（避免网络依赖）
  - 成功 / HTTP 错误 / 超时 / JSON 失败 / 空目录
- **`test_parser.py` 新增**：to_indent_dot、round-trip
- **`test_bookmark.py` 新增**：save_bookmarks_txt 写入验证

### 12.7 执行任务（v1.1 增量）

| ID | 任务 | 工作量 | 依赖 |
|----|------|--------|------|
| #18 | `fetcher.py` + 单测（mock HTTP） | 1.5h | parser |
| #19 | `to_indent_dot` + `save_bookmarks_txt` + 单测 | 1h | parser |
| #17 | GUI 新增「在线获取」区 + 挂载后自动保存 | 1.5h | #18, #19 |
| #20 | 端到端 + README/spec 更新 + commit/push | 0.5h | #17 |

**v1.1 总计：约 4.5h**

### 12.8 验收标准

- [ ] 合法 SSID 填充预览区
- [ ] API 异常不崩溃，友好提示
- [ ] 挂载成功自动生成 `<pdf>_bookmarks.txt`
- [ ] TXT 可被 `indent-dot` 重新解析（round-trip）
- [ ] 51 个旧测试全部通过
- [ ] 新增 fetcher / serializer 测试通过

### 12.9 风险

1. **API 变更**：第三方 API 可能改格式 → 错误信息含原始响应便于排查
2. **网络超时**：默认 30s + 后台线程不卡顿
3. **依赖**：复用 `urllib`，零新增依赖

---

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

---

## 15. 增量 v1.4：书签文本编辑工具集

### 15.1 目标

为「2. 书签文本（可编辑）」section 新增**批量编辑工具集**，覆盖最常见操作：

1. **页码批量偏移**（用户明确要求）：所有页码 +/- N
2. **其他实用工具**：归一化、裁剪、去重、Trim、展平、按页排序、移除异常页等

详细需求与方案对比见 [`proposal-bookmark-tools.md`](proposal-bookmark-tools.md)。

### 15.2 已确认决策

| 项 | 选择 |
|----|------|
| 工具范围 | P0+P1（8 个工具） |
| 页码 +/- 交互 | 主工具栏 Spinbox + 「应用」按钮 |
| 工具入口 | 主工具栏（页码 +/-）+ 🔧 工具弹窗（其余 7 个） |
| 新增模块 | `bookmark_pdf/transforms.py`（纯函数模块） |
| 改动范围 | GUI + 新增 transforms 模块；不动 parser/bookmark/fetcher |

### 15.3 模块改动

**新增 `bookmark_pdf/transforms.py`**：每个工具为纯函数

```python
Transform = Callable[[list[BookmarkNode]], list[BookmarkNode]]

def shift_pages(nodes, offset: int) -> list[BookmarkNode]:
    """所有页码 +/- offset；page=None 不变。"""

def normalize_pages(nodes, start: int = 1) -> list[BookmarkNode]:
    """按 DFS 顺序从 start 重新编号。"""

def cap_pages(nodes, max_page: int) -> list[BookmarkNode]:
    """超过 max_page 的设为 None。"""

def sort_by_page(nodes, descending: bool = False) -> list[BookmarkNode]:
    """按页码排序；page=None 排末尾。"""

def remove_duplicates(nodes) -> list[BookmarkNode]:
    """(title, page) 重复的去重，保留首次。"""

def remove_invalid_pages(nodes) -> list[BookmarkNode]:
    """移除 page=None 的条目（递归）。"""

def trim_titles(nodes) -> list[BookmarkNode]:
    """标题首尾去空白。"""

def flatten(nodes) -> list[BookmarkNode]:
    """移除所有层级，DFS 展平到顶层。"""
```

### 15.4 GUI 改动

**主工具栏**（在 `_build_text_section` 内）：

```
[📥 从 PDF 读取书签] [🔄 解析文本] [页码 +/- [N] [应用]] [🔧 工具 ▼] [📋 清空] [💾 导出 TXT]
```

**新增 `_open_tools_window`**：弹 `Toplevel` 工具弹窗，列出其余 7 个工具：

| 分组 | 工具 |
|------|------|
| 页码 | 归一化、裁剪到最大页 |
| 清理 | 去重、移除异常页 |
| 文本 | Trim 标题 |
| 树形 | 展平、按页码升/降序 |

**新增 `_apply_transform(transform)` 抽象方法**：
```python
def _apply_transform(self, transform: Transform, label: str = "") -> None:
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
    self._log_append(f"✓ 已应用工具: {label or transform.__name__}")
```

### 15.5 错误处理

| 场景 | 处理 |
|------|------|
| `_last_nodes` 为空 | 提示先解析 |
| transform 抛错 | messagebox.showerror |
| 工具参数非法 | 输入校验（如 `max_page >= 1`） |

### 15.6 测试策略

**单元测试 `tests/test_transforms.py` 新增**：

每个 transform ≥ 2 用例（含嵌套）：

- `shift_pages` /  `shift_pages_with_none` / `shift_pages_nested`
- `normalize_pages` / `normalize_pages_with_start_5`
- `cap_pages` / `cap_pages_nested`
- `sort_by_page_asc` / `sort_by_page_desc` / `sort_by_page_with_none`
- `remove_duplicates` / `remove_duplicates_nested`
- `remove_invalid_pages` / `remove_invalid_pages_keeps_children`
- `trim_titles` / `trim_titles_nested`
- `flatten` / `flatten_already_flat`

**Round-trip**：除归一化/排序/裁剪外，`to_indent_dot(transform(parse(text)))` 应结构等价。

**GUI 手动验收**：

- 输入文本 → Spinbox +5 → 应用 → 文本 +5 且预览刷新
- 🔧 工具 → 选「归一化」→ 文本从 1 开始重新编号
- 🔧 工具 → 选「按页码降序」→ 文本顺序改变
- 任何工具执行后，点「⚙ 执行挂载」仍可用

### 15.7 执行任务（v1.4 增量）

| ID | 任务 | 工作量 | 依赖 |
|----|------|--------|------|
| #28 | `transforms.py` 模块（8 个 P0+P1 函数）+ 单测 | 1.5h | — |
| #29 | GUI：页码 Spinbox + 应用按钮 + `_do_shift_pages` | 0.5h | #28 |
| #30 | GUI：🔧 工具弹窗 + `_open_tools_window` + 7 个工具接线 | 1.0h | #28 |
| #31 | `_apply_transform` 抽象 + README + spec + commit | 0.5h | #29, #30 |

**v1.4 总计：约 3.5h**

### 15.8 验收标准

- [ ] 8 个 transform 函数全部实现并通过单测
- [ ] 主工具栏页码 +/- Spinbox 工作
- [ ] 🔧 工具弹窗列出其余 7 个工具并可执行
- [ ] 执行 transform 后文本、预览、_last_nodes 三者同步
- [ ] 81 个旧测试 + 新增 transforms 测试全部通过
- [ ] README 补充「书签文本工具」用法
- [ ] GUI 启动 < 1s

### 15.9 风险

| 风险 | 缓解 |
|------|------|
| 工具按钮挤占 UI | 仅页码 +/- 直接显示；其余放弹窗 |
| transform 误删数据 | round-trip 测试覆盖；日志记录每次执行 |
| 大量工具发现性 | 弹窗分类展示，命名清晰 |

---

## 16. 未来扩展（不在 v1.4）

- transform 撤销栈（v1.5）
- P2 工具：prefix_titles / remove_titles_matching / fix_negative_pages
- 正则批量编辑（v1.5）
- [ ] 越界页码 / 非数字页码给出明确错误并在预览中标红
- [ ] 原位覆盖与新文件两种模式均工作
- [ ] 输出 PDF 在 Preview / Adobe Reader 中可显示书签树并正确跳转
- [ ] 单元测试全部通过
- [ ] 端到端流程跑通真实 PDF + TXT/MD 两种源

---

**下一步**：从 **T1（项目脚手架）** 开始执行。