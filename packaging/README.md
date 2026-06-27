# Packaging

将 `bookmark_pdf` 打包为独立 `.app`（macOS）/ 可执行目录的所有文件与产物集中在此目录。

## 目录结构

```
packaging/
├── bookmark_pdf.spec     # PyInstaller 配置
├── build.sh              # 一键构建脚本
├── README.md             # 本文档
├── build/                # 中间产物（PyInstaller 工作目录，git 忽略）
└── dist/                 # 最终产物（git 忽略）
    ├── BookmarkPDF.app/              # macOS 应用包
    └── BookmarkPDF-macos-arm64.zip  # 可分发的压缩包
```

## 快速构建

```bash
# 从项目根目录
./packaging/build.sh           # 增量构建
./packaging/build.sh --clean   # 清理后重建
```

构建产物自动输出到 `packaging/dist/`。

## 手动构建

```bash
pip install ".[build]"
pyinstaller --clean \
    --workpath packaging/build \
    --distpath packaging/dist \
    packaging/bookmark_pdf.spec
```

## 平台产物

| 平台 | 产物 | 格式 |
|------|------|------|
| macOS (Apple Silicon) | `packaging/dist/BookmarkPDF.app` | .app bundle |
| macOS (Intel) | `packaging/dist/BookmarkPDF.app` | .app bundle |
| Linux | `packaging/dist/BookmarkPDF/` | onedir |
| Windows | `packaging/dist/BookmarkPDF/` | onedir |

构建脚本同时生成 `BookmarkPDF-{platform}-{arch}.zip`（macOS）或 `.tar.gz`（Linux）。

## 自定义构建

修改 `bookmark_pdf.spec` 中的：
- `excludes`：添加更多不需要的模块以减小体积
- `hiddenimports`：添加 PyInstaller 无法自动检测的模块
- `console`：设为 `True` 显示终端窗口（调试用）
- BUNDLE `info_plist`：修改应用元信息（名称、版本、权限等）

## 已知问题

### macOS Gatekeeper 警告

未签名的 `.app` 在首次打开时 macOS 会弹出安全警告。三种处理方式：

1. 右键 → 打开（绕过警告一次）
2. 系统设置 → 隐私与安全性 → 仍要打开
3. 开发者签名（需 Apple Developer 账号）：
   ```bash
   codesign --deep --force --sign "Developer ID Application: Your Name" \
       packaging/dist/BookmarkPDF.app
   ```

### PyInstaller 6 + Python 3.13

之前存在 `libpython3.13.dylib` 路径问题导致 `.app` 启动失败，已通过 PyInstaller `--clean` 重建解决。如再遇此问题，可尝试升级到 PyInstaller 7 或回退 Python 3.12。