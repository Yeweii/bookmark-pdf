# Proposal: 书签文本编辑区（Bookmark Text Editor）

> 日期：2026-06-27
> 关联 Plan：v1.2 增量

---

## 1. 背景与目标

### 1.1 当前痛点

Bookmark PDF 现有流程：**书签源文件（TXT/MD）→ 解析 → 预览（Treeview）→ 挂载**。要修改任何书签都必须先准备一个 TXT/MD 文件，流程笨重：

- 用户想修正几行书签，需要"打开文件 → 编辑 → 保存 → 重选文件 → 重解析"
- 想复用其他来源（如微信、PDF 阅读器、网页）拷来的目录，得手动粘贴进 TXT
- 无法直接编辑已有 PDF 的书签树后挂回

### 1.2 目标

新增「**书签文本区**」——一个内置的、可编辑的多行文本框，作为书签的**直接编辑入口**：

1. **读 PDF 书签 → 显示 → 编辑 → 挂回**：一键把 PDF 现有 outline 转成文本填入区，用户编辑后挂载
2. **外部粘贴 → 编辑 → 挂载**：从任意来源复制的目录文本直接粘贴进来，挂载到目标 PDF
3. 现有 TXT/MD 文件输入流、在线 SSID 获取、模板解析系统**全部保留**

### 1.3 非目标

- 不替换 Treeview 预览（仍作为校验视图保留）
- 不破坏现有解析模板/正则系统
- 不引入新的运行依赖

---

## 2. 用户场景

| 场景 | 现有流程 | 新流程 |
|------|---------|--------|
| A. 在线获取后微调 | 拉到预览 → ❌ 无法编辑 → 只能重做 | 拉到预览 → 切到文本区 → 改一行 → 解析 → 挂载 |
| B. 修改 PDF 现有书签 | 导出 outline 到 TXT → 编辑 TXT → 选文件 → 解析 → 挂载 | 选 PDF → 点「📥 读取」 → 编辑 → 解析 → 挂载 |
| C. 微信/网页复制目录 | 粘贴到记事本 → 保存为 .txt → 选文件 → 解析 → 挂载 | 粘贴到文本区 → 选模板 → 解析 → 挂载 |
| D. TXT 文件输入 | 选文件 → 解析 → 挂载 | 不变（仍可用） |

---

## 3. 候选方案

### 3.1 文本区放置位置

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| **A. 独立 section（推荐）** | 在「解析规则」之上新增「3. 书签文本」区 | 流程清晰：源 → 文本 → 规则 → 预览 | 占用屏幕高度 |
| B. 嵌入 Treeview 预览区 | Text + Tree 双视图切换 Tab | 紧凑 | 实现复杂、UX 突兀 |
| C. 替换 Treeview | 直接用 Text 显示书签（缩进格式） | 最简洁 | 失去错误高亮、节点计数 |

**决策**：A。增量最小、语义清晰。

### 3.2 文本格式

| 方案 | 描述 |
|------|------|
| **A. indent-dot（推荐）** | `Title ...... 1`，已有 `to_indent_dot` 序列化函数，round-trip 经过 Parser 验证 |
| B. 让用户选 | 5 种内置模板都要支持，复杂度高 |

**决策**：A。indent-dot 是项目原生格式，序列化函数已存在。

### 3.3 读取 PDF 书签

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| **A. 显式按钮（推荐）** | 用户点「📥 从 PDF 读取书签」 | 避免误覆盖用户编辑 | 多一步 |
| B. 选择 PDF 自动读取 | 选完 PDF 自动填入 | 一步到位 | 会清空用户已有文本/解析结果 |
| C. 弹窗询问 | 选完 PDF 弹窗 | 折中 | 多一次点击 |

**决策**：A。显式按钮最安全。

### 3.4 文本 → BookmarkNode 触发时机

