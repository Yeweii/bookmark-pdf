# Tasks: TXT/MD 书签挂载到 PDF

> 与 `plan.md` / `spec.md` 配套的执行任务清单
> 日期：2026-06-27

## 进度总览

| 状态 | 数量 |
|------|------|
| ⬜ Pending | 7 |
| 🟡 In Progress | 1 |
| ✅ Completed | 0 |

**总计**：8 个任务 · 约 11 小时

---

## 🟢 P0 · 基础

### #1 · 项目脚手架与依赖（⏳ In Progress）
- **工作量**：0.5h
- **依赖**：—
- **产出**：
  - `src/__init__.py`、`tests/__init__.py`
  - `requirements.txt`：`pypdf>=4.0`
  - `requirements-dev.txt`：`pytest`, `reportlab`
  - `.gitignore`
  - 最小入口验证 `import pypdf; import tkinter` 通过

---

## 🟡 P1 · 核心模块

### #5 · TXT/MD 解析器 parser.py（TDD）
- **工作量**：2h
- **依赖**：#1
- **产出**：
  - `src/parser.py`：`ParseRule`、`BookmarkNode`、`Parser`、`ParseError`
  - 6 个内置模板：3 TXT（`flat` / `indent-dot` / `chapter`）+ 3 MD（`md-header-suffix` / `md-header-comment` / `md-toc-link`）
  - 三种 `level_mode`：`flat` / `indent` / `md_header`
  - 自定义正则校验（必须含 `title`、`page` 命名组）

### #2 · pypdf 书签挂载 bookmark.py
- **工作量**：1.5h
- **依赖**：#1
- **产出**：
  - `src/bookmark.py`：`mount_bookmarks()`、`PageOutOfRangeError`
  - 三种 `mode`：replace / append / merge
  - `page_offset` 参数（默认 -1：1-based → 0-based）
  - `on_progress` 回调

---

## 🟠 P2 · 测试与 GUI

### #7 · bookmark 模块单元测试
- **工作量**：1h
- **依赖**：#2
- **产出**：
  - `tests/test_bookmark.py`
  - `reportlab` 动态生成测试 PDF
  - 用例：3 mode × 单层/多层 × 越界 × Unicode × 进度回调

### #4 · Tkinter GUI 主框架
- **工作量**：2h
- **依赖**：#5, #2
- **产出**：
  - `src/app.py`：`BookmarkApp(tk.Tk)` 入口
  - 布局：文件选择区 / 规则区 / 预览区 / 输出区 / 进度区
  - 文件选择 dialog 过滤 `.txt` / `.md`

### #9 · MD 测试夹具与 GUI 文件过滤
- **工作量**：1h
- **依赖**：#5
- **产出**：
  - `tests/fixtures/md_header_suffix.md`、`md_header_comment.md`、`md_toc_link.md`
  - `test_parser.py` 新增 MD 用例
  - GUI 文件选择 dialog 过滤 `.txt` / `.md`（与 #4 部分重叠，验收时统一校验）

---

## 🔴 P3 · 收尾

### #8 · 解析规则编辑器与实时预览
- **工作量**：1h
- **依赖**：#4
- **产出**：
  - 模板下拉 + 层级模式下拉 + 正则输入框
  - 「重新解析」按钮
  - Treeview 预览，异常条目标红 `tags=("error",)`
  - 状态栏：节点计数 + 异常计数

### #6 · 输出选项与执行逻辑
- **工作量**：1h
- **依赖**：#4, #2
- **产出**：
  - 单选：新文件（默认） / 原位覆盖
  - 页码 -1 开关
  - 输出路径自动生成 `<原名>_bookmarked.pdf`，可编辑
  - 执行按钮 → threading 防卡顿 + queue 通信 + 进度条
  - 完成弹窗 + 「打开输出文件夹」按钮

### #3 · 端到端联调与 README
- **工作量**：1h
- **依赖**：#8, #6, #7, #9
- **产出**：
  - 真实 PDF + TXT/MD 跑通（人工验收）
  - 错误场景：页码越界 / 文件被占用 / 无 outline PDF
  - `README.md`：用法、解析规则示例、常见问题

