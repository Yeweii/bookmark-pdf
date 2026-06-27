"""Entry point: validates runtime dependencies and launches GUI."""
import sys


def check_dependencies() -> bool:
    """Verify all required runtime dependencies are importable."""
    errors = []

    try:
        import pypdf  # noqa: F401
    except ImportError:
        errors.append("pypdf (pip install pypdf)")

    try:
        import tkinter  # noqa: F401
    except ImportError:
        errors.append("tkinter (system package, e.g. python3-tk)")

    if errors:
        print("Missing dependencies:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return False
    return True


def main() -> int:
    if not check_dependencies():
        return 1

    from bookmark_pdf.app import BookmarkApp

    app = BookmarkApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())