| 方案 | 描述 |
|------|------|
| **A. 显式「解析」按钮 + onChange 节流（推荐）** | 手动按钮触发 + 编辑 500ms 后自动解析 |
| B. 完全手动 | 只手动按钮 |
| C. 完全实时 | 每次按键都解析，性能差 |

**决策**：A。给用户反馈同时避免卡顿。

### 3.5 与现有数据流的关系

```
┌─────────────────────────────────────────────────────────────┐
│ 书签源（多路并存）：                                          │
│   ① TXT/MD 文件 ───┐                                        │
│   ② 在线 SSID  ────┼──► _last_nodes (list[BookmarkNode])    │
│   ③ PDF 已有书签 ──┤     ▲                                  │
│   ④ 外部粘贴文本 ──┘     │                                  │
│                          │                                  │
│   ┌──────────────┐        │                                  │
│   │ Treeview 预览 │◄───────┘                                  │
│   └──────────────┘                                           │
│          ▲                                                   │
│          │ 解析后刷新                                         │
│   ┌──────────────┐                                           │
│   │ 文本编辑区    │  to_indent_dot(_last_nodes)              │
│   │ (indent-dot) │  ◄─── 用户编辑                            │
│   └──────────────┘  ───► Parser.parse(text) → _last_nodes   │
└─────────────────────────────────────────────────────────────┘
```

**决策**：四种来源并存，统一汇入 `_last_nodes`；文本区与 Treeview 双向联动。

---

## 4. 模块设计

### 4.1 新增 `bookmark_pdf/bookmark.py::read_bookmarks`

```python
def read_bookmarks(pdf_path: Path) -> list[BookmarkNode]:
    """Read existing outline from PDF and return as BookmarkNode tree.

    - PDF page index is 0-based → store 1-based in node.page (consistent with Parser)
    - Recursively walks nested lists in reader.outline
    - Skips items with unresolvable page (page=None)
    - line_no: assigned sequentially during DFS
    """
```

要点：
- 复用 `bookmark.py::_walk` 的遍历思路
- 用 `reader.get_destination_page_number(item.page)` 取页索引（0-based）→ +1 转 1-based
- 异常页码（None）允许挂在树上，挂载时会标红/跳过

### 4.2 GUI 新增 section「书签文本（可编辑）」

放在现有「1. 选择文件」和「2. 解析规则」之间，编号为 **1.5 / 新 3**：

```
┌─ 3. 书签文本（可编辑）─────────────────────────────┐
│ 格式：indent-dot（Title ...... Page，可手动改）     │
│ [多行 Text 控件，高度 8 行，自动换行]              │
│                                                     │
│ [📥 从 PDF 读取书签] [🔄 解析文本] [📋 清空] [💾 导出TXT] │
└─────────────────────────────────────────────────────┘
```

按钮行为：
- **📥 从 PDF 读取书签**：`pdf_path` 非空 → 调用 `read_bookmarks` → `to_indent_dot` → 填入 Text；空 → messagebox 提示先选 PDF
- **🔄 解析文本**：Text 内容 → 当前规则（默认 `indent-dot`）→ `_last_nodes` → 刷新 Treeview
- **📋 清空**：清空 Text + 清空 `_last_nodes` + 清空 Treeview
- **💾 导出 TXT**：把 Text 内容直接写到 `_source_path`（或弹窗另存为）

### 4.3 数据流改动

新增 state：
- `self._text_source = tk.BooleanVar(value=False)` — 标记当前 `_last_nodes` 来自文本区（用于决定是否自动回填）

修改：
- `_do_parse`（文件输入）→ 解析成功后调用 `_sync_text_from_nodes(nodes)` 把 Treeview 内容同步到 Text
- `_do_fetch`（SSID）→ 同上
- **新增** `_do_read_pdf` → 读 PDF → 同步到 Text → 解析 → 刷新 Treeview
- **新增** `_do_parse_text` → Text 内容 → 解析 → 刷新 Treeview
- 任何解析成功后 `_update_run_button()` 不变（仍按 `_last_nodes` 判断）

