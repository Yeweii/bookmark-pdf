# Proposal: 在线获取后保存书签 + 允许空书签源挂载

> 日期：2026-06-27
> 关联 Plan：v1.3 增量

---

## 1. 背景与目标

### 1.1 当前痛点

- 在线获取书签成功后，用户没有明显的"保存书签"入口，只能去手动点「💾 导出 TXT」
- 用户可能不清楚"在线获取后可以直接挂载"——可能误以为必须先选书签源文件

### 1.2 目标

1. **在线获取成功后弹框询问"是否保存书签？"** → 用户选择"是" → 选择文件夹 → 保存为 `<书名>_bookmarks.txt`
2. **明确支持"在线获取 → 直接挂载"流程**（书签源 `_source_path` 可为空）

### 1.3 非目标

- 不改变挂载时自动保存 TXT 的现有行为（仍按 `default_txt_path_for(out_path)` 写到 PDF 同目录）
- 不影响 TXT/MD 文件输入流、PDF 已有书签读取、文本编辑区等其他来源

---

## 2. 用户场景

| 场景 | 现有流程 | 新流程 |
|------|---------|--------|
| 在线获取 → 想保存书签到指定文件夹 | 拉到预览 → 点「💾 导出 TXT」→ 选路径 → 保存 | 拉到预览 → 弹框"是否保存？" → 是 → 选文件夹 → 自动命名保存 |
| 在线获取 → 直接挂载 | 拉到预览 → 选 PDF → 点挂载（**技术上已可用**，但用户不知情） | 同上 + 状态栏/弹框提示"可直接挂载" |
| 在线获取 → 编辑后挂载 | 拉到预览 → 编辑文本 → 解析 → 挂载 | 不变 |

---

## 3. 候选方案

### 3.1 弹框触发时机

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| **A. 获取成功后立即弹（推荐）** | `_poll_fetch` 处理 "ok" 分支后调用 `messagebox.askyesno` | 立即、明确 | 每次获取都弹 |
| B. 仅在状态栏显示"已获取 X 个书签"+ 单独"保存书签"按钮 | 不打断 | 用户可能错过 | UX 不直接 |
| C. 两种都保留 | 弹框 + 按钮 | 灵活 | 实现稍多 |

**决策**：A。明确符合用户描述。

### 3.2 文件夹选择

| 方案 | 描述 |
|------|------|
| **A. askdirectory（推荐）** | `filedialog.askdirectory()` → 用户选目录 → 默认文件名 `<title>_bookmarks.txt` |
| B. asksaveasfilename | 用户选完整路径 |
| C. 固定到 PDF 同目录 | 简单但违背用户描述 |

**决策**：A。直接对应用户描述"选择文件夹保存"。

### 3.3 默认文件名

| 方案 | 描述 |
|------|------|
| **A. `<title>_bookmarks.txt`（推荐）** | 用书名；sanitize 非法字符；空则用 SSID |
| B. `<ssid>_bookmarks.txt` | 永远用 SSID |
| C. 用户输入 | 多一步 |

**决策**：A。最直观。

### 3.4 书签源为空

| 方案 | 描述 |
|------|------|
| **A. 不改校验（推荐）** | `_do_mount` 已不检查 `_source_path`，无需改代码 |
| B. 加显式提示 | "来源：在线 SSID xxx" 状态 |

**决策**：A。技术上已支持；如需 UX 增强可在「0. 在线获取」区加 hint 标签。

---

## 4. 模块设计

### 4.1 新增方法 `app.py::BookmarkApp`

```python
def _prompt_save_after_fetch(self, meta: BookMeta) -> None:
    """在线获取成功后询问是否保存书签到用户选定文件夹。"""
    if not messagebox.askyesno("是否保存书签", f"已获取《{meta.title}》的书签。\n是否保存为 TXT 文件？"):
        return

    folder = filedialog.askdirectory(
        title="选择保存文件夹",
        mustexist=True,
    )
    if not folder:
        return

    filename = self._suggest_filename(meta)
    target = Path(folder) / filename
    try:
        save_bookmarks_txt(self._last_nodes, target)
    except OSError as e:
        messagebox.showerror("保存失败", str(e))
        return
    self._log_append(f"✓ 书签已保存: {target}")
    self._set_status(f"已保存: {target.name}")
    messagebox.showinfo("完成", f"书签已保存到:\n{target}")

def _suggest_filename(self, meta: BookMeta) -> str:
    """构造默认文件名：sanitize 后的 <title>_bookmarks.txt，空则用 ssid。"""
    base = (meta.title or "").strip()
    if not base:
        base = meta.ssid
    return self._sanitize_filename(base) + "_bookmarks.txt"

@staticmethod
def _sanitize_filename(name: str, max_len: int = 80) -> str:
    """移除非法字符，折叠空白，截断长度。"""
    # 1. 替换非法字符为空格
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t]', ' ', name)
    # 2. 折叠连续空白
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # 3. 截断（按字符而非字节）
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip()
    return cleaned or "bookmarks"
```

### 4.2 集成点 `_poll_fetch`

