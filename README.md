# Snowy Bot

Snowy Bot is a Python-based automated compounding engine utilizing PyQt5 and QWebEngine to interact with browser-based interfaces.

---

## Prerequisites

Ensure you have **Python 3.8+** installed on your system. You can verify your installation by running:
```bash
python --version
```
*(On some Linux distributions or macOS setups, you may need to use `python3` instead of `python`)*.

---

## Installation Guide

### 1. Clone or Download the Repository
Save `snowybot.py` into a local directory of your choice, then open your terminal (or Command Prompt / PowerShell on Windows) and navigate to that directory:
```bash
cd path/to/snowy-bot-directory
```

### 2. Install Dependencies

The script relies on `PyQt5`, `PyQtWebEngine`, and `pwinput`.

#### **Linux (Ubuntu / Debian / Fedora / Arch)**
On Linux, Qt requires platform support libraries. Install Python packages and system dependencies using your package manager:

* **Ubuntu / Debian:**
  ```bash
  sudo apt-get update
  sudo apt-get install -y python3-pip python3-pyqt5 python3-pyqt5.qtwebengine
  pip3 install pwinput
  ```
* **Fedora / RHEL:**
  ```bash
  sudo dnf install python3-pip python3-qt5 python3-qt5-webengine
  pip install pwinput
  ```
* **Arch Linux:**
  ```bash
  sudo pacman -S python-pip python-pyqt5 python-pyqtwebengine
  pip install pwinput
  ```

#### **Windows**
Open **Command Prompt** or **PowerShell** as Administrator and run:
```cmd
pip install PyQt5 PyQtWebEngine pwinput
```

#### **macOS**
Open your terminal and install via `pip`:
```bash
pip3 install PyQt5 PyQtWebEngine pwinput
```
*(Note: If you encounter permission errors on macOS or Linux, append `--user` to the `pip install` command, or use a Python virtual environment).*

---

## How to Use

By default, the script runs in an **offscreen headless mode** (`QT_QPA_PLATFORM = "offscreen"`), meaning the browser window will execute in the background.

1. Run the script from your terminal:
   ```bash
   python snowybot.py
   ```
   *(Use `python3 snowybot.py` if necessary)*.

2. Follow the secure interactive terminal prompts:
   * **User:** Enter your account username.
   * **Pass:** Enter your account password (hidden by masking characters).
   * **2FA:** Enter your 2FA code if enabled, or simply press **Enter** to skip.

3. The bot will automatically initialize an isolated browser profile, handle the authentication sequence, and begin the compounding session. Status updates and bet logs will print directly to your terminal.
