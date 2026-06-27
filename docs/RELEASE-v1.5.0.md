# Release v1.5.0 · 项目修改记录

> 发布日期：2026-06-27
> Git range: `ddf3f98..HEAD`（3 个 feat commit）
> 发布分支：`release/v1.5.0`

---

## 1. 变更概览

| 维度 | v1.1.0 → v1.5.0 |
|------|------------------|
| 提交数 | +3（v1.2 / v1.3 / v1.4） |
| 新增模块 | `bookmark_pdf.transforms` |
| 新增方法 | `BookmarkApp._sanitize_filename` / `_suggest_default_filename` / `_prompt_save_after_fetch` |
| 新增测试 | 44 个（12 filename + 32 transforms） |
| 测试总数 | 139（44 新 + 95 旧） |
| 代码行数（app.py） | 851 → 1025（+174） |
| 文档 | CHANGELOG.md（新增）/ README / spec / tasks 同步更新 |
| 二进制 | 27 MB（macOS arm64） |

---

## 2. 三个 commit 的内容

### `91cafa8` feat(v1.2): 书签文本编辑区

- **`bookmark_pdf.bookmark`** 新增 `read_bookmarks(pdf_path) → list[BookmarkNode]`
  - 处理 pypdf 5+ 的 nested-list outline 结构 `[A, [B, C], D]`
  - 1-based 页码（与 parser 一致），异常页 → `page=None`
- **GUI** 新增「2. 书签文本（可编辑）」section（4 按钮 + 8 行 Text + 自动 500ms 节流解析）
- 文本 ↔ Treeview 双向同步（仅在文本区为空或未脏时覆盖）

### `07fcce2` feat(v1.3): 在线获取后弹框保存 + 书签源可为空

- **新增 `_sanitize_filename` / `_suggest_default_filename` 工具方法**
  - 优先级：`_book_meta.title` → `_book_meta.ssid` → `_source_path.stem` → `"bookmarks"`
  - 自动跳过已以 `bookmarks` 结尾的 stem（避免 `my_bookmarks_bookmarks.txt`）
- **新增 `_prompt_save_after_fetch(meta)`**
  - `askyesno("是否保存书签", ...)` → `askdirectory(...)` → `save_bookmarks_txt`
  - 用 `self.after(0, ...)` 调度，避开 `_poll_fetch` 循环
- `_build_fetch_section` 加 hint 标签
- `_do_export_txt` Save As 用 `_suggest_default_filename()` 作默认名

### `c98f1fd` feat(v1.4): 书签文本工具集

- **新增 `bookmark_pdf.transforms` 模块**（8 个纯函数 + 3 个 P2 stub）
  - `shift_pages` / `normalize_pages` / `cap_pages` / `sort_by_page`
  - `remove_duplicates` / `remove_invalid_pages` / `trim_titles` / `flatten`
- **GUI 主工具栏**：页码 +/- Spinbox + 应用按钮
- **GUI「🔧 工具 ▼」弹窗**（Toplevel）：4 Labelframe 分组 8 工具
- **新增 `_apply_transform(transform, label)` 抽象方法**：统一 text/preview/nodes 三者同步

---

## 3. 关键文件变更

```
bookmark_pdf/
├── app.py                     # +174 行（fetch 弹框 + filename 工具 + transforms 接线）
├── bookmark.py                # +25 行（read_bookmarks 实现）
└── transforms.py              # 新文件，115 行（8 纯函数 + 3 stub）

tests/
├── test_filename_utils.py     # 新文件，12 用例
├── test_read_bookmarks.py     # 新文件，7 用例
└── test_transforms.py         # 新文件，32 用例

docs/
├── spec.md                    # +3 子节（§6.7.1-6.7.3 / §6.8）
├── tasks.md                   # 4 增量小节（v1.2-v1.4）
└── RELEASE-v1.5.0.md          # 本文件

packaging/
├── bookmark_pdf.spec          # 版本号 1.4.0 → 1.5.0
└── dist/
    ├── BookmarkPDF.app        # 新构建（arm64，27 MB）
    └── BookmarkPDF-macos-arm64.zip
```

根目录：
```
CHANGELOG.md                   # 新增（Keep a Changelog 风格）
pyproject.toml                 # 版本号 1.4.0 → 1.5.0
.gitignore                     # +.venv311
```

---

## 4. 用户可见的功能变化

| 功能 | v1.1 | v1.5 |
|------|------|------|
| 书签源：TXT/MD 文件 | ✅ | ✅ |
| 书签源：在线 SSID 拉取 | ✅ | ✅ |
| 书签源：从 PDF 读取 outline | ❌ | ✅（v1.2） |
| 书签源：粘贴外部文本 | ❌ | ✅（v1.2） |
| 书签源：编辑后自动解析 | ❌ | ✅（v1.2） |
| 在线获取 → 一键保存到文件夹 | ❌ | ✅（v1.3） |
| 在线获取 → 直接挂载（无需书签源） | 隐藏 | 显式（v1.3 hint） |
| 主工具栏页码批量偏移 | ❌ | ✅（v1.4） |
| 工具弹窗（8 个批量编辑工具） | ❌ | ✅（v1.4） |

---

## 5. 验收清单

- [x] 139 个测试全过
- [x] `.app` 启动 smoke test 通过（PID 82114，3s 后正常退出）
- [x] 版本号一致：`pyproject.toml` / `bookmark_pdf.spec` / `Info.plist` 均为 1.5.0
- [x] CHANGELOG.md 记录完整
- [x] README 路线图标记 v1.4 为当前
- [x] spec.md §6 包含新接口契约
- [x] tasks.md 4 增量小节状态准确
- [x] `.venv311` 已加入 `.gitignore`
- [x] 不破坏 v1.1 既有功能（向后兼容）

---

## 6. 已知限制 / 后续计划

- **未实现**：v1.5 路线图中的「书签模板保存/加载」「批量处理」未做
- **测试覆盖**：GUI 流程仍以 smoke test 为主，未做端到端 GUI 自动化
- **CI**：未配置 GitHub Actions 自动构建多平台 release
- **代码签名**：`.app` 未做正式 codesign，macOS Gatekeeper 首次打开需右键「打开」

---

## 7. 上游 / 下游依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| pypdf | 6.14 | PDF 读写 + outline |
| tkinter | stdlib | GUI |
| PyInstaller | 6.21 | 打包 |
| reportlab | 5.0 | 测试 PDF 生成 |
| pytest | 8.4 | 测试框架 |
| Python | 3.10+ | 运行时 |
