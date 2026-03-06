"""
neonflood/gui.py
================
Cyberpunk-themed graphical interface for NeonFlood v2.0.

Layout (top → bottom)
----------------------
  Header bar       — tool name, version, website link, update badge
  Control panel    — target URL, mode, workers, sockets, timeout,
                     rate-limit, proxy, Tor toggle, profile manager
  Stats bar        — live STRIKES / DROPPED / RPS / TIME / MODE
  RPS graph        — live colour-gradient bar chart (last 60 seconds)
  Console          — colour-coded scrolling log output
  Bottom bar       — start/stop button, clear, export, footer

Bugs fixed vs v1.x
-------------------
  - tk.simpledialog was referenced before import; fixed with top-level import
  - Unused imports (ttk, os) removed
  - Dead attribute _rps_prev removed
  - SlowlorisWorker: added brief sleep between failed socket attempts
  - _poll_logs: console trim threshold raised and batch-deletes to avoid lag
"""

import tkinter as tk
import tkinter.simpledialog as simpledialog          # must be top-level import
from tkinter import scrolledtext, messagebox, filedialog
from multiprocessing import Manager, Queue
import threading
import queue as queue_module
import time
import webbrowser
import random
import urllib.parse
import sys

from neonflood import __version__, __author__, __website__, __tool__
from neonflood.counter  import SafeCounter
from neonflood.workers  import create_worker, MODE_MAP
from neonflood.reporter import SessionReport, SessionLogger
from neonflood.profiles import (save_profile, load_profile,
                                 list_profiles, delete_profile)
from neonflood.updater  import check_for_update


# ─────────────────────────────────────────────────────────────────────────────
#  Warning popup  (shown once on startup)
# ─────────────────────────────────────────────────────────────────────────────

def show_warning_popup(root: tk.Tk) -> None:
    """
    Display the legal disclaimer popup.

    Blocks via root.wait_window() until the user clicks the accept button.
    Deferred via root.after() so the main window is fully rendered first.

    Parameters
    ----------
    root : tk.Tk — the application root window
    """
    popup = tk.Toplevel(root)
    popup.title("NeonFlood — Warning")
    popup.configure(bg="#050505")
    popup.resizable(False, False)
    popup.attributes("-topmost", True)

    W, H = 560, 480
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    popup.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")
    popup.grab_set()
    popup.lift()
    popup.focus_force()

    # Red neon border
    border = tk.Frame(popup, bg="#FF003C", padx=2, pady=2)
    border.pack(fill="both", expand=True, padx=8, pady=8)
    inner = tk.Frame(border, bg="#0a0a0a")
    inner.pack(fill="both", expand=True, padx=1, pady=1)

    # Title (animated glitch effect)
    glitch_lbl = tk.Label(inner, text="⚠  WARNING  ⚠",
                           font=("Courier", 22, "bold"),
                           bg="#0a0a0a", fg="#FF003C")
    glitch_lbl.pack(pady=(20, 2))

    tk.Label(inner, text="[ UNAUTHORIZED USE IS ILLEGAL ]",
             font=("Courier", 9), bg="#0a0a0a", fg="#FF6600").pack(pady=(0, 10))

    tk.Frame(inner, bg="#FF003C", height=1).pack(fill="x", padx=18, pady=(0, 10))

    # Warning lines (colour escalates from green → red)
    body_frame = tk.Frame(inner, bg="#0a0a0a")
    body_frame.pack(padx=28, fill="x")
    for text, color in [
        ("»  FOR AUTHORIZED & EDUCATIONAL USE ONLY.",   "#00FF00"),
        ("»  DO NOT test systems you do not own.",       "#FFFF00"),
        ("»  DO NOT use without explicit permission.",   "#FFFF00"),
        ("»  Misuse may violate local & federal laws.",  "#FF6600"),
        ("»  You bear FULL responsibility for all use.", "#FF003C"),
    ]:
        tk.Label(body_frame, text=text, font=("Courier", 10),
                 bg="#0a0a0a", fg=color, anchor="w").pack(fill="x", pady=3)

    tk.Frame(inner, bg="#333333", height=1).pack(fill="x", padx=18, pady=(12, 8))

    # Developer credit
    dev_row = tk.Frame(inner, bg="#0a0a0a")
    dev_row.pack()
    tk.Label(dev_row, text="DEVELOPER: ",
             font=("Courier", 10), bg="#0a0a0a", fg="#555555").pack(side="left")
    tk.Label(dev_row, text=__author__,
             font=("Courier", 10, "bold"), bg="#0a0a0a", fg="#00FFFF").pack(side="left")

    # Clickable website link
    link_row = tk.Frame(inner, bg="#0a0a0a")
    link_row.pack(pady=(5, 0))
    tk.Label(link_row, text="WEBSITE:   ",
             font=("Courier", 10), bg="#0a0a0a", fg="#555555").pack(side="left")
    link = tk.Label(link_row, text="nhprince.dpdns.org  ↗",
                    font=("Courier", 10, "bold", "underline"),
                    bg="#0a0a0a", fg="#BF00FF", cursor="hand2")
    link.pack(side="left")
    link.bind("<Button-1>", lambda e: webbrowser.open(__website__))
    link.bind("<Enter>",    lambda e: link.config(fg="#FF00FF"))
    link.bind("<Leave>",    lambda e: link.config(fg="#BF00FF"))

    tk.Frame(inner, bg="#FF003C", height=1).pack(fill="x", padx=18, pady=(12, 0))

    # Accept button
    closed = {"v": False}

    def on_accept() -> None:
        closed["v"] = True
        popup.grab_release()
        popup.destroy()

    btn = tk.Button(inner, text="[ I UNDERSTAND — ENTER ]",
                    font=("Courier", 11, "bold"),
                    bg="#0a0a0a", fg="#FF003C",
                    activebackground="#FF003C", activeforeground="#000",
                    relief="flat", bd=0, padx=16, pady=9,
                    cursor="hand2", command=on_accept)
    btn.pack(pady=14)
    btn.bind("<Enter>", lambda e: btn.config(bg="#1a0000", fg="#FF6666"))
    btn.bind("<Leave>", lambda e: btn.config(bg="#0a0a0a", fg="#FF003C"))

    # Glitch animation on the title label
    _G_COLORS = ["#FF003C", "#FF6600", "#FFFF00", "#FF003C",
                  "#FFFFFF", "#FF003C", "#FF003C"]
    _G_TEXTS  = ["⚠  WARNING  ⚠", "W̴A̷R̸N̵I̶N̴G̷", "⚠  WARNING  ⚠",
                  "▓▓ WARNING ▓▓", "⚠  WARNING  ⚠", "!! WARNING !!",
                  "⚠  WARNING  ⚠"]

    def _glitch(i: int = 0) -> None:
        if closed["v"]:
            return
        try:
            glitch_lbl.config(fg=_G_COLORS[i % len(_G_COLORS)],
                               text=_G_TEXTS[i % len(_G_TEXTS)])
            popup.after(random.choice([90, 70, 180, 55, 280, 130, 400]),
                        _glitch, i + 1)
        except tk.TclError:
            pass  # popup was destroyed

    _glitch()
    root.wait_window(popup)


