#!/usr/bin/env bash
# Build standalone .app bundle for the current platform.
#
# Usage:
#   ./packaging/build.sh           # Build (incremental)
#   ./packaging/build.sh --clean   # Clean before build
#
# Output (all under packaging/):
#   packaging/build/   - PyInstaller intermediate working files
#   packaging/dist/    - Final .app bundle + zip

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGING_DIR="$PROJECT_ROOT/packaging"
cd "$PROJECT_ROOT"

CLEAN=0
for arg in "$@"; do
    case "$arg" in
        --clean) CLEAN=1 ;;
    esac
done

if [[ "$CLEAN" == 1 ]]; then
    rm -rf packaging/build packaging/dist
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
echo "  spec:    packaging/bookmark_pdf.spec"
echo "  work:    packaging/build/"
echo "  dist:    packaging/dist/"

# Build with output paths under packaging/
pyinstaller --clean \
    --workpath "$PACKAGING_DIR/build" \
    --distpath "$PACKAGING_DIR/dist" \
    "$PACKAGING_DIR/bookmark_pdf.spec"

# Smoke test
APP_PATH="$PACKAGING_DIR/dist/BookmarkPDF.app"
echo ""
echo "→ Smoke test: $APP_PATH"
case "$OS" in
    Darwin)
        open "$APP_PATH"
        sleep 3
        if pgrep -f "BookmarkPDF.app/Contents/MacOS/BookmarkPDF" > /dev/null; then
            echo "  ✓ Binary launched successfully"
            pkill -9 -f "BookmarkPDF.app/Contents/MacOS/BookmarkPDF" 2>/dev/null || true
        else
            echo "  ✗ Binary crashed on launch"
            exit 1
        fi
        ;;
    Linux)
        "$APP_PATH/Contents/MacOS/BookmarkPDF" 2>/dev/null &
        PID=$!
        sleep 2
        if kill -0 "$PID" 2>/dev/null; then
            echo "  ✓ Binary launched successfully"
            kill -9 "$PID" 2>/dev/null || true
        else
            echo "  ✗ Binary crashed on launch"
            exit 1
        fi
        ;;
esac

# Create distributable archive
echo ""
echo "→ Creating archive..."
cd "$PACKAGING_DIR/dist"

# Remove the loose onedir directory (only .app is needed for distribution)
if [[ "$OS" == "Darwin" && -d "BookmarkPDF" ]]; then
    rm -rf "BookmarkPDF"
fi

if [[ "$OS" == "Darwin" ]]; then
    if command -v zip &> /dev/null; then
        zip -qr "BookmarkPDF-$PLATFORM.zip" BookmarkPDF.app/
        echo "  ✓ BookmarkPDF-$PLATFORM.zip"
    fi
elif [[ "$OS" == "Linux" ]]; then
    tar -czf "BookmarkPDF-$PLATFORM.tar.gz" BookmarkPDF/
    echo "  ✓ BookmarkPDF-$PLATFORM.tar.gz"
fi

echo ""
echo "✓ Build complete"
echo "  App:      $APP_PATH"
[[ -f "$PACKAGING_DIR/dist/BookmarkPDF-$PLATFORM.zip" ]] && \
    echo "  Archive:  $PACKAGING_DIR/dist/BookmarkPDF-$PLATFORM.zip"
[[ -f "$PACKAGING_DIR/dist/BookmarkPDF-$PLATFORM.tar.gz" ]] && \
    echo "  Archive:  $PACKAGING_DIR/dist/BookmarkPDF-$PLATFORM.tar.gz"