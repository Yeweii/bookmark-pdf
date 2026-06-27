#!/usr/bin/env bash
# Build standalone executable for the current platform.
#
# Usage:
#   ./packaging/build.sh           # Build
#   ./packaging/build.sh --clean   # Clean before build
#
# Output:
#   dist/BookmarkPDF/                       (onedir distribution)
#   dist/BookmarkPDF-{platform}-{arch}.zip  (distributable archive)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

CLEAN=0
for arg in "$@"; do
    case "$arg" in
        --clean) CLEAN=1 ;;
    esac
done

if [[ "$CLEAN" == 1 ]]; then
    rm -rf build dist
fi

# Ensure PyInstaller is available
python3 -c "import PyInstaller" 2>/dev/null || {
    echo "→ Installing PyInstaller..."
    pip install ".[build]"
}

# Detect platform & arch
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS-$ARCH" in
    Darwin-arm64)  PLATFORM="macos-arm64" ;;
    Darwin-x86_64) PLATFORM="macos-x64" ;;
    Linux-x86_64)  PLATFORM="linux-x64" ;;
    Linux-aarch64) PLATFORM="linux-arm64" ;;
    MINGW*-x86_64) PLATFORM="windows-x64" ;;
    *)             PLATFORM="unknown" ;;
esac

echo "→ Building for $PLATFORM..."

# Build
pyinstaller --clean packaging/bookmark_pdf.spec

# Smoke test (skip on Windows where background process behaves differently)
if [[ "$OS" == "Darwin" || "$OS" == "Linux" ]]; then
    echo "→ Smoke test..."
    if [[ "$OS" == "Darwin" ]]; then
        # macOS: launch in background, give it 2s, then kill
        ./dist/BookmarkPDF/BookmarkPDF &
        PID=$!
        sleep 2
        if kill -0 "$PID" 2>/dev/null; then
            echo "  ✓ Binary launched successfully"
            kill -9 "$PID" 2>/dev/null || true
        else
            echo "  ✗ Binary crashed on launch"
            exit 1
        fi
    fi
fi

# Create distributable archive
echo "→ Creating archive..."
cd dist
if [[ "$OS" == "MINGW"* ]]; then
    # Windows: zip
    if command -v zip &> /dev/null; then
        zip -qr "BookmarkPDF-$PLATFORM.zip" BookmarkPDF/
    else
        echo "  ! zip not found; skipping archive creation"
    fi
elif [[ "$OS" == "Darwin" || "$OS" == "Linux" ]]; then
    if [[ "$OS" == "Darwin" ]]; then
        zip -qr "BookmarkPDF-$PLATFORM.zip" BookmarkPDF/
    else
        tar -czf "BookmarkPDF-$PLATFORM.tar.gz" BookmarkPDF/
    fi
fi

echo ""
echo "✓ Build complete"
echo "  Distribution: dist/BookmarkPDF/"
[[ -f "dist/BookmarkPDF-$PLATFORM.zip" || -f "dist/BookmarkPDF-$PLATFORM.tar.gz" ]] && \
    echo "  Archive:      dist/BookmarkPDF-$PLATFORM.{zip,tar.gz}"