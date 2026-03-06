#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  NeonFlood v2.0.0 — Linux / macOS Quick-Start Script
#  Developer : NH Prince | https://nhprince.dpdns.org
#  Usage     : bash neonflood.sh [any neonflood CLI flags]
#  Examples  : bash neonflood.sh
#              bash neonflood.sh -u http://target.com -m slowloris
# ═══════════════════════════════════════════════════════════════════
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RESET='\033[0m'

echo -e "${RED}"
cat << 'BANNER'
  ███╗   ██╗███████╗ ██████╗ ███╗   ██╗███████╗██╗      ██████╗  ██████╗ ██████╗
  ████╗  ██║██╔════╝██╔═══██╗████╗  ██║██╔════╝██║     ██╔═══██╗██╔═══██╗██╔══██╗
  ██╔██╗ ██║█████╗  ██║   ██║██╔██╗ ██║█████╗  ██║     ██║   ██║██║   ██║██║  ██║
  ██║╚██╗██║██╔══╝  ██║   ██║██║╚██╗██║██╔══╝  ██║     ██║   ██║██║   ██║██║  ██║
  ██║ ╚████║███████╗╚██████╔╝██║ ╚████║██║     ███████╗╚██████╔╝╚██████╔╝██████╔╝
  ╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝     ╚══════╝ ╚═════╝  ╚═════╝ ╚═════╝
BANNER
echo -e "${RESET}"
echo -e "${CYAN}  v2.0.0  //  NH Prince  //  nhprince.dpdns.org${RESET}"
echo -e "${RED}  FOR AUTHORIZED AND EDUCATIONAL USE ONLY${RESET}"
echo ""

# ── Detect OS ────────────────────────────────────────────────────────────────
OS="$(uname -s 2>/dev/null || echo Unknown)"

# ── Install system dependencies if missing ───────────────────────────────────
install_system_deps() {
    echo -e "${YELLOW}[*] Installing system dependencies...${RESET}"

    if   command -v apt    &>/dev/null; then
        sudo apt update -qq
        sudo apt install -y python3 python3-tk python3-pip
    elif command -v pacman &>/dev/null; then
        sudo pacman -Syu --noconfirm python python-tk tk python-pip
    elif command -v dnf    &>/dev/null; then
        sudo dnf install -y python3 python3-tkinter python3-pip
    elif command -v yum    &>/dev/null; then
        sudo yum install -y python3 python3-tkinter python3-pip
    elif command -v zypper &>/dev/null; then
        sudo zypper install -y python3 python3-tk python3-pip
    elif command -v brew   &>/dev/null; then
        brew install python python-tk
    else
        echo -e "${RED}[!] Cannot detect package manager."
        echo -e "    Please install python3 and python3-tk manually.${RESET}"
        exit 1
    fi

    echo -e "${GREEN}[✓] System dependencies installed.${RESET}"
}

# ── Check Python ─────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo -e "${YELLOW}[!] python3 not found.${RESET}"
    install_system_deps
fi

PYTHON_VERSION=$(python3 -c "import sys; print(sys.version_info.major * 10 + sys.version_info.minor)")
if [ "$PYTHON_VERSION" -lt 310 ]; then
    echo -e "${RED}[!] Python 3.10 or newer is required (found: $(python3 --version)).${RESET}"
    exit 1
fi

# ── Check tkinter ────────────────────────────────────────────────────────────
if ! python3 -c "import tkinter" &>/dev/null; then
    echo -e "${YELLOW}[!] tkinter not found — installing...${RESET}"
    install_system_deps
fi

# ── Optional: install PySocks for proxy support ───────────────────────────────
echo -e "${YELLOW}[*] Checking optional proxy support (PySocks)...${RESET}"
python3 -c "import socks" &>/dev/null || \
    pip3 install PySocks --break-system-packages 2>/dev/null || \
    pip3 install PySocks 2>/dev/null || \
    echo -e "${YELLOW}[!] PySocks not installed — proxy/Tor features disabled.${RESET}"

echo -e "${GREEN}[✓] Environment ready.${RESET}"
echo ""

# ── Launch NeonFlood (pass all script arguments through) ────────────────────
echo -e "${CYAN}[*] Launching NeonFlood...${RESET}"
echo ""
python3 -m neonflood "$@"
