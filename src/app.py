"""Tkinter GUI for bookmark mounting tool."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Literal

from src.bookmark import PageOutOfRangeError, mount_bookmarks
from src.parser import (
    BookmarkNode,
    ParseError,
    ParseRule,
    Parser,
)


class BookmarkApp(tk.Tk):
    """Main GUI window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("书签挂载工具")
        self.geometry("920x720")
        self.minsize(720, 600)

        # State
        self._source_path = tk.StringVar()
        self._pdf_path = tk.StringVar()
        self._rule_name = tk.StringVar(value="flat")
        self._custom_regex = tk.StringVar()
        self._level_mode = tk.StringVar(value="flat")
        self._indent_spaces = tk.IntVar(value=2)
        self._output_mode = tk.StringVar(value="new")  # "new" | "overwrite"
        self._page_offset = tk.IntVar(value=-1)
        self._status_text = tk.StringVar(value="就绪")

        # Cached parse result
        self._last_nodes: list[BookmarkNode] = []

        # Thread communication
        self._progress_queue: queue.Queue = queue.Queue()

        # Build UI
        self._build_layout()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.mainloop()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        outer = ttk.Frame(self, padding=8)
        outer.pack(fill=tk.BOTH, expand=True)

        self._build_file_section(outer)
        ttk.Separator(outer, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        self._build_rule_section(outer)
        ttk.Separator(outer, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        self._build_preview_section(outer)
        ttk.Separator(outer, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        self._build_output_section(outer)
        ttk.Separator(outer, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        self._build_progress_section(outer)

    def _build_file_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="1. 选择文件", padding=8)
        frame.pack(fill=tk.X)

        # Source (TXT/MD)
        ttk.Label(frame, text="书签源:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        ttk.Entry(frame, textvariable=self._source_path).grid(
            row=0, column=1, sticky=tk.EW, padx=4
        )
        ttk.Button(frame, text="浏览…", command=self._browse_source).grid(
            row=0, column=2, padx=4
        )

        # PDF
        ttk.Label(frame, text="PDF:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        ttk.Entry(frame, textvariable=self._pdf_path).grid(
            row=1, column=1, sticky=tk.EW, padx=4
        )
        ttk.Button(frame, text="浏览…", command=self._browse_pdf).grid(
            row=1, column=2, padx=4
        )

        frame.columnconfigure(1, weight=1)

    def _build_rule_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="2. 解析规则", padding=8)
        frame.pack(fill=tk.X)

        # Template selector
        ttk.Label(frame, text="模板:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        templates = list(Parser.BUILTIN_RULES.keys())
        cb = ttk.Combobox(
            frame, textvariable=self._rule_name, values=templates,
            state="readonly", width=24,
        )
        cb.grid(row=0, column=1, sticky=tk.W, padx=4)
        cb.bind("<<ComboboxSelected>>", lambda _e: self._on_template_changed())

        # Level mode
        ttk.Label(frame, text="层级模式:").grid(row=0, column=2, sticky=tk.W, padx=(16, 4))
        modes = ["flat", "indent", "md_header"]
        ttk.Combobox(
            frame, textvariable=self._level_mode, values=modes,
            state="readonly", width=12,
        ).grid(row=0, column=3, sticky=tk.W, padx=4)

        # Indent spaces
        ttk.Label(frame, text="缩进=N 层:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        ttk.Spinbox(
            frame, from_=1, to=8, textvariable=self._indent_spaces, width=6,
        ).grid(row=1, column=1, sticky=tk.W, padx=4)

        # Custom regex
        ttk.Label(frame, text="自定义正则:").grid(row=2, column=0, sticky=tk.W, padx=4, pady=2)
        ttk.Entry(frame, textvariable=self._custom_regex).grid(
            row=2, column=1, columnspan=3, sticky=tk.EW, padx=4
        )
        ttk.Label(
            frame,
            text="(留空则使用所选模板；正则必须含命名组 ?P<title> 与 ?P<page>)",
            foreground="#666",
        ).grid(row=3, column=1, columnspan=3, sticky=tk.W, padx=4)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=0, column=4, rowspan=2, padx=8)
        ttk.Button(btn_frame, text="↻ 重新解析", command=self._do_parse).pack(pady=2)

        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

    def _build_preview_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="3. 预览", padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        # Treeview
        cols = ("title", "page")
        self._tree = ttk.Treeview(frame, columns=cols, show="tree headings", height=10)
        self._tree.heading("#0", text="层级")
        self._tree.heading("title", text="标题")
        self._tree.heading("page", text="页码")
        self._tree.column("#0", width=120, stretch=False)
        self._tree.column("title", width=400, stretch=True)
        self._tree.column("page", width=80, stretch=False, anchor=tk.E)
        self._tree.tag_configure("error", foreground="red")
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Status bar
        self._status_label = ttk.Label(parent, textvariable=self._status_text, anchor=tk.W)
        self._status_label.pack(fill=tk.X, padx=4, pady=(2, 0))

    def _build_output_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="4. 输出选项", padding=8)
        frame.pack(fill=tk.X)

        # Output mode
        ttk.Radiobutton(
            frame, text="保存为新文件（默认）", variable=self._output_mode, value="new",
        ).grid(row=0, column=0, sticky=tk.W, padx=4)
        ttk.Radiobutton(
            frame, text="原地覆盖原 PDF", variable=self._output_mode, value="overwrite",
        ).grid(row=0, column=1, sticky=tk.W, padx=4)

        # Page offset
        ttk.Checkbutton(
            frame,
            text="页码 -1（TXT/MD 1-based → PDF 0-based）",
            variable=self._page_offset,
            onvalue=-1, offvalue=0,
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=4, pady=2)

        # Action button
        self._run_btn = ttk.Button(
            frame, text="⚙ 执行挂载", command=self._do_mount, state=tk.DISABLED,
        )
        self._run_btn.grid(row=0, column=2, rowspan=2, padx=12, ipadx=10, ipady=4)

        frame.columnconfigure(2, weight=1)

    def _build_progress_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="5. 进度与日志", padding=8)
        frame.pack(fill=tk.BOTH)

        # Progress bar
        self._progress = ttk.Progressbar(frame, mode="determinate", maximum=100)
        self._progress.pack(fill=tk.X, pady=2)

        # Log
        self._log = tk.Text(frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self._log.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        scroll = ttk.Scrollbar(self._log, orient=tk.VERTICAL, command=self._log.yview)
        self._log.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # ------------------------------------------------------------------
    # File dialogs
    # ------------------------------------------------------------------

    def _browse_source(self) -> None:
        path = filedialog.askopenfilename(
            title="选择书签文件",
            filetypes=[
                ("书签文件", "*.txt *.md"),
                ("文本文件", "*.txt"),
                ("Markdown", "*.md"),
                ("所有文件", "*.*"),
            ],
        )
        if path:
            self._source_path.set(path)
            self._do_parse()

    def _browse_pdf(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 PDF",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
        )
        if path:
            self._pdf_path.set(path)

    # ------------------------------------------------------------------
    # Parse
    # ------------------------------------------------------------------

    def _on_template_changed(self) -> None:
        name = self._rule_name.get()
        if name in Parser.BUILTIN_RULES:
            rule = Parser.BUILTIN_RULES[name]
            self._custom_regex.set(rule.line_pattern)
            self._level_mode.set(rule.level_mode)
            self._indent_spaces.set(rule.indent_spaces)

    def _current_rule(self) -> ParseRule:
        name = self._rule_name.get() or "custom"
        custom = self._custom_regex.get().strip()
        if custom:
            return ParseRule(
                name=name + "_custom",
                line_pattern=custom,
                level_mode=self._level_mode.get(),  # type: ignore[arg-type]
                indent_spaces=self._indent_spaces.get(),
            )
        if name in Parser.BUILTIN_RULES:
            return Parser.BUILTIN_RULES[name]
        # Fallback
        return Parser.BUILTIN_RULES["flat"]

    def _do_parse(self) -> None:
        source = self._source_path.get().strip()
        if not source:
            self._set_status("请先选择书签源文件")
            return
        path = Path(source)
        if not path.exists():
            self._set_status(f"文件不存在: {source}")
            return

        try:
            rule = self._current_rule()
        except ValueError as e:
            self._set_status(f"规则错误: {e}")
            return

        try:
            nodes = Parser(rule).parse_file(path)
        except ParseError as e:
            self._set_status(f"解析错误（行 {e.line_no}）: {e.reason}")
            messagebox.showerror("解析错误", str(e))
            return
        except Exception as e:
            self._set_status(f"解析失败: {e}")
            messagebox.showerror("解析失败", str(e))
            return

        self._last_nodes = nodes
        self._refresh_preview(nodes)
        self._update_run_button()

    def _refresh_preview(self, nodes: list[BookmarkNode]) -> None:
        self._tree.delete(*self._tree.get_children())
        total, errors = 0, 0
        for n in nodes:
            t, e = self._insert_node(n, parent="")
            total += t
            errors += e
        self._set_status(
            f"已解析: {total} 条书签，{len(nodes)} 个顶层节点，{errors} 条页码异常"
        )

    def _insert_node(self, node: BookmarkNode, parent: str) -> tuple[int, int]:
        total = 1
        errors = int(node.page is None)
        tags = ("error",) if node.page is None else ()
        page_str = str(node.page) if node.page is not None else "异常"
        iid = self._tree.insert(
            parent, "end", text=f"line {node.line_no}",
            values=(node.title, page_str), tags=tags,
        )
        for child in node.children:
            t, e = self._insert_node(child, parent=iid)
            total += t
            errors += e
        return total, errors

    def _update_run_button(self) -> None:
        ok = bool(self._last_nodes) and bool(self._pdf_path.get().strip())
        self._run_btn.config(state=(tk.NORMAL if ok else tk.DISABLED))

    # ------------------------------------------------------------------
    # Mount
    # ------------------------------------------------------------------

    def _do_mount(self) -> None:
        if not self._last_nodes:
            messagebox.showwarning("提示", "请先解析书签")
            return
        pdf_str = self._pdf_path.get().strip()
        if not pdf_str:
            messagebox.showwarning("提示", "请先选择 PDF")
            return
        pdf_path = Path(pdf_str)
        if not pdf_path.exists():
            messagebox.showerror("错误", f"PDF 不存在: {pdf_str}")
            return

        # Determine output
        if self._output_mode.get() == "new":
            out_path = pdf_path.with_name(pdf_path.stem + "_bookmarked.pdf")
        else:
            out_path = pdf_path

        if out_path.exists() and out_path == pdf_path:
            if not messagebox.askyesno("确认", f"将覆盖原文件:\n{out_path}\n是否继续？"):
                return

        # Disable button, start thread
        self._run_btn.config(state=tk.DISABLED)
        self._progress["value"] = 0
        self._log_clear()
        self._log_append(f"开始挂载 → {out_path}")

        thread = threading.Thread(
            target=self._mount_worker,
            args=(pdf_path, self._last_nodes, out_path),
            daemon=True,
        )
        thread.start()
        self.after(100, self._poll_progress)

    def _mount_worker(
        self,
        pdf_path: Path,
        nodes: list[BookmarkNode],
        out_path: Path,
    ) -> None:
        try:
            mount_bookmarks(
                pdf_path,
                nodes,
                out_path,
                page_offset=self._page_offset.get(),
                on_progress=lambda c, t: self._progress_queue.put(("p", c, t)),
            )
            self._progress_queue.put(("done", out_path))
        except PageOutOfRangeError as e:
            self._progress_queue.put(("err", f"页码越界（行 {e.line_no}）: {e.page}，PDF 共 {e.page_count} 页"))
        except Exception as e:
            self._progress_queue.put(("err", f"{type(e).__name__}: {e}"))

    def _poll_progress(self) -> None:
        try:
            while True:
                msg = self._progress_queue.get_nowait()
                kind = msg[0]
                if kind == "p":
                    _, c, t = msg
                    pct = (c / t * 100) if t else 0
                    self._progress["value"] = pct
                elif kind == "done":
                    out_path = msg[1]
                    self._progress["value"] = 100
                    self._log_append("✓ 完成")
                    self._run_btn.config(state=tk.NORMAL)
                    if messagebox.askyesno(
                        "完成",
                        f"书签已挂载到:\n{out_path}\n\n是否打开所在文件夹？",
                    ):
                        self._open_folder(out_path.parent)
                    return
                elif kind == "err":
                    err = msg[1]
                    self._log_append(f"✗ 失败: {err}")
                    messagebox.showerror("挂载失败", err)
                    self._run_btn.config(state=tk.NORMAL)
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll_progress)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, text: str) -> None:
        self._status_text.set(text)

    def _log_append(self, text: str) -> None:
        self._log.config(state=tk.NORMAL)
        self._log.insert(tk.END, text + "\n")
        self._log.see(tk.END)
        self._log.config(state=tk.DISABLED)

    def _log_clear(self) -> None:
        self._log.config(state=tk.NORMAL)
        self._log.delete("1.0", tk.END)
        self._log.config(state=tk.DISABLED)

    def _open_folder(self, folder: Path) -> None:
        import subprocess
        import sys
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        elif sys.platform.startswith("win"):
            subprocess.Popen(["explorer", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def main() -> int:
    from src.__main__ import check_dependencies
    if not check_dependencies():
        return 1
    app = BookmarkApp()
    app.run()
    return 0