# ─────────────────────────────────────────────────────────────────────────────
#  Session summary popup  (shown after a session ends)
# ─────────────────────────────────────────────────────────────────────────────

def show_summary_popup(root: tk.Tk, report: SessionReport) -> None:
    """
    Show a session results popup with export buttons.

    Parameters
    ----------
    root   : tk.Tk           — parent window
    report : SessionReport   — completed session report object
    """
    popup = tk.Toplevel(root)
    popup.title("NeonFlood — Session Summary")
    popup.configure(bg="#050505")
    popup.resizable(False, False)
    popup.attributes("-topmost", True)

    W, H = 480, 420
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    popup.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")
    popup.grab_set()

    border = tk.Frame(popup, bg="#00FFFF", padx=2, pady=2)
    border.pack(fill="both", expand=True, padx=8, pady=8)
    inner = tk.Frame(border, bg="#0a0a0a")
    inner.pack(fill="both", expand=True, padx=1, pady=1)

    tk.Label(inner, text="SESSION COMPLETE",
             font=("Courier", 18, "bold"), bg="#0a0a0a", fg="#00FFFF"
             ).pack(pady=(18, 4))
    tk.Label(inner, text="[ STRIKE REPORT ]",
             font=("Courier", 9), bg="#0a0a0a", fg="#555555"
             ).pack(pady=(0, 10))

    tk.Frame(inner, bg="#00FFFF", height=1).pack(fill="x", padx=18, pady=(0, 12))

    sf = tk.Frame(inner, bg="#0a0a0a")
    sf.pack(padx=30, fill="x")

    def _row(label: str, value: str, vc: str = "#00FF00") -> None:
        f = tk.Frame(sf, bg="#0a0a0a")
        f.pack(fill="x", pady=3)
        tk.Label(f, text=f"{label:<22}", font=("Courier", 10),
                 bg="#0a0a0a", fg="#555555").pack(side="left")
        tk.Label(f, text=value, font=("Courier", 10, "bold"),
                 bg="#0a0a0a", fg=vc).pack(side="left")

    _row("Target",         report.target,                          "#00FFFF")
    _row("Mode",           report.mode.upper(),                    "#BF00FF")
    _row("Duration",       f"{report.duration}s")
    _row("Total Requests", f"{report.total_hits + report.total_fails:,}")
    _row("Successful",     f"{report.total_hits:,}",               "#00FF00")
    _row("Failed",         f"{report.total_fails:,}",              "#FF0000")
    _row("Avg RPS",        f"{report.avg_rps}",                    "#FFFF00")
    _row("Peak RPS",       f"{report.peak_rps}",                   "#FF6600")

    tk.Frame(inner, bg="#333333", height=1).pack(fill="x", padx=18, pady=(12, 8))

    btn_frame = tk.Frame(inner, bg="#0a0a0a")
    btn_frame.pack(pady=6)

    def _export_json() -> None:
        path = filedialog.asksaveasfilename(
            parent=popup,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export JSON Report",
        )
        if path:
            report.export_json(path)
            messagebox.showinfo("Exported", f"JSON report saved to:\n{path}",
                                parent=popup)

    def _export_csv() -> None:
        path = filedialog.asksaveasfilename(
            parent=popup,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export CSV Report",
        )
        if path:
            report.export_csv(path)
            messagebox.showinfo("Exported", f"CSV report saved to:\n{path}",
                                parent=popup)

    for label, cmd, fg in [
        ("[ EXPORT JSON ]", _export_json,  "#00FFFF"),
        ("[ EXPORT CSV  ]", _export_csv,   "#FFFF00"),
        ("[ CLOSE ]",       popup.destroy, "#555555"),
    ]:
        b = tk.Button(btn_frame, text=label,
                      font=("Courier", 10, "bold"),
                      bg="#0d0d0d", fg=fg,
                      activebackground=fg, activeforeground="#000",
                      relief="flat", cursor="hand2",
                      padx=10, pady=6, command=cmd)
        b.pack(side="left", padx=6)