### 4.4 自动保存（保留现有 v1.1 行为）

挂载成功后调用 `save_bookmarks_txt(nodes, txt_path)` **不依赖文本区来源** —— 只要 `_last_nodes` 有效就保存。

---

## 5. 错误处理

| 场景 | 处理 |
|------|------|
| 文本区为空 | 「解析文本」按钮置灰；「执行挂载」已有相同防护 |
| 文本格式无法解析 | messagebox.showerror，列出错误行号；不清空已有 `_last_nodes` |
| 选择 PDF 后无 outline | messagebox.showinfo「该 PDF 没有书签」；Text 仍可手动编辑 |
| PDF 加密/损坏 | messagebox.showerror「PDF 读取失败」 |
| 文本区编辑后未点解析就点挂载 | 仍按当前 `_last_nodes` 挂载（避免误挂编辑中的脏数据） |
| 文本区编辑后切换模板 | 提示「文本已修改，是否重新解析？」 |

---

## 6. 测试策略

### 6.1 单元测试 `tests/test_bookmark.py` 新增

- `test_read_bookmarks_with_outline`：reportlab 生成带 outline 的 PDF → `read_bookmarks` → 验证节点结构
- `test_read_bookmarks_no_outline`：无书签 PDF → 返回空列表
- `test_read_bookmarks_nested`：多层 outline → 正确建立 children
- `test_read_bookmarks_invalid_page`：某项指向不存在的页 → `page=None`

### 6.2 round-trip 验证

`test_bookmark.py` 新增：
- `read_bookmarks(pdf)` → `to_indent_dot(...)` → `Parser.parse(...)` → 结构等价

### 6.3 GUI 手动验收

- 粘贴一段外部文本 → 解析 → Treeview 显示 → 挂载
- 选带书签 PDF → 「📥 读取」 → 文本区显示 → 编辑一行 → 解析 → 挂载
- 在线 SSID → 拉到预览 → 切到文本区 → 改一行 → 解析 → 挂载

---

## 7. 风险与权衡

| 风险 | 缓解 |
|------|------|
| 文本区与 Treeview 不同步导致挂错内容 | 解析后同步；状态栏始终显示当前节点数；执行前可选弹窗确认 |
| PDF outline 解析异常 | 复用 `_walk` 思路；异常页设 `page=None` 而非崩溃 |
| 文本区过大卡顿 | Text 控件无性能问题；解析按需触发 |
| 占用屏幕高度 | 6 段变 7 段，可滚动容器或降低每段高度 |
| 现有 v1.1 自动保存 TXT 行为 | 不改：仍按 `_last_nodes` 保存 |

---

## 8. 验收标准

- [ ] PDF 有书签时「📥 读取」正确填充文本区
- [ ] PDF 无书签时不崩溃，友好提示
- [ ] 外部粘贴文本 → 解析 → Treeview 显示 → 挂载链路通
- [ ] 文本区编辑 → 解析 → 挂载链路通
- [ ] 现有 TXT/MD 文件输入流仍可用
- [ ] 现有 SSID 在线获取仍可用
- [ ] 文本区与 Treeview 双向同步（编辑 → 重解析 → 刷新）
- [ ] 51 个旧测试仍全部通过
- [ ] 新增 `read_bookmarks` 测试通过
- [ ] round-trip 测试通过
- [ ] README 补充「书签文本区」用法说明

---

## 9. 工作量预估

| 模块 | 工作量 |
|------|--------|
| `read_bookmarks` 实现 + 单测 | 1h |
| GUI 新增 section（布局 + 4 按钮 + 解析） | 1.5h |
| 文本 ↔ Treeview 同步逻辑 | 0.5h |
| round-trip 测试 + 端到端验收 | 0.5h |
| README + spec 更新 | 0.5h |
| **总计** | **4h** |