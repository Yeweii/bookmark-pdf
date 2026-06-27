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