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
- [ ] README 含用法、解析规则示例、常见问题
- [ ] 无 `pypdf` 之外的运行依赖
- [ ] GUI 启动 < 1s，解析 1000 行 < 100ms