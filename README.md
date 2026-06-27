# 书签挂载工具 · Bookmark PDF

将 **TXT** 或 **Markdown** 格式的书签文件解析为层级树，并挂载到 PDF 的 outline（书签）字段，生成可跳转的导航。

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![pypdf](https://img.shields.io/badge/pypdf-%E2%89%A54.0-green) ![GUI](https://img.shields.io/badge/GUI-Tkinter-orange)

---

## 特性

- ✅ 支持 TXT（3 种模板）+ Markdown（3 种模板）+ 自定义正则
- ✅ Tkinter GUI，所见即所得操作
- ✅ 树形预览，页码异常实时标红
- ✅ 后台线程挂载，进度条 + 日志
- ✅ 三种输出策略：新文件 / 原位覆盖 / 追加
- ✅ Unicode 标题、嵌套层级、页码校验

---

## 安装

```bash
# 运行时依赖
pip install -r requirements.txt

# 开发依赖（含 pytest 与 reportlab）
pip install -r requirements-dev.txt
```

> **macOS / Linux 提示**：tkinter 通常随 Python 一起安装；如果 `import tkinter` 报错，Linux 用户请安装系统包 `python3-tk`。

---

## 运行

```bash
python -m src
```

或者：

```bash
python src/__main__.py
```

GUI 启动后会看到 5 个分区：**选择文件 → 解析规则 → 预览 → 输出选项 → 进度日志**。

---

## 支持的书签格式

### TXT 模板

| 模板 | 适用格式示例 |
|------|--------------|
| `flat` | `1 第一章`<br>`2 第二章` |
| `indent-dot` | `第一章 .......... 1`<br>`  1.1 引言 ... 2` |
| `chapter` | `第一章 引言 1`<br>`第二章 背景 5` |

### Markdown 模板

| 模板 | 适用格式示例 |
|------|--------------|
| `md-header-suffix` | `# 概述 .................. 1`<br>`## 1.1 背景 ......... 3` |
| `md-header-comment` | `# 概述 <!-- 1 -->`<br>`## 背景 <!-- 3 -->` |
| `md-toc-link` | `- [概述](#intro) 1`<br>`  - [背景](#bg) 3` |

### 自定义正则

在 GUI「自定义正则」输入框填写，需含命名组 `title` 与 `page`：

```
^(?P<page>\d+)\s+(?P<title>.+)$
```

层级模式：
- `flat`：所有匹配项同级
- `indent`：用缩进空格数 ÷ `缩进=N 层` 决定层级（默认 N=2）
- `md_header`：用标题行首 `#` 的数量决定层级

---

## 页码语义

- TXT/MD 中的页码通常是**印刷页码**（1-based）
- PDF 内部页码是 **0-based**（索引）
- GUI 默认勾选「页码 -1」自动转换；如 PDF 已是 0-based，去掉勾选

---

## 项目结构

```
bookmark_pdf/
├── src/
│   ├── parser.py        # TXT/MD 解析器
│   ├── bookmark.py      # pypdf 书签挂载
│   ├── app.py           # Tkinter GUI
│   └── __main__.py      # CLI 入口
├── tests/
│   ├── test_parser.py   # 解析器单元测试
│   ├── test_bookmark.py # 挂载单元测试
│   ├── test_e2e.py      # 端到端测试
│   └── fixtures/        # TXT/MD 测试夹具
├── examples/            # 示例书签文件
├── docs/                # 计划与规范
│   └── plan.md
├── plan.md              # 实施计划
├── spec.md              # 规范文档
├── tasks.md             # 任务清单
└── requirements.txt
```

---

## 开发

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试
python -m pytest tests/test_parser.py -v

# 代码行数
wc -l src/*.py
```

测试覆盖：
- 解析器：6 种模板、异常处理、Unicode、自定义正则
- 挂载：3 种 mode、嵌套、越界、进度回调
- 端到端：6 个夹具 + 真实 PDF

---

## 常见问题

**Q：GUI 启动后中文显示为方框？**
A：Tkinter 默认字体不含中文。macOS 通常自动处理；Linux 可安装 `fonts-noto-cjk` 或在代码中指定字体。

**Q：执行挂载时页码越界？**
A：检查 TXT/MD 中的最大页码是否 ≤ PDF 实际页数。预览中标红的条目表示页码解析异常。

**Q：自定义正则报错？**
A：必须包含命名组 `?P<title>` 与 `?P<page>`，且正则语法正确（可在 https://regex101.com 测试）。

**Q：输出 PDF 在某些阅读器中看不到书签？**
A：极少数阅读器需要手动启用「显示书签栏」。pypdf 生成的标准 outline 在 Preview / Adobe Reader / Sumatra / Foxit 等主流阅读器中均可正常显示。

**Q：能保留原 PDF 的书签吗？**
A：GUI 输出策略选「原地覆盖」时使用 `mode="append"`（保留）或 `mode="merge"`（去重）；默认为 `replace`（替换）。

---

## 路线图

- v1.0（当前）：核心解析 + 挂载 + GUI
- v1.1：书签模板保存/加载（用户预设）
- v1.2：批量处理（多 PDF 队列）
- v2.0：PyInstaller 打包 .app / .exe

---

## 许可

MIT

## 致谢

- [pypdf](https://github.com/py-pdf/pypdf) — PDF 操作
- [reportlab](https://www.reportlab.com/) — 测试 PDF 生成
- [Tkinter](https://docs.python.org/3/library/tkinter.html) — GUI 框架