# ─────────────────────────────────────────────────────────────────────────────
#  Live RPS bar-graph widget
# ─────────────────────────────────────────────────────────────────────────────

class RPSGraph(tk.Canvas):
    """
    A live updating bar chart that displays up to MAX_POINTS RPS samples.

    Bars are colour-coded green → yellow → red proportionally to peak value.
    Grid lines are drawn at 25 % / 50 % / 75 % / 100 % of peak RPS.
    """

    MAX_POINTS = 60   # number of seconds of history to display

    def __init__(self, parent: tk.Widget, **kwargs):
        super().__init__(parent, bg="#000000", highlightthickness=0, **kwargs)
        self._data: list[int] = []
        self.bind("<Configure>", lambda _e: self._redraw())

    def push(self, rps: int) -> None:
        """Append one RPS sample and refresh the canvas."""
        self._data.append(rps)
        if len(self._data) > self.MAX_POINTS:
            self._data.pop(0)
        self._redraw()

    def clear(self) -> None:
        """Erase all stored samples and redraw the empty canvas."""
        self._data = []
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 4 or h < 4:
            return

        self._draw_grid(w, h)

        if not self._data:
            return

        peak = max(self._data) or 1
        bar_w = max(1, w // self.MAX_POINTS)

        for i, val in enumerate(self._data):
            x1 = i * (w / self.MAX_POINTS)
            x2 = x1 + bar_w - 1
            bar_h = int((val / peak) * (h - 16))
            if bar_h < 1:
                continue
            y1 = h - bar_h
            y2 = h
            ratio = val / peak
            if ratio < 0.5:
                r = int(ratio * 2 * 255)
                g = 255
            else:
                r = 255
                g = int((1.0 - (ratio - 0.5) * 2) * 255)
            self.create_rectangle(x1, y1, x2, y2,
                                  fill=f"#{r:02x}{g:02x}00", outline="")

        # Labels
        self.create_text(4, 4, anchor="nw",
                         text=f"PEAK: {int(peak)} rps",
                         fill="#444444", font=("Courier", 8))
        self.create_text(w - 4, 4, anchor="ne",
                         text=f"NOW: {int(self._data[-1])} rps",
                         fill="#00FF00", font=("Courier", 8))

    def _draw_grid(self, w: int, h: int) -> None:
        step_y = max(8, h // 4)
        for y in range(0, h, step_y):
            self.create_line(0, y, w, y, fill="#111111")
        step_x = max(8, w // 12)
        for x in range(0, w, step_x):
            self.create_line(x, 0, x, h, fill="#111111")


# ─────────────────────────────────────────────────────────────────────────────
#  Main application class
# ─────────────────────────────────────────────────────────────────────────────

class NeonFloodGUI:
    """
    Main GUI application for NeonFlood.

    Manages the full lifecycle of a test session:
      - Input validation
      - Worker process creation and teardown
      - Live stats polling and display
      - Log forwarding to the console widget
      - Profile save/load
      - Session report export
      - Background update check
    """

    def __init__(self, root: tk.Tk):
        self.root       = root
        self.active     = False
        self.workers: list = []
        self.log_queue  = Queue()
        self.manager    = None
        self.counter    = None
        self.report     = SessionReport()
        self.logger     = None
        self._start_ts  = None

        self.root.title(f"NeonFlood v{__version__}")
        self.root.geometry("980x870")
        self.root.configure(bg="#050505")
        self.root.resizable(True, True)

        self._build_ui()

        # Defer warning popup until the main window is rendered
        self.root.after(200, lambda: show_warning_popup(self.root))
        # Start background update check 3 s after launch
        self.root.after(3000, self._check_update_async)

        threading.Thread(target=self._poll_logs, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────
    #  UI construction
    # ─────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self._build_header()
        self._build_controls()
        self._build_stats_bar()
        self._build_rps_graph()
        self._build_console()
        self._build_bottom_bar()

    def _build_header(self) -> None:
        hdr = tk.Frame(self.root, bg="#050505")
        hdr.pack(fill="x", padx=20, pady=(12, 0))

        tk.Label(hdr, text=f">> {__tool__} <<",
                 font=("Fixedsys", 22), bg="#050505",
                 fg="#00FF00").pack(side="left")

        tk.Label(hdr, text=f"v{__version__}",
                 font=("Courier", 10), bg="#050505",
                 fg="#333333").pack(side="left", padx=8)

        # Update available badge — populated by _show_update_badge()
        self._update_badge = tk.Label(hdr, text="",
                                       font=("Courier", 9),
                                       bg="#050505", fg="#FFFF00",
                                       cursor="hand2")
        self._update_badge.pack(side="right", padx=10)

        link = tk.Label(hdr, text="nhprince.dpdns.org ↗",
                        font=("Courier", 9, "underline"),
                        bg="#050505", fg="#BF00FF", cursor="hand2")
        link.pack(side="right", padx=4)
        link.bind("<Button-1>", lambda _e: webbrowser.open(__website__))
        link.bind("<Enter>",    lambda _e: link.config(fg="#FF00FF"))
        link.bind("<Leave>",    lambda _e: link.config(fg="#BF00FF"))

        tk.Frame(self.root, bg="#1a1a1a", height=1).pack(
            fill="x", padx=20, pady=(8, 0))

    def _build_controls(self) -> None:
        ctrl = tk.Frame(self.root, bg="#0d0d0d")
        ctrl.pack(fill="x", padx=20, pady=6)

        def _label(text, row, col, **kw):
            tk.Label(ctrl, text=text, bg="#0d0d0d", fg="#00FF00",
                     font=("Courier", 10), **kw).grid(row=row, column=col,
                                                       padx=(10, 4), pady=8,
                                                       sticky="w")

        def _spinbox(row, col, frm, to, default, **kw):
            sb = tk.Spinbox(ctrl, from_=frm, to=to, width=4,
                            bg="#111", fg="#00FF00", font=("Courier", 10),
                            buttonbackground="#222", relief="flat",
                            insertbackground="#00FF00",
                            highlightthickness=1, highlightcolor="#00FF00",
                            highlightbackground="#333", **kw)
            sb.delete(0, tk.END)
            sb.insert(0, str(default))
            sb.grid(row=row, column=col, pady=8, ipady=2)
            return sb

        # ── Row 0: target URL ───────────────────────────────────────────
        _label("TARGET:", 0, 0)
        self.url_entry = tk.Entry(ctrl, width=40,
                                   bg="#111", fg="#00FF00",
                                   font=("Courier", 10), relief="flat",
                                   insertbackground="#00FF00",
                                   highlightthickness=1,
                                   highlightcolor="#00FF00",
                                   highlightbackground="#333")
        self.url_entry.insert(0, "http://")
        self.url_entry.grid(row=0, column=1, columnspan=2,
                             pady=8, ipady=4, padx=(0, 10), sticky="w")

        _label("MODE:", 0, 3, padx=(0, 4))
        self.mode_var = tk.StringVar(value="get")
        mode_menu = tk.OptionMenu(ctrl, self.mode_var, *list(MODE_MAP.keys()))
        mode_menu.config(bg="#111", fg="#BF00FF", font=("Courier", 10),
                         relief="flat", highlightthickness=0,
                         activebackground="#1a001a",
                         activeforeground="#FF00FF", cursor="hand2")
        mode_menu["menu"].config(bg="#111", fg="#BF00FF",
                                  font=("Courier", 10),
                                  activebackground="#1a001a")
        mode_menu.grid(row=0, column=4, padx=(0, 10))

        # ── Row 1: workers / sockets / timeout / rate-limit ────────────
        _label("WORKERS:", 1, 0)
        self.w_spin = _spinbox(1, 1, 1, 50, 5)

        _label("SOCKETS:", 1, 2, padx=(10, 4))
        self.sock_spin = _spinbox(1, 3, 1, 500, 50)

        _label("TIMEOUT:", 1, 4, padx=(10, 4))
        self.timeout_spin = _spinbox(1, 5, 1, 60, 5)

        # ── Row 2: rate limit / proxy / Tor ────────────────────────────
        _label("RATE LIMIT:", 2, 0)
        self.rate_entry = tk.Entry(ctrl, width=7,
                                    bg="#111", fg="#FFFF00",
                                    font=("Courier", 10), relief="flat",
                                    insertbackground="#FFFF00",
                                    highlightthickness=1,
                                    highlightcolor="#FFFF00",
                                    highlightbackground="#333")
        self.rate_entry.insert(0, "0")
        self.rate_entry.grid(row=2, column=1, pady=8, ipady=2, sticky="w")

        tk.Label(ctrl, text="rps (0=off)", bg="#0d0d0d", fg="#333333",
                 font=("Courier", 8)).grid(row=2, column=2, padx=(2, 8), sticky="w")

        _label("PROXY:", 2, 3, padx=(0, 4))
        self.proxy_entry = tk.Entry(ctrl, width=32,
                                     bg="#111", fg="#333333",
                                     font=("Courier", 10), relief="flat",
                                     insertbackground="#FF6600",
                                     highlightthickness=1,
                                     highlightcolor="#FF6600",
                                     highlightbackground="#333")
        self._proxy_placeholder = "socks5://127.0.0.1:1080  (optional)"
        self.proxy_entry.insert(0, self._proxy_placeholder)
        self.proxy_entry.bind("<FocusIn>",  self._proxy_focus_in)
        self.proxy_entry.bind("<FocusOut>", self._proxy_focus_out)
        self.proxy_entry.grid(row=2, column=4, columnspan=2,
                               pady=8, ipady=4, sticky="w")

        self.tor_var = tk.BooleanVar(value=False)
        tk.Checkbutton(ctrl, text="TOR",
                       variable=self.tor_var,
                       bg="#0d0d0d", fg="#BF00FF",
                       selectcolor="#0d0d0d",
                       activebackground="#0d0d0d",
                       activeforeground="#FF00FF",
                       font=("Courier", 10),
                       cursor="hand2").grid(row=2, column=6, padx=(6, 10))

        # ── Row 3: profile manager ──────────────────────────────────────
        _label("PROFILE:", 3, 0, padx=(10, 4))
        self.profile_var = tk.StringVar(value="-- select --")
        self._profile_names = ["-- select --"] + list_profiles()
        self.profile_menu = tk.OptionMenu(
            ctrl, self.profile_var, *self._profile_names,
            command=self._on_profile_selected,
        )
        self.profile_menu.config(bg="#111", fg="#00FFFF",
                                  font=("Courier", 10),
                                  relief="flat", highlightthickness=0,
                                  cursor="hand2")
        self.profile_menu["menu"].config(bg="#111", fg="#00FFFF",
                                          font=("Courier", 10))
        self.profile_menu.grid(row=3, column=1, columnspan=2,
                                pady=(0, 10), sticky="w")

        tk.Button(ctrl, text="[SAVE]",
                  font=("Courier", 9, "bold"),
                  bg="#0d0d0d", fg="#00FFFF",
                  relief="flat", cursor="hand2",
                  activebackground="#00FFFF", activeforeground="#000",
                  command=self._save_profile
                  ).grid(row=3, column=3, padx=4, pady=(0, 10))

        tk.Button(ctrl, text="[DEL]",
                  font=("Courier", 9, "bold"),
                  bg="#0d0d0d", fg="#FF0000",
                  relief="flat", cursor="hand2",
                  activebackground="#FF0000", activeforeground="#000",
                  command=self._delete_profile
                  ).grid(row=3, column=4, padx=4, pady=(0, 10))

    def _proxy_focus_in(self, _event) -> None:
        if self.proxy_entry.get() == self._proxy_placeholder:
            self.proxy_entry.delete(0, tk.END)
            self.proxy_entry.config(fg="#FF6600")

    def _proxy_focus_out(self, _event) -> None:
        if not self.proxy_entry.get().strip():
            self.proxy_entry.insert(0, self._proxy_placeholder)
            self.proxy_entry.config(fg="#333333")

    def _build_stats_bar(self) -> None:
        sf = tk.Frame(self.root, bg="#050505")
        sf.pack(fill="x", padx=20, pady=4)

        self.hits_lbl = tk.Label(sf, text="STRIKES: 0",
                                  font=("Courier", 13, "bold"),
                                  bg="#050505", fg="#00FF00")
        self.hits_lbl.pack(side="left", padx=20)

        self.fails_lbl = tk.Label(sf, text="DROPPED: 0",
                                   font=("Courier", 13, "bold"),
                                   bg="#050505", fg="#FF0000")
        self.fails_lbl.pack(side="left", padx=20)

        self.rps_lbl = tk.Label(sf, text="RPS: —",
                                 font=("Courier", 13, "bold"),
                                 bg="#050505", fg="#FFFF00")
        self.rps_lbl.pack(side="left", padx=20)

        self.timer_lbl = tk.Label(sf, text="TIME: 00:00:00",
                                   font=("Courier", 13, "bold"),
                                   bg="#050505", fg="#555555")
        self.timer_lbl.pack(side="left", padx=20)

        self.mode_lbl = tk.Label(sf, text="MODE: —",
                                  font=("Courier", 13, "bold"),
                                  bg="#050505", fg="#BF00FF")
        self.mode_lbl.pack(side="right", padx=20)

    def _build_rps_graph(self) -> None:
        gf = tk.Frame(self.root, bg="#050505")
        gf.pack(fill="x", padx=20, pady=(0, 4))
        tk.Label(gf, text="RPS GRAPH (60s):",
                 font=("Courier", 8), bg="#050505",
                 fg="#333333").pack(anchor="w")
        self.rps_graph = RPSGraph(gf, height=60)
        self.rps_graph.pack(fill="x")

    def _build_console(self) -> None:
        self.console = scrolledtext.ScrolledText(
            self.root, height=16,
            bg="#000000", fg="#00FF00",
            font=("Courier", 9), relief="flat",
            insertbackground="#00FF00",
        )
        self.console.pack(fill="both", expand=True, padx=20, pady=(0, 4))
        # Colour tags for log levels
        self.console.tag_config("HIT",  foreground="#00FF00")
        self.console.tag_config("FAIL", foreground="#FF0000")
        self.console.tag_config("WARN", foreground="#FFFF00")
        self.console.tag_config("LOAD", foreground="#BF00FF")
        self.console.tag_config("SYS",  foreground="#00FFFF")
        self.console.tag_config("TS",   foreground="#333333")

    def _build_bottom_bar(self) -> None:
        bf = tk.Frame(self.root, bg="#050505")
        bf.pack(fill="x", padx=20, pady=(0, 12))

        self.btn = tk.Button(bf, text="[ INITIALIZE STRIKE ]",
                              font=("Courier", 12, "bold"),
                              bg="#0d0d0d", fg="#00FF00",
                              activebackground="#00FF00",
                              activeforeground="#000",
                              relief="flat", cursor="hand2",
                              padx=20, pady=10,
                              command=self.toggle)
        self.btn.pack(side="left", padx=(0, 10))
        self.btn.bind("<Enter>", lambda _e: self.btn.config(bg="#001a00"))
        self.btn.bind("<Leave>", lambda _e: self.btn.config(bg="#0d0d0d"))

        tk.Button(bf, text="[CLR]",
                  font=("Courier", 10, "bold"),
                  bg="#0d0d0d", fg="#333333",
                  relief="flat", cursor="hand2",
                  activebackground="#333333", activeforeground="#000",
                  command=lambda: self.console.delete("1.0", tk.END)
                  ).pack(side="left", padx=4)

        tk.Button(bf, text="[EXPORT]",
                  font=("Courier", 10, "bold"),
                  bg="#0d0d0d", fg="#00FFFF",
                  relief="flat", cursor="hand2",
                  activebackground="#00FFFF", activeforeground="#000",
                  command=self._quick_export
                  ).pack(side="left", padx=4)

        tk.Label(bf, text=f"NeonFlood v{__version__}  //  {__author__}",
                 font=("Courier", 8), bg="#050505",
                 fg="#222222").pack(side="right")

    # ─────────────────────────────────────────────────────────────────────
    #  Input validation helpers
    # ─────────────────────────────────────────────────────────────────────

    def _validate_url(self, url: str) -> bool:
        """Return True if url is a well-formed HTTP/HTTPS URL."""
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            messagebox.showerror("INVALID INPUT",
                                  "URL must start with http:// or https://",
                                  parent=self.root)
            return False
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.netloc or not parsed.hostname:
                raise ValueError("Missing hostname")
            if parsed.port and not (1 <= parsed.port <= 65535):
                raise ValueError(f"Port {parsed.port} out of valid range")
        except ValueError as exc:
            messagebox.showerror("INVALID INPUT",
                                  f"Malformed URL: {exc}",
                                  parent=self.root)
            return False
        return True

    def _read_config(self) -> dict | None:
        """
        Read and validate all control panel values.

        Returns a config dict on success, or None if any value is invalid.
        """
        try:
            workers = int(self.w_spin.get())
            sockets = int(self.sock_spin.get())
            timeout = int(self.timeout_spin.get())
            rate    = int(self.rate_entry.get())
            if workers < 1 or sockets < 1 or timeout < 1 or rate < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "INVALID INPUT",
                "Workers / Sockets / Timeout must be positive integers.\n"
                "Rate Limit must be 0 or greater.",
                parent=self.root,
            )
            return None

        proxy_raw = self.proxy_entry.get().strip()
        proxy = None
        if proxy_raw and proxy_raw != self._proxy_placeholder:
            proxy = proxy_raw

        # Tor toggle overrides proxy field
        if self.tor_var.get():
            proxy = "socks5://127.0.0.1:9050"

        return {
            "target":  self.url_entry.get().strip(),
            "mode":    self.mode_var.get(),
            "workers": workers,
            "sockets": sockets,
            "timeout": timeout,
            "rate":    rate,
            "proxy":   proxy,
        }

    @staticmethod
    def _parse_proxy(proxy_str: str | None) -> tuple | None:
        """
        Parse a proxy URL string into a (scheme, host, port) tuple.

        Returns None if the string is empty/None or cannot be parsed.
        """
        if not proxy_str:
            return None
        try:
            p = urllib.parse.urlparse(proxy_str)
            return (p.scheme, p.hostname, p.port or 1080)
        except Exception:
            return None

    # ─────────────────────────────────────────────────────────────────────
    #  Log polling  (daemon thread → main thread via after())
    # ─────────────────────────────────────────────────────────────────────

    def _poll_logs(self) -> None:
        """
        Background thread that drains the log queue and appends entries to
        the console widget.  Also writes to the session log file if active.

        Trims the console when it exceeds 1 200 lines to prevent memory
        growth during long sessions (deletes 200 lines at a time).
        """
        while True:
            try:
                level, msg = self.log_queue.get(timeout=0.1)
                ts = time.strftime("%H:%M:%S")
                self.console.insert(tk.END, f"[{ts}] ", "TS")
                self.console.insert(tk.END, f"{level}: {msg}\n", level)
                self.console.see(tk.END)
                # Trim when console exceeds 1 200 lines
                line_count = int(self.console.index("end-1c").split(".")[0])
                if line_count > 1200:
                    self.console.delete("1.0", "201.0")
                if self.logger:
                    self.logger.write(level, msg)
            except queue_module.Empty:
                continue
            except Exception as exc:
                print(f"[poll_logs] {exc}", file=sys.stderr)

    # ─────────────────────────────────────────────────────────────────────
    #  Live stats updater  (scheduled via root.after())
    # ─────────────────────────────────────────────────────────────────────

    def _update_stats(self) -> None:
        """
        Poll the shared counters every second and update all stat labels,
        the RPS graph, and the session timer.  Re-schedules itself while
        a session is active.
        """
        if not self.active or not self.counter:
            return

        hits  = self.counter.hit_count
        fails = self.counter.fail_count
        self.hits_lbl.config(text=f"STRIKES: {hits:,}")
        self.fails_lbl.config(text=f"DROPPED: {fails:,}")

        rps = self.counter.reset_rps_tick()
        self.rps_lbl.config(text=f"RPS: {rps}")
        self.rps_graph.push(rps)
        self.report.record_rps(rps)

        if self._start_ts:
            elapsed = int(time.time() - self._start_ts)
            h, rem  = divmod(elapsed, 3600)
            m, s    = divmod(rem, 60)
            self.timer_lbl.config(text=f"TIME: {h:02d}:{m:02d}:{s:02d}",
                                   fg="#00FFFF")

        self.root.after(1000, self._update_stats)

    # ─────────────────────────────────────────────────────────────────────
    #  Session start / stop
    # ─────────────────────────────────────────────────────────────────────

    def toggle(self) -> None:
        """Start a session if idle, or stop the current session."""
        if not self.active:
            self._start()
        else:
            self._shutdown()

    def _start(self) -> None:
        cfg = self._read_config()
        if cfg is None:
            return
        if not self._validate_url(cfg["target"]):
            return

        parsed  = urllib.parse.urlparse(cfg["target"])
        host    = parsed.hostname
        port    = parsed.port or (443 if parsed.scheme == "https" else 80)
        path    = parsed.path or "/"
        use_ssl = parsed.scheme == "https"
        proxy   = self._parse_proxy(cfg["proxy"])

        self.manager    = Manager()
        self.counter    = SafeCounter(self.manager)
        self.logger     = SessionLogger()
        self.active     = True
        self._start_ts  = time.time()

        self.report.start(
            target=cfg["target"], mode=cfg["mode"],
            workers=cfg["workers"], sockets=cfg["sockets"],
            proxy=cfg["proxy"], rate_limit=cfg["rate"],
        )

        self.btn.config(text="[ TERMINATE SESSION ]", fg="#FF0000")
        self.mode_lbl.config(text=f"MODE: {cfg['mode'].upper()}")
        self.timer_lbl.config(fg="#00FFFF")
        self.rps_graph.clear()

        self.log_queue.put(("SYS",
            f"ENGINE STARTING — target={cfg['target']}"))
        self.log_queue.put(("SYS",
            f"mode={cfg['mode'].upper()}  workers={cfg['workers']}  "
            f"sockets={cfg['sockets']}  timeout={cfg['timeout']}s  "
            f"rate_limit={cfg['rate']} rps"))
        if cfg["proxy"]:
            self.log_queue.put(("SYS", f"proxy={cfg['proxy']}"))

        for _ in range(cfg["workers"]):
            p = create_worker(
                mode=cfg["mode"], host=host, port=port, path=path,
                use_ssl=use_ssl, nr_socks=cfg["sockets"],
                counter=self.counter, log_queue=self.log_queue,
                timeout=cfg["timeout"], proxy=proxy,
                rate_limit=cfg["rate"],
            )
            p.daemon = True
            p.start()
            self.workers.append(p)

        self._update_stats()

    def _shutdown(self) -> None:
        self.active = False

        # Signal workers to exit cleanly first
        for p in self.workers:
            try:
                p.stop()
            except Exception:
                pass
        time.sleep(0.3)
        # Force-terminate any that did not exit
        for p in self.workers:
            try:
                p.terminate()
                p.join(timeout=2)
            except Exception:
                pass
        self.workers.clear()

        hits  = self.counter.hit_count  if self.counter else 0
        fails = self.counter.fail_count if self.counter else 0
        self.report.finish(hits, fails)

        if self.manager:
            try:
                self.manager.shutdown()
            except Exception:
                pass
            self.manager = None
        self.counter = None

        if self.logger:
            self.logger.close()
            self.logger = None

        self.btn.config(text="[ INITIALIZE STRIKE ]", fg="#00FF00")
        self.timer_lbl.config(fg="#555555")
        self.mode_lbl.config(text="MODE: —")
        self.rps_lbl.config(text="RPS: —")
        self.log_queue.put(("SYS",
            f"SESSION TERMINATED — hits={hits:,}  fails={fails:,}  "
            f"avg_rps={self.report.avg_rps}  peak_rps={self.report.peak_rps}"))

        # Show summary 300 ms later so the console log entry appears first
        self.root.after(300, lambda: show_summary_popup(self.root, self.report))

    # ─────────────────────────────────────────────────────────────────────
    #  Profile management
    # ─────────────────────────────────────────────────────────────────────

    def _read_ui_as_config(self) -> dict:
        """Return current UI control values as a serialisable dict."""
        return {
            "target":     self.url_entry.get(),
            "mode":       self.mode_var.get(),
            "workers":    self.w_spin.get(),
            "sockets":    self.sock_spin.get(),
            "timeout":    self.timeout_spin.get(),
            "proxy":      self.proxy_entry.get(),
            "rate_limit": self.rate_entry.get(),
        }

    def _apply_config_to_ui(self, cfg: dict) -> None:
        """Populate all UI controls from a config dict."""
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, cfg.get("target", "http://"))

        self.mode_var.set(cfg.get("mode", "get"))

        self.w_spin.delete(0, tk.END)
        self.w_spin.insert(0, str(cfg.get("workers", 5)))

        self.sock_spin.delete(0, tk.END)
        self.sock_spin.insert(0, str(cfg.get("sockets", 50)))

        self.timeout_spin.delete(0, tk.END)
        self.timeout_spin.insert(0, str(cfg.get("timeout", 5)))

        self.rate_entry.delete(0, tk.END)
        self.rate_entry.insert(0, str(cfg.get("rate_limit", 0)))

        proxy = cfg.get("proxy", "")
        self.proxy_entry.delete(0, tk.END)
        if proxy and proxy != self._proxy_placeholder:
            self.proxy_entry.insert(0, proxy)
            self.proxy_entry.config(fg="#FF6600")
        else:
            self.proxy_entry.insert(0, self._proxy_placeholder)
            self.proxy_entry.config(fg="#333333")

    def _save_profile(self) -> None:
        name = simpledialog.askstring(
            "Save Profile", "Enter a profile name:",
            parent=self.root,
        )
        if not name:
            return
        save_profile(name, self._read_ui_as_config())
        self._refresh_profile_menu()
        messagebox.showinfo("Profile Saved",
                             f"Profile '{name}' saved.",
                             parent=self.root)

    def _on_profile_selected(self, name: str) -> None:
        if name == "-- select --":
            return
        cfg = load_profile(name)
        if cfg:
            self._apply_config_to_ui(cfg)

    def _delete_profile(self) -> None:
        name = self.profile_var.get()
        if name == "-- select --":
            return
        delete_profile(name)
        self._refresh_profile_menu()
        messagebox.showinfo("Profile Deleted",
                             f"Profile '{name}' deleted.",
                             parent=self.root)

    def _refresh_profile_menu(self) -> None:
        """Rebuild the profile dropdown after a save or delete."""
        self._profile_names = ["-- select --"] + list_profiles()
        menu = self.profile_menu["menu"]
        menu.delete(0, tk.END)
        for name in self._profile_names:
            menu.add_command(
                label=name,
                command=lambda n=name: (
                    self.profile_var.set(n),
                    self._on_profile_selected(n),
                ),
            )
        self.profile_var.set("-- select --")

    # ─────────────────────────────────────────────────────────────────────
    #  Quick export
    # ─────────────────────────────────────────────────────────────────────

    def _quick_export(self) -> None:
        """Open the session summary / export popup from the bottom bar."""
        if not self.report.start_time:
            messagebox.showwarning("No Data",
                                    "No session data to export yet.",
                                    parent=self.root)
            return
        show_summary_popup(self.root, self.report)

    # ─────────────────────────────────────────────────────────────────────
    #  Background update checker
    # ─────────────────────────────────────────────────────────────────────

    def _check_update_async(self) -> None:
        """Spawn a daemon thread to check GitHub for a newer release."""
        def _check() -> None:
            try:
                has_update, latest, url = check_for_update()
                if has_update:
                    self.root.after(
                        0, lambda: self._show_update_badge(latest, url))
            except Exception:
                pass

        threading.Thread(target=_check, daemon=True).start()

    def _show_update_badge(self, latest: str, url: str) -> None:
        """Display the update badge in the header and log a SYS message."""
        self._update_badge.config(text=f"⬆ UPDATE v{latest} AVAILABLE")
        self._update_badge.bind("<Button-1>",
                                 lambda _e: webbrowser.open(url))
        self.log_queue.put(
            ("SYS", f"New version available: v{latest} — {url}"))


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────

def launch_gui() -> None:
    """Create the root Tk window and start the NeonFlood GUI event loop."""
    root = tk.Tk()
    NeonFloodGUI(root)
    root.mainloop()