```python
def _poll_fetch(self) -> None:
    try:
        msg = self._fetch_queue.get_nowait()
        kind = msg[0]
        if kind == "ok":
            _, meta, nodes = msg
            self._book_meta = meta
            self._last_nodes = nodes
            ...
            self._update_run_button()
            # 新增：异步弹框（避免阻塞 poll 循环）
            self.after(0, lambda: self._prompt_save_after_fetch(meta))
            return
        ...
```

**为何用 `after(0, ...)`**：
- `_poll_fetch` 本身被 `after(100, self._poll_fetch)` 循环调用
- 直接弹 messagebox 会阻塞当前调度，但不会破坏 poll（因为 messagebox 是模态对话框）
- 用 `after(0, ...)` 把弹框推到下一轮事件循环，更清晰

### 4.3 书签源为空

**无需代码改动**：
- `_do_mount` 校验逻辑：`if not self._last_nodes` + `if not pdf_str`
- `_update_run_button`：`ok = bool(self._last_nodes) and bool(self._pdf_path.get().strip())`
- 在线获取后 `_last_nodes` 已填充 → 「执行挂载」按钮自动启用

**UX 增强（可选）**：
- 在「0. 在线获取」区添加 hint：`提示：获取后可直接点「⚙ 执行挂载」，无需先选书签源文件`
- 状态栏已显示 `_fetch_status`，包含书名与节点数

---

## 5. 错误处理

| 场景 | 处理 |
|------|------|
| 用户选"否" | 不保存，继续 |
| 用户取消 askdirectory | 不保存，无错误 |
| sanitize 后文件名为空 | 用 `"bookmarks"` 兜底 |
| 文件已存在 | 直接覆盖（同 `save_bookmarks_txt` 行为） |
| 写入失败 | `messagebox.showerror` + 日志 |

---

## 6. 测试策略

### 6.1 单元测试（GUI 模块）

GUI 测试需要 mock `messagebox` 和 `filedialog`：

```python
# tests/test_app_save_prompt.py
def test_sanitize_filename_removes_illegal_chars():
    from bookmark_pdf.app import BookmarkApp
    assert BookmarkApp._sanitize_filename('a/b\\c:d*e?f"g<h>i|j') == 'a b c d e f g h i j'
    assert BookmarkApp._sanitize_filename('   多   余   空  格  ') == '多 余 空 格'
    assert BookmarkApp._sanitize_filename('') == 'bookmarks'
    assert BookmarkApp._sanitize_filename('a' * 200, max_len=10) == 'a' * 10

def test_suggest_filename_uses_title():
    meta = BookMeta(ssid='12345', dxid='', isbn='', title='深度学习', author='', publish='', publish_time='', total_pages=300, cover_url=None)
    from bookmark_pdf.app import BookmarkApp
    app = BookmarkApp.__new__(BookmarkApp)  # 不调用 __init__
    assert app._suggest_filename(meta) == '深度学习_bookmarks.txt'

def test_suggest_filename_falls_back_to_ssid():
    meta = BookMeta(ssid='12345', ..., title='', ...)
    ...
    assert app._suggest_filename(meta) == '12345_bookmarks.txt'
```

### 6.2 手动验收

- 选 SSID → 获取 → 弹"是否保存？" → 是 → 选文件夹 → 验证文件存在且内容正确
- 选 SSID → 获取 → 弹"是否保存？" → 否 → 不应创建文件
- 选 SSID → 获取 → 弹 → 取消文件夹选择 → 不应创建文件
- 选 SSID → 获取 → 弹 → 选文件夹 → 但书签源空 → 点「⚙ 执行挂载」→ 应能正常挂载

---

## 7. 风险与权衡

| 风险 | 缓解 |
|------|------|
| 弹框打断用户 | 弹框是标准 yesno，用户一眼可读懂；「💾 导出 TXT」按钮仍可用 |
| 用户多次获取 → 多次弹框 | 每次获取都弹，符合预期 |
| OS 弹框体验差异 | tkinter 标准 dialog，无特殊问题 |
| sanitize 不够完善 | 用 `_sanitize_filename` 严格处理；兜底用 SSID 或 `bookmarks` |
| 文件名过长 | 截断到 80 字符 |

---

## 8. 验收标准

- [ ] 在线获取成功后立即弹"是否保存书签？"
- [ ] 选"是" → askdirectory 弹窗 → 选文件夹 → 保存为 `<书名>_bookmarks.txt`
- [ ] 选"否" → 不保存，继续
- [ ] 取消文件夹选择 → 不保存，无错误
- [ ] sanitize 非法字符生效
- [ ] 书名为空时使用 SSID
- [ ] 书签源为空时仍可点「⚙ 执行挂载」（已支持）
- [ ] 81 个旧测试 + 新增单元测试全部通过
- [ ] README 补充「在线获取后保存」用法

---

## 9. 工作量预估

| 模块 | 工作量 |
|------|--------|
| `_prompt_save_after_fetch` + `_sanitize_filename` + `_suggest_filename` 实现 | 0.5h |
| 集成到 `_poll_fetch` | 0.2h |
| 单元测试（mock + sanitize / suggest） | 0.3h |
| README + spec 更新 | 0.3h |
| 手动验收 + commit/push | 0.2h |
| **总计** | **1.5h** |