---

## 执行依赖图

```
#1 (脚手架)
 │
 ├──► #5 (parser.py) ─┬──► #9 (MD 夹具) ──┐
 │                    │                    │
 │                    └──► #4 (GUI 主框架) ─┴──► #8 (规则编辑器) ──┐
 │                                                                  │
 └──► #2 (bookmark.py) ─┬──► #7 (bookmark 测试) ───────────────────┤
                        │                                          │
                        └──► #4 (GUI 主框架) ──► #6 (输出与执行) ───┤
                                                                   │
                                                                   ▼
                                                                  #3 (端到端 + README)
```

---

## 工作量汇总

| 优先级 | 任务 | 累计 |
|--------|------|------|
| P0 | #1 | 0.5h |
| P1 | #5, #2 | 3.5h |
| P2 | #7, #4, #9 | 4h |
| P3 | #8, #6, #3 | 3h |
| **总计** | **8 个任务** | **11h** |

---

## 验收清单

- [ ] 8 个任务全部 Completed
- [ ] 单元测试通过：`pytest tests/` 全绿
- [ ] 端到端跑通：真实 PDF + TXT/MD 各 1 例
- [ ] 输出 PDF 在 Preview / Adobe Reader 中书签树正确显示

---

## v1.1 增量：在线书签获取 + 自动保存 TXT

> 2026-06-27 增量规划

### 任务概览

| ID | 任务 | 工作量 | 状态 |
|----|------|--------|------|
| #18 | `fetcher.py` + 单测（mock HTTP） | 1.5h | ⬜ Pending |
| #19 | `to_indent_dot` + `save_bookmarks_txt` + 单测 | 1h | ⬜ Pending |
| #17 | GUI 新增「在线获取」区 + 挂载后自动保存 | 1.5h | ⬜ Pending |
| #20 | 端到端 + README/spec 更新 + commit/push | 0.5h | ⬜ Pending |

**总计：4.5h**

### 依赖关系

```
[parser] ──┬──► #18 (fetcher.py)
           │       │
           └──► #19 (to_indent_dot)
                   │
                   └──► #17 (GUI 集成)
                            │
                            └──► #20 (E2E + 文档)
```

### #18 · 在线书签获取 fetcher.py（TDD）

- `src/fetcher.py`：`BookMeta` / `FetchError` / `fetch_bookmarks(ssid) -> (BookMeta, list[BookmarkNode])`
- 使用 `urllib.request`（零依赖）
- 按 API `i` 字段直接建树（4 级：卷/节/小节/标题）
- 单测：`unittest.mock` 模拟 HTTP 响应（成功 / 4xx / 超时 / 坏 JSON / 空目录）
- 真实 API 测试 `@pytest.mark.skipif(no_network)` 跳过

### #19 · 书签节点序列化 TXT（TDD）

- `src/parser.py::to_indent_dot(nodes, *, indent_spaces=2) -> str`
- `src/bookmark.py::save_bookmarks_txt(nodes, output_path) -> Path`
- 单测：单层 / 多层 / Unicode / None page
- **Round-trip**：`parse(to_indent_dot(parse(text))) == parse(text)`

### #17 · GUI 新增「在线获取」区 + 挂载后自动保存

- `src/app.py`：在主区顶部新增 section「0. 在线获取」
  - SSID 输入框 + 「🌐 获取书签」按钮 + 状态标签
  - 点击后后台线程调用 fetcher，结果填充预览
- `_mount_worker` 成功后调用 `save_bookmarks_txt` 写 `<pdf>_bookmarks.txt`
- 日志区追加「✓ 已保存书签文件：xxx」

### #20 · fetcher 端到端与文档更新

- `tests/test_fetcher.py`：1 个真实 API 调用测试（无网络 skip）
- `docs/plan.md` §12 增量计划（已完成）
- `README.md`：补充「在线获取」用法
- `spec.md`：补充 fetcher / save_bookmarks_txt 接口契约
- commit + push

