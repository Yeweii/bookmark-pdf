# Changelog · 书签挂载工具

> 与 GitHub Releases 配套的版本变更日志
> 维护原则：按 [Keep a Changelog](https://keepachangelog.com/) 风格书写

---

## [1.5.0] - 2026-06-27

### 新增

- **v1.3 在线获取后弹框保存**：在线获取成功后，弹框询问「是否保存书签？」
  - 选「是」→ 弹出文件夹选择对话框 → 保存为 `<书名>_bookmarks.txt`
  - 文件名自动 sanitize（去除 `/\\:*?"<>|` 等非法字符、折叠空白、截断 80 字）
  - 选「否」或取消 → 不保存，无错误
- **v1.3 书签源可为空**：在线获取成功后，无需在「1. 选择文件」选书签源，
  直接选 PDF → 点「⚙ 执行挂载」即可；fetch 区显示 hint 提示
- **v1.4 书签文本工具集**：新增 `bookmark_pdf.transforms` 模块，8 个纯函数变换
  - 主工具栏：页码 +/- Spinbox + 应用（所有页码批量偏移 N）
  - 「🔧 工具 ▼」弹窗：4 分组共 8 个工具
    - 页码：归一化（DFS 重新编号）/ 裁剪到最大页
    - 清理：去重（title+page）/ 移除异常页（page=None）
    - 文本：去除标题首尾空白（Trim）
    - 树形：展平（DFS）/ 按页码升序 / 按页码降序
- **v1.4 文件名工具**：`_sanitize_filename` / `_suggest_default_filename`
  - 复用 v1.3 的 sanitize 逻辑
  - 「💾 导出 TXT」 Save As 弹窗的 `initialfile` 自动使用建议名
- **测试**：新增 12 个 filename_utils 单测 + 32 个 transforms 单测 = 共 44 个新测试

### 变更

- 优化测试基础设施：项目要求 Python ≥ 3.10（PEP 604 union syntax）
- `.gitignore` 新增 `.venv311/`
- 版本号：`1.4.0` → `1.5.0`

### 技术细节

- 弹框调度使用 `self.after(0, ...)`，避免阻塞 `_poll_fetch` 循环
- 工具弹窗使用 `tk.Toplevel(transient=self)`，随主窗口最小化
- transforms 全为纯函数：输入 `list[BookmarkNode]` → 返回新列表（不修改输入）
- PyInstaller 6.21 + Python 3.11 + pypdf 6.14

### 验证

- 139 个单元测试全过（44 新 + 95 旧）
- `.app` 启动 smoke test 通过
- 二进制大小：27 MB（macOS arm64）

---

## [1.4.0] - 2026-06-27

### 新增

- 「2. 书签文本（可编辑）」section 的工具栏
- 页码 +/- Spinbox + 应用按钮（主工具栏）
- 「🔧 工具 ▼」Toplevel 弹窗（4 分组 8 工具）
- `bookmark_pdf.transforms` 模块（8 纯函数）

### 文档

- `README.md` 新增「🔧 工具弹窗」章节
- `docs/spec.md` §6.8 transforms 模块契约
- `docs/plan.md` §15 v1.4 增量计划

---

## [1.3.0] - 2026-06-27

> 注：v1.3 在 1.4 之后补齐，合并发布于 1.5.0

### 新增

- 在线获取后 `_prompt_save_after_fetch` 弹框流程
- `_sanitize_filename` / `_suggest_default_filename` 文件名工具
- 「0. 在线获取」区 hint 标签

---

## [1.2.0] - 2026-06-27

### 新增

- 「2. 书签文本（可编辑）」section
  - 8 行 Text 多行编辑区 + 横向滚动
  - 「📥 从 PDF 读取书签」按钮
  - 「🔄 解析文本」按钮（自动 500ms 节流）
  - 「📋 清空」/「💾 导出 TXT」按钮
- `bookmark_pdf.bookmark.read_bookmarks` 从 PDF outline 反向构造 BookmarkNode 树
- 文本 ↔ Treeview 双向同步（仅在文本区为空或未脏时覆盖）

---

## [1.1.0] - 2026-06-27

### 新增

- 「0. 在线获取（可选）」section：SSID 输入 + 后台拉取书签
- `bookmark_pdf.fetcher` 模块：`fetch_bookmarks(ssid) → (BookMeta, list[BookmarkNode])`
- `bookmark_pdf.bookmark.save_bookmarks_txt` 挂载成功后自动保存 `<pdf>_bookmarks.txt`
- `bookmark_pdf.parser.to_indent_dot` BookmarkNode → indent-dot 格式序列化
- 「3. 解析规则」新增 `indent-dot` 模板

---

## [1.0.0] - 2026-06-27

### 新增

- 核心解析：`bookmark_pdf.parser`（6 个内置模板 + 3 种层级模式 + 自定义正则）
- 挂载：`bookmark_pdf.bookmark.mount_bookmarks`（3 种 mode + page_offset + 进度回调）
- GUI：`bookmark_pdf.app.BookmarkApp`（Tkinter 7 section 一体化操作）
- PyInstaller 打包：macOS `.app` + 跨平台 spec
- `pyproject.toml` + `pip install -e ".[dev]"` + `bookmark-pdf` CLI 入口
