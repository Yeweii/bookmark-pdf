# Packaging

将 `bookmark_pdf` 打包为独立可执行文件的所有文件集中在此目录。

## 文件

| 文件 | 说明 |
|------|------|
| `bookmark_pdf.spec` | PyInstaller 配置（onedir 模式） |
| `build.sh` | 一键构建脚本 |

## 快速构建

```bash
# 从项目根目录
./packaging/build.sh           # 普通构建
./packaging/build.sh --clean   # 清理后重建
```

构建产物位于 `dist/BookmarkPDF/`（在项目根）。

## 手动构建

```bash
# 安装依赖
pip install ".[build]"

# 构建
pyinstaller --clean packaging/bookmark_pdf.spec
```

## 平台产物

| 平台 | 格式 |
|------|------|
| macOS | `dist/BookmarkPDF-macos-arm64.zip` |
| Linux | `dist/BookmarkPDF-linux-x64.tar.gz` |
| Windows | `dist/BookmarkPDF-windows-x64.zip` |

## 已知问题

### macOS `.app` BUNDLE 失败

PyInstaller 6 + Python 3.13 在 macOS 的 `.app` bundle 模式下存在 `libpython3.13.dylib` 路径问题，会导致启动失败：

```
Failed to load Python shared library '.../Frameworks/libpython3.13.dylib'
```

**当前方案**：使用 **onedir** 模式（输出为目录 + 二进制），双击 `BookmarkPDF/BookmarkPDF` 即可启动。

**未来方案**（待 PyInstaller 修复）：
- 升级到 PyInstaller 7
- 或改用 `py2app` / 手动 codesign

## 自定义构建

修改 `bookmark_pdf.spec` 中的：
- `excludes`：添加更多不需要的模块以减小体积
- `hiddenimports`：添加 PyInstaller 无法自动检测的模块
- `console`：设为 `True` 显示终端窗口（调试用）