### v1.1 验收清单

- [ ] 4 个新任务全部 Completed
- [ ] 51 个旧测试仍通过
- [ ] 新增 fetcher / serializer / save_bookmarks_txt 测试通过
- [ ] GUI 输入 SSID 后预览填充
- [ ] 挂载成功后同目录生成 `<pdf>_bookmarks.txt`
- [ ] TXT 可被 `indent-dot` 模板重新解析（round-trip 验证）
- [ ] README 含用法、解析规则示例、常见问题
- [ ] 无 `pypdf` 之外的运行依赖
- [ ] GUI 启动 < 1s，解析 1000 行 < 100ms

---

## v1.2 增量：书签文本编辑区

> 2026-06-27 增量规划
> 详见 [`proposal-bookmark-text-area.md`](proposal-bookmark-text-area.md)

### 任务概览

| ID | 任务 | 工作量 | 状态 |
|----|------|--------|------|
| #21 | `read_bookmarks` 实现 + 单测 + round-trip | 1h | ⬜ Pending |
| #22 | GUI 新增「书签文本」section + 4 按钮 | 1.5h | ⬜ Pending |
| #23 | 文本 ↔ Treeview 同步逻辑 + 自动解析节流 | 0.5h | ⬜ Pending |
| #24 | 端到端 + README/spec 更新 + commit/push | 0.5h | ⬜ Pending |

**总计：3.5h**

### 依赖关系

```
[parser, bookmark] ──► #21 (read_bookmarks)
                            │
                            ▼
                       #22 (GUI section)
                            │
                            ▼
                       #23 (同步逻辑)
                            │
                            ▼
                       #24 (E2E + 文档)
```

### #21 · 读取 PDF 书签（TDD）

- `src/bookmark.py::read_bookmarks(pdf_path) -> list[BookmarkNode]`
  - 递归遍历 `reader.outline`（处理嵌套 list，复用 `_walk` 思路）
  - `reader.get_destination_page_number(item.page)` 取页索引 → +1 转 1-based
  - 异常页码 → `page=None`，不抛错
  - `line_no` 按 DFS 顺序分配
- `tests/test_bookmark.py` 新增：
  - `test_read_bookmarks_with_outline`：reportlab 造带 outline 的 PDF → 验证节点结构
  - `test_read_bookmarks_no_outline`：返回空列表
  - `test_read_bookmarks_nested`：多层 outline → 正确建立 children
  - `test_read_bookmarks_invalid_page`：`page=None`
  - `test_read_bookmarks_round_trip`：`read → to_indent_dot → parse` 结构等价

### #22 · GUI 新增「书签文本」section

- `src/app.py`：在「1. 选择文件」与「2. 解析规则」之间新增 `_build_text_section()`
- 文本控件：`tk.Text(height=8, wrap=tk.WORD)` + `Scrollbar`
- 四个按钮：
  - `📥 从 PDF 读取书签` → `_do_read_pdf()`
  - `🔄 解析文本` → `_do_parse_text()`
  - `📋 清空` → 清空 Text + `_last_nodes` + Treeview
  - `💾 导出 TXT` → 写入 `_source_path` 或弹窗另存为
- 状态变量：`self._text_dirty = tk.BooleanVar(value=False)` 标记文本被编辑
- 编号调整：原「2. 解析规则」保持，但「3. 预览」→「4. 预览」，依此类推

### #23 · 文本 ↔ Treeview 同步

- 新增 `_sync_text_from_nodes(nodes)`：用 `to_indent_dot` 序列化后填入 Text
- 新增 `_sync_tree_from_nodes(nodes)`：复用 `_refresh_preview`
- 修改 `_do_parse` / `_do_fetch`：解析成功后调用 `_sync_text_from_nodes`
- 自动解析：`Text` 控件绑定 `<KeyRelease>` + 500ms `after` 节流 → 自动 `_do_parse_text()`
- `_do_parse_text`：Text 内容 → 当前规则 → `_last_nodes` → `_refresh_preview`

