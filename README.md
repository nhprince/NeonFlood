# NeonFlood

<p align="center">
  <img src="https://img.shields.io/badge/version-2.0.0-red?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/python-3.10+-green?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-blue?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/license-Educational%20Use%20Only-yellow?style=for-the-badge"/>
</p>

<p align="center">
  <b>Professional HTTP stress testing suite with cyberpunk GUI and full CLI.</b><br/>
  Developer: <a href="https://nhprince.dpdns.org">NH Prince</a>
</p>

---

> ⚠️ **LEGAL DISCLAIMER**
> NeonFlood is for **authorized and educational use only**.
> Do **NOT** use this tool against systems you do not own or have explicit permission to test.
> Misuse may violate local, national, and international laws.
> **You bear full legal responsibility for all use.**

---

## Table of Contents

- [Features](#features)
- [Attack Modes](#attack-modes)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage — GUI](#usage--gui)
- [Usage — CLI](#usage--cli)
- [CLI Reference](#cli-reference)
- [Proxy & Tor Support](#proxy--tor-support)
- [Profiles](#profiles)
- [Reports & Logs](#reports--logs)
- [Project Structure](#project-structure)
- [Changelog](#changelog)
- [Credits](#credits)

---

## Features

| Feature | Description |
|---|---|
| **4 Attack Modes** | GET flood, POST flood, HEAD flood, Slowloris |
| **GUI + CLI** | Full cyberpunk GUI and headless terminal mode |
| **Live RPS Graph** | Real-time colour-gradient bar chart (60-second history) |
| **User-Agent Rotation** | 48+ real browser User-Agents rotated per request |
| **Randomized Headers** | Accept, Accept-Language, Referer, Cache-Control vary per request |
| **SOCKS5 / HTTP Proxy** | Route traffic through any proxy or Tor |
| **Rate Limiter** | Cap requests/sec per worker with `--ratelimit` |
| **JSON / CSV Export** | Full session report with RPS history after every session |
| **Session Logging** | Auto-saved timestamped log files in `~/.neonflood/logs/` |
| **Named Profiles** | Save and reload named test configurations |
| **Auto-Update Check** | Silently checks GitHub for newer releases on startup |
| **Session Timer** | Live HH:MM:SS elapsed timer in GUI and CLI |
| **Session Summary** | Pop-up summary of hits, fails, avg/peak RPS after each session |

---

## Attack Modes

### `get` — GET Flood
Opens N connections per worker, sends randomized GET requests with unique
query strings and rotated headers, reads responses, repeats. Most common
flood type.

### `post` — POST Flood
Same as GET flood but sends 256–2048 bytes of random body data per request.
Tests upload rate-limiting and POST request parsing.

### `head` — HEAD Flood
Sends HEAD requests (no response body). Maximum connection rate at minimum
bandwidth. Tests connection pool limits.

### `slowloris` — Slowloris
Opens raw TCP sockets and sends **partial** HTTP headers — never completing
the request. Every 15 seconds a new header line is sent to keep each
connection alive. The server holds every slot open indefinitely,
exhausting its connection pool. Effective with very little bandwidth.

---

## Requirements

- **Python** 3.10 or newer
- **tkinter** (included with Python on Windows/macOS; install separately on Linux)
- **PySocks** *(optional — required only for `--proxy` / `--tor`)*

---

## Installation

### Linux (Debian / Ubuntu / Kali)

```bash
# Install system dependencies
sudo apt update
sudo apt install python3 python3-tk python3-pip

# Clone the repository
git clone https://github.com/nhprince/NeonFlood.git
cd NeonFlood

# Optional: install proxy support
pip3 install PySocks --break-system-packages

# Run
python3 -m neonflood
```

### Linux (Arch / Manjaro)

```bash
sudo pacman -S python python-tk tk python-pip
git clone https://github.com/nhprince/NeonFlood.git
cd NeonFlood
pip install PySocks
python3 -m neonflood
```

### Linux — One-line quick-start

```bash
git clone https://github.com/nhprince/NeonFlood.git && cd NeonFlood && bash neonflood.sh
```

The shell script auto-detects your distro and installs all dependencies.

### Windows

```bat
git clone https://github.com/nhprince/NeonFlood.git
cd NeonFlood
neonflood.bat
```

Or double-click `neonflood.bat`.

### pip install (any OS)

```bash
pip install .               # core (no proxy)
pip install ".[proxy]"      # core + SOCKS5 support
```

After `pip install`, the `neonflood` command is available globally:

```bash
neonflood           # launch GUI
neonflood --help    # show CLI help
```

---

## Usage — GUI

Launch the GUI (no arguments):

```bash
python3 -m neonflood
# or
neonflood
# or
bash neonflood.sh
```

On first launch a legal disclaimer popup will appear. Click
**[ I UNDERSTAND — ENTER ]** to proceed.

### GUI Controls

| Control | Description |
|---|---|
| **TARGET** | Full URL including scheme, e.g. `http://example.com` |
| **MODE** | Attack mode dropdown: get / post / head / slowloris |
| **WORKERS** | Number of worker processes (1–50) |
| **SOCKETS** | Connections per worker per loop (1–500) |
| **TIMEOUT** | Socket timeout in seconds (1–60) |
| **RATE LIMIT** | Max requests/sec per worker (0 = unlimited) |
| **PROXY** | Optional proxy URL (cleared when empty) |
| **TOR** | Tick to route via Tor on `127.0.0.1:9050` |
| **PROFILE** | Load / save named configurations |
| **[ INITIALIZE STRIKE ]** | Start the session |
| **[ TERMINATE SESSION ]** | Stop all workers |
| **[CLR]** | Clear the console log |
| **[EXPORT]** | Open session summary + export popup |

---

## Usage — CLI

```bash
# Basic GET flood
python3 -m neonflood -u http://target.com

# POST flood — 10 workers, 100 sockets each
python3 -m neonflood -u http://target.com -w 10 -s 100 -m post

# Slowloris via Tor
python3 -m neonflood -u http://target.com -m slowloris --tor

# HEAD flood with rate limit and SOCKS5 proxy
python3 -m neonflood -u http://target.com -m head \
    --proxy socks5://127.0.0.1:1080 \
    --ratelimit 200

# Auto-stop after 60 seconds, export both report formats
python3 -m neonflood -u http://target.com --duration 60 \
    --report report.json --csv report.csv

# Force GUI even with flags present
python3 -m neonflood --gui

# Show version
python3 -m neonflood --version
```

The CLI always asks for a `YES` confirmation before starting to ensure
you are aware you are about to test the target.

---

## CLI Reference

```
usage: neonflood [-h] [-u URL] [-w N] [-s N] [-m MODE] [-t SEC]
                 [--proxy PROXY] [--tor] [--ratelimit RPS]
                 [--report FILE] [--csv FILE] [--duration SEC]
                 [--gui] [-v]

options:
  -h, --help            Show this help message and exit
  -u URL, --url URL     Target URL (http:// or https://)
  -w N, --workers N     Worker processes (default: 5)
  -s N, --sockets N     Connections per worker (default: 50)
  -m MODE, --mode MODE  Attack mode: get, post, head, slowloris
                        (default: get)
  -t SEC, --timeout SEC Socket timeout in seconds (default: 5)
  --proxy PROXY         Proxy URL e.g. socks5://127.0.0.1:1080
  --tor                 Route via Tor (127.0.0.1:9050)
  --ratelimit RPS       Max requests/sec per worker (0=unlimited)
  --report FILE         Export JSON report to FILE on exit
  --csv FILE            Export CSV report to FILE on exit
  --duration SEC        Auto-stop after N seconds
  --gui                 Force launch GUI
  -v, --version         Show version and exit
```

---

## Proxy & Tor Support

> Requires `PySocks`: `pip install PySocks`

### SOCKS5 proxy

```bash
neonflood -u http://target.com --proxy socks5://127.0.0.1:1080
```

### HTTP proxy

```bash
neonflood -u http://target.com --proxy http://proxy.host:8080
```

### Tor

Make sure Tor is running (default port 9050):

```bash
# Linux
sudo systemctl start tor

# Then use --tor flag
neonflood -u http://target.com --tor
```

### Proxy list rotation

Proxy list rotation is not yet built-in to the CLI. To approximate it,
run multiple NeonFlood instances each with a different `--proxy` value.

---

## Profiles

Save frequently used configurations as named profiles in the GUI:

1. Fill in TARGET, MODE, WORKERS, SOCKETS etc.
2. Click **[SAVE]** and enter a profile name.
3. To reload: select the profile name from the **PROFILE** dropdown.
4. To delete: select the profile and click **[DEL]**.

Profiles are stored as JSON files in `~/.neonflood/profiles/`.

---

## Reports & Logs

### Session logs

Every session automatically writes a log file to:

```
~/.neonflood/logs/session_YYYY-MM-DD_HH-MM-SS.log
```

### JSON report

Full session data including RPS history:

```json
{
  "tool": "NeonFlood v2.0.0",
  "target": "http://example.com",
  "mode": "get",
  "workers": 5,
  "sockets_per_worker": 50,
  "duration_seconds": 120.5,
  "total_requests": 48320,
  "successful_hits": 44210,
  "failed_requests": 4110,
  "avg_rps": 402.6,
  "peak_rps": 581,
  "rps_history": [
    {"timestamp": "2024-01-15T14:22:01", "rps": 390},
    ...
  ]
}
```

Export via:
- GUI: click **[EXPORT]** → **[ EXPORT JSON ]**
- CLI: `--report output.json`
- Auto-saved to `~/.neonflood/reports/` if not specified

### CSV report

Summary table + per-second RPS history rows.

Export via:
- GUI: click **[EXPORT]** → **[ EXPORT CSV ]**
- CLI: `--csv output.csv`

---

## Project Structure

```
NeonFlood/
├── neonflood/                  # Main Python package
│   ├── __init__.py             # Version, author, metadata
│   ├── __main__.py             # python -m neonflood entry point
│   ├── cli.py                  # Argparse CLI, banner, run loop
│   ├── gui.py                  # Full tkinter GUI application
│   ├── workers.py              # GET / POST / HEAD / Slowloris workers
│   ├── counter.py              # Thread-safe multiprocessing counters
│   ├── reporter.py             # SessionReport, SessionLogger
│   ├── profiles.py             # Named profile save/load system
│   ├── updater.py              # GitHub release update checker
│   └── useragents.py           # UA pool, random_headers()
├── setup.py                    # pip package configuration
├── requirements.txt            # Optional dependencies
├── neonflood.sh                # Linux/macOS quick-start script
├── neonflood.bat               # Windows quick-start script
└── README.md                   # This file
```

---

## Changelog

### v2.0.0
- Added full CLI with argparse (`-u`, `-w`, `-s`, `-m`, `-t`, `--proxy`,
  `--tor`, `--ratelimit`, `--report`, `--csv`, `--duration`, `--gui`, `--version`)
- Added POST flood mode
- Added HEAD flood mode
- Added Slowloris attack mode (raw socket, partial HTTP headers)
- Added SOCKS5 / HTTP proxy routing
- Added Tor routing (`--tor` shortcut)
- Added live RPS counter and colour-gradient graph widget
- Added session timer (HH:MM:SS) in both GUI and CLI
- Added JSON and CSV report export
- Added session file logging to `~/.neonflood/logs/`
- Added named profile save/load system
- Added GitHub release update checker (background thread)
- Added session summary popup after each session
- Added 48+ real browser User-Agent rotation pool
- Added randomized Accept, Accept-Language, Referer, Cache-Control headers
- Added per-worker rate limiter (`--ratelimit`)
- Fixed cursor visibility in all GUI input fields
- Fixed `tk.simpledialog` import (was broken in v1.x)
- Removed all dead imports (`ttk`, `os`, unused attributes)
- Improved console trimming (batch delete, 1200-line threshold)
- Made tool pip-installable with `setup.py`
- Added `neonflood.sh` auto-install script for Linux/macOS
- Added `neonflood.bat` quick-start script for Windows

### v1.0.0
- Initial release: single GET flood mode, GUI only

---

## Credits

**Developer**: NH Prince
**Website**: [nhprince.dpdns.org](https://nhprince.dpdns.org)
**Repository**: [github.com/nhprince/NeonFlood](https://github.com/nhprince/NeonFlood)

---

*For authorized and educational use only.*
