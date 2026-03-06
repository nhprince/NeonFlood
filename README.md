<div align="center">

# ⚡ NeonFlood

<img src="https://img.shields.io/badge/Python-3.10%2B-cyan?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-blueviolet?style=for-the-badge"/>
<img src="https://img.shields.io/badge/GUI-Tkinter-ff69b4?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Purpose-Educational%20Only-red?style=for-the-badge"/>
<img src="https://img.shields.io/badge/License-Educational-yellow?style=for-the-badge"/>

**A cyberpunk-themed Python GUI tool for network load simulation and authorized stress testing.**

[🌐 Developer Website](https://nhprince.dpdns.org) • [📦 Releases](#) • [🐛 Issues](#)

</div>

---

## ⚠️ Legal Disclaimer

> **THIS TOOL IS FOR EDUCATIONAL AND AUTHORIZED TESTING ONLY.**
>
> Do **NOT** use NeonFlood against any system, server, or network that you do **not own** or do **not have explicit written permission** to test.
>
> Unauthorized use of this tool may violate local, national, and international laws including but not limited to the **Computer Fraud and Abuse Act (CFAA)**, **UK Computer Misuse Act**, and equivalent legislation in your jurisdiction.
>
> **By downloading, installing, or running this software, you agree to take full legal and ethical responsibility for your actions.**
>
> The developer assumes **no liability** for any misuse or damage caused by this tool.

---


## ✨ Features

| Feature | Description |
|---|---|
| 🎨  GUI |  Tkinter interface  |
| 📊 Real-time Stats | Live strike count and fail/drop statistics |
| ⚙️ Multi-threaded | Multi-process worker architecture for load simulation |
| ▶️ Easy Controls | One-click **Initialize Strike** and **Terminate Session** buttons |

---

## 🧰 Requirements

- **Python** 3.10 or higher
- **Tkinter** — `tkinter` (usually bundled with Python)
- **Built-in modules** — `multiprocessing`, `queue`, `threading`

> **Linux users:** Root or elevated permissions may be required for raw network operations.

---

## 📥 Installation & Running

### Step 1 — Clone the Repository

```bash
git clone https://github.com/nhprince/NeonFlood.git
cd NeonFlood
```

---

### Step 2 — Install Dependencies & Run

Choose the command for your operating system:

#### 🐧 Linux (Ubuntu / Debian / Mint / Kali)

```bash
sudo apt update && sudo apt install python3 python3-tk -y && python3 ddos-gui.py
```

#### 🐧 Linux (Arch / Manjaro)

```bash
sudo pacman -Syu python python-tk tk --noconfirm && python3 ddos-gui.py
```

#### 🪟 Windows (PowerShell)

```powershell
python -m pip install --upgrade pip; python ddos-gui.py
```

> 💡 If `python` is not recognized on Windows, try `py ddos-gui.py` instead.  
> Make sure Python 3 is installed and added to your system **PATH**.

---

## 🚀 Usage

1. **Launch** GUI will open .
2. **Enter** the target URL or IP address *(authorized systems only)*.
3. **Select** the number of worker processes using the slider or input field.
4. **Click** `[ INITIALIZE STRIKE ]` to begin the stress test.
5. **Monitor** real-time strikes, dropped packets, and log output in the console.
6. **Click** `[ TERMINATE SESSION ]` to safely stop all workers and end the test.

---



## 📝 Notes

- ✅ This tool is strictly for **educational purposes** and **authorized penetration testing**.
- ❌ **Never** run this against systems without **explicit permission**.
- 🔐 On Linux, run with appropriate permissions if network operations are restricted.
- 🔔 A warning popup appears at startup — read it carefully before proceeding.

---

## 👤 Credits

| Role | Info |
|---|---|
| **Developer** | NH Prince |
| **Website** | [https://nhprince.dpdns.org](https://nhprince.dpdns.org) |

---

## 📄 License

This project is provided **for educational and authorized testing purposes only**.

Unauthorized use, distribution, or deployment against systems without permission is **strictly prohibited** and may be illegal.

---

<div align="center">

Made with 💜 by [NH Prince](https://nhprince.dpdns.org) &nbsp;|&nbsp; ⚡ NeonFlood

</div>