### #24 · 端到端验收与文档

- `tests/test_e2e.py` 新增：粘贴文本 → 解析 → 挂载 → 读取校验
- `README.md`：补充「书签文本区」用法章节
- `docs/spec.md`：补充 `read_bookmarks` 接口契约
- `docs/plan.md` §13（已完成）
- commit + push

### v1.2 验收清单

- [ ] 4 个新任务全部 Completed
- [ ] 51 个 v1.0 测试 + v1.1 测试全部通过
- [ ] 新增 `read_bookmarks` 测试通过
- [ ] round-trip 测试通过
- [ ] PDF 有书签时「📥 读取」正确填充文本区
- [ ] PDF 无书签时不崩溃，友好提示
- [ ] 外部粘贴文本 → 解析 → Treeview → 挂载链路通
- [ ] 文本区编辑 → 解析 → 挂载链路通
- [ ] 现有 TXT/MD 文件输入流仍可用
- [ ] 现有 SSID 在线获取仍可用
- [ ] 文本区与 Treeview 双向同步
- [ ] README 补充「书签文本区」用法说明
- [ ] GUI 启动 < 1s（增加 section 后不退化）
- [ ] 解析 1000 行 < 100ms

---

## v1.3 增量：在线获取 UX 增强

> 2026-06-27 增量规划
> 详见 [`proposal-save-after-fetch.md`](proposal-save-after-fetch.md)

### 任务概览

| ID | 任务 | 工作量 | 状态 |
|----|------|--------|------|
| #25 | `_sanitize_filename` + `_suggest_default_filename` 实现 + 单测 | 0.5h | ⬜ Pending |
| #26 | `_build_fetch_section` 加 hint + `_do_export_txt` 改用 suggested | 0.3h | ⬜ Pending |
| #27 | README + spec 更新 + commit | 0.3h | ⬜ Pending |

**总计：1.1h**

### 依赖关系

```
#25 (sanitize + suggest)
    │
    ▼
#26 (GUI hint + export)
    │
    ▼
#27 (文档)
```

### #25 · sanitize 与默认文件名工具（TDD）

- `app.py::BookmarkApp._sanitize_filename(name, max_len=80) -> str`：
  - 移除 `/\\:*?"<>|\r\n\t`
  - 折叠连续空白
  - 截断到 max_len
  - 空字符串兜底 `"bookmarks"`
- `app.py::BookmarkApp._suggest_default_filename() -> str`：
  - 优先级：`_book_meta.title` > `_source_path.stem` > `"bookmarks"`
  - 书名为空时回退到 `_book_meta.ssid`
- 单测 `tests/test_export_filename.py`：
  - `test_sanitize_filename_removes_illegal_chars`
  - `test_sanitize_filename_collapses_whitespace`
  - `test_sanitize_filename_truncates`
  - `test_sanitize_filename_empty_falls_back_to_bookmarks`
  - `test_suggest_default_filename_uses_book_meta_title`
  - `test_suggest_default_filename_falls_back_to_ssid`
  - `test_suggest_default_filename_uses_source_path_stem`
  - `test_suggest_default_filename_no_source_uses_bookmarks`

### #26 · GUI hint + export 默认名

- `_build_fetch_section` 增加 hint：
  - `提示：获取后可直接点「⚙ 执行挂载」，无需先选书签源文件。`
- `_do_export_txt` 修改：
  - 用 `_suggest_default_filename()` 生成默认名
  - `filedialog.asksaveasfilename(..., initialfile=suggested, ...)`

### #27 · 文档与提交

- `README.md`：在「在线获取流程」或新增小节说明「可跳过书签源直接挂载」
- `docs/spec.md`：在 §6 补充 `_sanitize_filename` / `_suggest_default_filename` 契约
- `docs/plan.md` §14（已完成）
- commit + push
- **不重新打包**（v1.3 仅 UX 改动，不发布新版本）

