# 书签挂载工具 · Bookmark PDF

将 **TXT** 或 **Markdown** 格式的书签文件解析为层级树，并挂载到 PDF 的 outline（书签）字段，生成可跳转的导航。

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![pypdf](https://img.shields.io/badge/pypdf-%E2%89%A54.0-green) ![GUI](https://img.shields.io/badge/GUI-Tkinter-orange)

---

## 特性

- ✅ 支持 TXT（3 种模板）+ Markdown（3 种模板）+ 自定义正则
- ✅ **在线获取书签**（api.pdfshuwu.com，按 SSID 拉取目录）
- ✅ **挂载后自动保存书签文件**（`indent-dot` 格式 TXT）
- ✅ Tkinter GUI，所见即所得操作
- ✅ 树形预览，页码异常实时标红
- ✅ 后台线程挂载，进度条 + 日志
- ✅ 三种输出策略：新文件 / 原位覆盖 / 追加
- ✅ Unicode 标题、嵌套层级、页码校验

---

## 安装

### 方式 A · 直接下载（推荐普通用户）

从 [GitHub Releases](https://github.com/Yeweii/bookmark-pdf/releases) 下载对应平台的可执行文件：

| 平台 | 文件 |
|------|------|
| macOS (Apple Silicon) | `BookmarkPDF-macos-arm64.zip` |
| macOS (Intel) | `BookmarkPDF-macos-x64.zip` |
| Windows | `BookmarkPDF-windows-x64.zip` |
| Linux | `BookmarkPDF-linux-x64.tar.gz` |

解压后运行 `BookmarkPDF/BookmarkPDF`（macOS/Linux）或 `BookmarkPDF.exe`（Windows）。

### 方式 B · pip 安装（推荐开发者）

```bash
# 从 GitHub 安装最新版本
pip install git+https://github.com/Yeweii/bookmark-pdf.git

# 或克隆后本地安装（开发模式）
git clone https://github.com/Yeweii/bookmark-pdf.git
cd bookmark-pdf
pip install -e ".[dev]"
```

安装后命令行工具 `bookmark-pdf` 可用：

```bash
bookmark-pdf        # 启动 GUI
```

### 方式 C · 从源码运行

```bash
git clone https://github.com/Yeweii/bookmark-pdf.git
cd bookmark-pdf
pip install -r requirements.txt
python -m bookmark_pdf
```

> **macOS / Linux 提示**：tkinter 通常随 Python 一起安装；如果 `import tkinter` 报错，Linux 用户请安装系统包 `python3-tk`。

---

## 运行

```bash
# 方式 1：安装后的脚本
bookmark-pdf

# 方式 2：模块方式
python -m bookmark_pdf
```

GUI 启动后会看到 6 个分区：

```
0. 在线获取（SSID → 一键拉取目录）
1. 选择文件（书签源 + PDF）
2. 解析规则（模板 + 自定义正则）
3. 预览（树形结构，页码异常标红）
4. 输出选项（新文件 / 覆盖 / 页码 -1）
5. 进度与日志
```

### 在线获取流程

1. 在「0. 在线获取」输入框填入 SSID（如 `13284383`）
2. 点击「🌐 获取书签」，后台从 `api.pdfshuwu.com` 拉取目录
3. 成功后自动填入「3. 预览」区
4. 选择对应 PDF → 点击「⚙ 执行挂载」
5. 完成后**自动保存** `<pdf>_bookmarks.txt`（与 PDF 同目录）

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
├── bookmark_pdf/        # Python 包
│   ├── parser.py        # TXT/MD 解析器
│   ├── bookmark.py      # pypdf 书签挂载
│   ├── app.py           # Tkinter GUI
│   ├── __main__.py      # CLI 入口
│   └── py.typed         # PEP 561 类型标记
├── tests/
│   ├── test_parser.py   # 解析器单元测试
│   ├── test_bookmark.py # 挂载单元测试
│   ├── test_e2e.py      # 端到端测试
│   └── fixtures/        # TXT/MD 测试夹具
├── examples/            # 示例书签文件
├── docs/                # 项目文档
│   ├── plan.md          # 实施计划
│   ├── spec.md          # 规范文档
│   └── tasks.md         # 任务清单
├── pyproject.toml       # 包配置
├── packaging/           # 打包相关
│   ├── bookmark_pdf.spec
│   ├── build.sh
│   └── README.md
├── README.md
├── LICENSE
└── requirements*.txt
```

---

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行所有测试
python -m pytest tests/

# 运行特定测试
python -m pytest tests/test_parser.py -v

# 代码行数
wc -l bookmark_pdf/*.py
```

### 打包为可执行文件

打包相关文件与产物统一在 [`packaging/`](packaging/) 目录下：

```
packaging/
├── bookmark_pdf.spec        # PyInstaller 配置
├── build.sh                 # 一键构建脚本
├── README.md                # 打包说明
├── build/                   # 中间产物（git 忽略）
└── dist/                    # 最终产物（git 忽略）
    ├── BookmarkPDF.app/              # macOS 应用包
    └── BookmarkPDF-macos-arm64.zip  # 可分发的压缩包
```

```bash
# 一键构建（推荐）
./packaging/build.sh

# 清理后重建
./packaging/build.sh --clean
```

产物全部在 `packaging/dist/` 下，**不污染根目录**。详见 [packaging/README.md](packaging/README.md)。

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

- v1.0（当前）：核心解析 + 挂载 + GUI + pip 安装 + PyInstaller 打包
- v1.1：书签模板保存/加载（用户预设）
- v1.2：批量处理（多 PDF 队列）
- v2.0：CI 自动构建多平台 release（GitHub Actions）

---

## 许可

MIT

## 致谢

- [pypdf](https://github.com/py-pdf/pypdf) — PDF 操作
- [reportlab](https://www.reportlab.com/) — 测试 PDF 生成
- [Tkinter](https://docs.python.org/3/library/tkinter.html) — GUI 框架