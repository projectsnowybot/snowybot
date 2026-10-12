

# snowybot is a clamcoin-just-dice-gambling-bot

snowybot is a headless browser-based cryptocurrency gambling and compounding automation built with Python and PyQt5.

snowybot operates on the just-dice.com platform using an isolated session storage profile.

Prerequisites

Ensure you have Python 3.8 or higher installed on your system. You can verify your Python version by running:

    python3 --version

Installation & Setup

Choose your operating system below to install the required dependencies (PyQt5 and pwinput).

# 1. Linux (Ubuntu / Debian) and known install equivalent 

Open your terminal and run the following commands and update package lists and install python3-pip if not already installed

    sudo apt update && sudo apt install -y python3-pip python3-pyqt5 python3-pyqt5.qtwebengine

Install the required Python package for masked password/2FA inputs
    
    pip install pwinput --break-system-packages

(Note: Depending on your Linux distribution, you may need to run inside a Python virtual environment if system package managers restrict global pip installs).


# 2. Windows

Open Command Prompt or PowerShell as Administrator and run:
DOS

Install PyQt5 and pwinput via pip

    pip install PyQt5 PyQtWebEngine pwinput

# 3. macOS

Open your Terminal app and install the dependencies using pip3:

Install required packages

    pip3 install PyQt5 PyQtWebEngine pwinput

How to Use

# Make sure you have created your account and signed up on just-dice.com beforehand.
# You will need your account username and password during execution.
# you will need balance above 0.0144 for snowybot to work without glitch.

Open a terminal or command prompt in the directory containing snowybot.py

Run the script:

    python3 snowybot.py

or

    python snowybot.py

When prompted by the console, enter your Just-Dice username, password, and optional 2FA code (press Enter to skip 2FA if you do not have it enabled):

        User: your_username

        Pass: **********

        2FA (optional, press Enter to skip): [Enter code or leave blank]

The script will launch an offscreen automated browser instance, navigate to just-dice.com, log into your account using your signup credentials, and start the automated reset-compounding betting loop.
State & Logs

.bot_state.json: Automatically tracks your session data, wallet stash, and compounding progress. If you wish to reset your baseline completely, delete this file before starting the script.

Milestone / Safety: The bot automatically halts if it reaches the target balance, or resets its baseline profile upon hitting a 10% compounding profit milestone.

# warning remember delete the .bot_state.json file when balance changes or compound daily while the bots stopped
# warning snowybot.py recreates .bot_state.json file while running do not remove while running or can lose funds