### v1.3 验收清单

- [ ] 3 个新任务全部 Completed
- [ ] 81 个旧测试仍通过
- [ ] 新增 sanitize / suggest 测试通过
- [ ] 「0. 在线获取」区显示 hint 标签
- [ ] 在线获取后点「💾 导出 TXT」→ Save As 弹窗默认名为 `<书名>_bookmarks.txt`
- [ ] 书名含 `/` 等非法字符时 sanitize 生效
- [ ] README / spec 文档已更新

---

## v1.4 增量：书签文本编辑工具集

> 2026-06-27 增量规划
> 详见 [`proposal-bookmark-tools.md`](proposal-bookmark-tools.md)

### 任务概览

| ID | 任务 | 工作量 | 状态 |
|----|------|--------|------|
| #28 | `transforms.py` 模块（8 个 P0+P1 函数）+ 单测 | 1.5h | ⬜ Pending |
| #29 | GUI：页码 Spinbox + 应用按钮 + `_do_shift_pages` | 0.5h | #28 |
| #30 | GUI：🔧 工具弹窗 + `_open_tools_window` + 7 个工具接线 | 1.0h | #28 |
| #31 | `_apply_transform` 抽象 + README + spec + commit | 0.5h | #29, #30 |

**总计：3.5h**

### 依赖关系

```
#28 (transforms.py)
   ├──► #29 (页码 Spinbox)
   │       │
   │       ▼
   │   #31 (抽象 + 文档)
   └──► #30 (工具弹窗)
           │
           ▼
       #31 (抽象 + 文档)
```

### #28 · transforms 模块（TDD）

- `bookmark_pdf/transforms.py` 新增 8 个纯函数：
  - `shift_pages(nodes, offset)` — 所有页码 +/- offset
  - `normalize_pages(nodes, start=1)` — 从 start 重新编号
  - `cap_pages(nodes, max_page)` — 超过 max_page 设为 None
  - `sort_by_page(nodes, descending=False)` — 按页码排序
  - `remove_duplicates(nodes)` — 重复条目去重
  - `remove_invalid_pages(nodes)` — 移除 page=None
  - `trim_titles(nodes)` — 标题去空白
  - `flatten(nodes)` — 移除层级
- 每个函数：纯函数 + 处理嵌套 + None 安全
- 单测 `tests/test_transforms.py`：
  - 每函数 ≥ 2 用例
  - round-trip 测试（除归一化/排序/裁剪外）

### #29 · GUI 页码 +/- 直接显示

- `_build_text_section` 按钮区新增：
  - `Label("页码 +/-")` + `Spinbox(-9999, 9999)` + `Button("应用")`
- `_do_shift_pages(offset)`：
  - 调用 `_apply_transform(lambda n: shift_pages(n, offset), f"页码 {offset:+d}")`

### #30 · 🔧 工具弹窗

- `_open_tools_window()`：
  - 弹 `tk.Toplevel`，标题"书签文本工具"
  - 4 个分组：`ttk.Labelframe`
  - 每组若干 `ttk.Radiobutton` + 参数 `Entry/Spinbox`
  - 底部 `[执行] [取消]`
- 弹窗点击"执行" → 调 `_apply_transform`
- 7 个工具接线：normalize / cap / sort_asc / sort_desc / dedup / remove_invalid / trim / flatten
- 弹窗关闭时清理引用

### #31 · 抽象 + 文档

- `_apply_transform(transform, label)` 通用抽象方法
- README 补充「书签文本工具」用法章节
- spec.md §6 补充 transforms 模块契约
- commit + push

### v1.4 验收清单

- [ ] 4 个新任务全部 Completed
- [ ] 81 个旧测试仍通过
- [ ] 8 个新 transform 测试通过
- [ ] 主工具栏页码 +/- 可工作
- [ ] 🔧 工具弹窗可打开并执行 7 个工具
- [ ] 执行 transform 后文本、预览、_last_nodes 三者同步
- [ ] README / spec 文档已更新