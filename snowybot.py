#!/usr/bin/env python3
import ast
import asyncio
import json
import math
import os
import shutil
import subprocess
import sys
import time

import pwinput
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Local bypass to prevent urllib3 crashes
os.environ["no_proxy"] = os.environ["NO_PROXY"] = (
    os.environ.get("no_proxy", "") + ",localhost,127.0.0.1,127.0.0.53,0.0.0.0"
).strip(",")

STATE_FILE = "/home/r36s/bot_state.json"
LOG_OUT = "/home/r36s/bot_output.log"
LOG_ERR = "/home/r36s/bot_error.log"  # Fixed missing slash typo
GECKO_PATH = "/home/r36s/geckodriver"

# Global Selenium Driver and Credentials
driver = None
username = ""
password = ""
code_2fa = ""

# Global Strategy State Variables
startingPocketChange = 0.0
tinyPeanutSize = 0.0
backupPeanut = 0.0
tenPeanuts = 0.0
walletStash = 0.0
areWeRichYet = False
oopsieCounter = 0
previousWalletState = 0.0
oldTicketStub = 0
shinyNewTicket = 0
totalSessionWins = 0
totalSessionLosses = 0
baseWinReference = 0
baseLossReference = 0
currentWagerAmount = 0.0
previousWagerAmount = 0.0
luckyCoinFlip = 0
checkpointJuice = 0.0
wobbleFactor = 1.0
safetyCheckpoint = 0.0

last_logged_wager_id = 0
last_balance_change_time = time.time()
last_observed_balance = 0.0


def reset_session():
    profile_path = "/home/r36s/.mozilla/firefox/bot_profile"
    if os.path.exists(profile_path):
        try:
            shutil.rmtree(profile_path)
            print("[System] Cleared old Firefox bot profile.")
        except Exception as e:
            print(f"[System] Could not clear bot profile: {e}")
    time.sleep(1)


def get_g_hosts():
    try:
        r = subprocess.check_output(
            ["gsettings", "get", "org.gnome.system.proxy", "ignore-hosts"],
            text=True,
        ).strip()
        return ast.literal_eval(r)
    except Exception:
        return [
            "localhost",
            "127.0.0.1",
            "just-dice.com",
            "altquick.com",
            "jsdelivr.net",
            "jquery.com",
            "cloudflareinsights.com",
            "hcaptcha.com",
            "gstatic.com",
            "googleapis.com",
            "highcharts.com",
            "192.168.1.1",
        ]


def daemonize():
    """Disconnects process from terminal cleanly via UNIX Double-Fork."""
    print("Detaching process and launching background daemon...")
    print(f"Standard output: {LOG_OUT}")
    print(f"Error output: {LOG_ERR}\n")
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        print(f"Fork #1 failed: {e}", file=sys.stderr)
        sys.exit(1)

    os.chdir("/")
    os.setsid()
    os.umask(0)

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        print(f"Fork #2 failed: {e}", file=sys.stderr)
        sys.exit(1)

    sys.stdout.flush()
    sys.stderr.flush()

    si = open(os.devnull, "r")
    so = open(LOG_OUT, "a+", encoding="utf-8")
    se = open(LOG_ERR, "a+", encoding="utf-8")

    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())


# ============================================================================
# STATE PERSISTENCE HELPERS
# ============================================================================


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Error] Failed to load state file: {e}")
    return None


def save_state():
    bot_state = {
        "walletStash": walletStash,
        "startingPocketChange": startingPocketChange,
        "tinyPeanutSize": tinyPeanutSize,
        "backupPeanut": backupPeanut,
        "tenPeanuts": tenPeanuts,
        "areWeRichYet": areWeRichYet,
        "oopsieCounter": oopsieCounter,
        "previousWalletState": previousWalletState,
        "oldTicketStub": oldTicketStub,
        "shinyNewTicket": shinyNewTicket,
        "totalSessionWins": totalSessionWins,
        "totalSessionLosses": totalSessionLosses,
        "baseWinReference": baseWinReference,
        "baseLossReference": baseLossReference,
        "currentWagerAmount": currentWagerAmount,
        "previousWagerAmount": previousWagerAmount,
        "luckyCoinFlip": luckyCoinFlip,
        "checkpointJuice": checkpointJuice,
        "wobbleFactor": wobbleFactor,
        "safetyCheckpoint": safetyCheckpoint,
        "last_seen_timestamp": time.time(),
    }
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(bot_state, f)
    except Exception as e:
        print(f"[Error] Failed to save state file: {e}")


# ============================================================================
# DOM INTERACTION HELPERS
# ============================================================================


def safe_float(val, default=0.0):
    try:
        cleaned = str(val).strip().replace(",", "")
        return float(cleaned)
    except (ValueError, TypeError):
        return default


def shake_the_piggy_bank():
    try:
        element = driver.find_element(By.ID, "pct_balance")
        val = element.get_attribute("value") or element.text
        return round(safe_float(val, 0.0), 8)
    except Exception:
        return 0.0


def count_the_happy_wins():
    try:
        el = driver.find_element(By.ID, "wins")
        return int(safe_float(el.text, 0))
    except Exception:
        return 0


def count_the_sad_losses():
    try:
        el = driver.find_element(By.ID, "losses")
        return int(safe_float(el.text, 0))
    except Exception:
        return 0


def fetch_latest_wager_id():
    try:
        script = """
        var me = document.getElementById("me");
        if (!me || !me.firstElementChild || !me.firstElementChild.lastElementChild || !me.firstElementChild.lastElementChild.firstElementChild) return 0;
        var row = me.firstElementChild.lastElementChild.firstElementChild;
        return row.children[5] ? row.children[5].innerText : 0;
        """
        res = driver.execute_script(script)
        val = int(safe_float(res, 0))
        return val if val > 0 else 0
    except Exception:
        return 0


def inspect_roll_outcome():
    try:
        script = """
        var me = document.getElementById("me");
        if (!me || !me.firstElementChild || !me.firstElementChild.lastElementChild || !me.firstElementChild.lastElementChild.firstElementChild) return -1;
        var row = me.firstElementChild.lastElementChild.firstElementChild;
        return row.children[7] ? row.children[7].innerText : -1;
        """
        res = driver.execute_script(script)
        return safe_float(res, -1.0)
    except Exception:
        return -1.0


def click_minimum_bet_button():
    try:
        driver.find_element(By.ID, "b_min").click()
    except Exception:
        pass


def configure_win_odds(chance_value=49.5):
    try:
        chance_input = driver.find_element(By.ID, "pct_chance")
        chance_input.clear()
        chance_input.send_keys(str(chance_value))
    except Exception:
        pass


def apply_stake_amount(stake_value):
    try:
        bet_input = driver.find_element(By.ID, "pct_bet")
        formatted = f"{float(stake_value):.8f}"
        bet_input.clear()
        bet_input.send_keys(formatted)
    except Exception:
        pass


def trigger_roll_action():
    try:
        driver.find_element(By.ID, "a_lo").click()
        return True
    except Exception as e:
        print(f"[ERROR] Could not find #a_lo element to place roll: {e}")
        return False


def execute_placement_routine(target_stake, win_chance=49.5):
    global last_balance_change_time
    last_balance_change_time = time.time()
    click_minimum_bet_button()
    configure_win_odds(win_chance)
    apply_stake_amount(target_stake)
    return trigger_roll_action()


def log_bet_info(bet_amount, current_profit, wager_id):
    global last_logged_wager_id
    if wager_id and wager_id > 0 and wager_id == last_logged_wager_id:
        return
    if wager_id and wager_id > 0:
        last_logged_wager_id = wager_id
    print(f"Bet: {bet_amount:.8f} | Profit: {current_profit:.8f}")


# ============================================================================
# STRATEGY & BETTING LOGIC
# ============================================================================


def calculate_next_progression_step(incoming_wager):
    global walletStash, currentWagerAmount, wobbleFactor, checkpointJuice, safetyCheckpoint

    walletStash = shake_the_piggy_bank()
    currentWagerAmount = float(incoming_wager)

    if walletStash >= (safetyCheckpoint + ((tinyPeanutSize * 10) * wobbleFactor)):
        currentWagerAmount = backupPeanut
        wobbleFactor = 1.0
        checkpointJuice = float(
            math.floor(walletStash / (tinyPeanutSize * 10)) * (tinyPeanutSize * 10)
        )
        safetyCheckpoint = float(
            math.floor(walletStash / (tinyPeanutSize * 10)) * (tinyPeanutSize * 10)
        )

    if (currentWagerAmount < (backupPeanut * 1.5)) and (
        walletStash > (checkpointJuice + (currentWagerAmount * 6.9))
    ):
        currentWagerAmount = currentWagerAmount * 2
        checkpointJuice = float(walletStash)

    if (currentWagerAmount < (backupPeanut * 1.5)) and (
        walletStash < (checkpointJuice - (currentWagerAmount * 2.9))
    ):
        currentWagerAmount = currentWagerAmount * 2
        checkpointJuice = float(walletStash)

    if (currentWagerAmount > (backupPeanut * 1.5)) and (
        walletStash > (checkpointJuice + (currentWagerAmount * 4.9))
    ):
        currentWagerAmount = currentWagerAmount * 2
        checkpointJuice = float(walletStash)

    if (currentWagerAmount > (backupPeanut * 1.5)) and (
        walletStash < (checkpointJuice - (currentWagerAmount * 4.9))
    ):
        currentWagerAmount = currentWagerAmount * 2
        wobbleFactor = 0.0
        checkpointJuice = float(walletStash)

    return round(float(currentWagerAmount), 8)


def init_bot():
    global driver, username, password, code_2fa
    global startingPocketChange, tinyPeanutSize, backupPeanut, tenPeanuts
    global walletStash, areWeRichYet, oopsieCounter, previousWalletState
    global oldTicketStub, shinyNewTicket, totalSessionWins, totalSessionLosses
    global baseWinReference, baseLossReference, currentWagerAmount, previousWagerAmount
    global luckyCoinFlip, checkpointJuice, wobbleFactor, safetyCheckpoint
    global last_observed_balance, last_balance_change_time

    print("[System] Navigating to just-dice.com...")
    driver.get("https://just-dice.com")

    # Dismiss modal if present
    try:
        close_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.fancybox-item.fancybox-close"))
        )
        close_btn.click()
    except Exception:
        pass

    time.sleep(2)
    account_link = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Account"))
    )
    account_link.click()

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "myuser")))
    driver.find_element(By.ID, "myuser").clear()
    driver.find_element(By.ID, "myuser").send_keys(username)
    driver.find_element(By.ID, "mypass").clear()
    driver.find_element(By.ID, "mypass").send_keys(password)
    driver.find_element(By.ID, "mycode").clear()
    driver.find_element(By.ID, "mycode").send_keys(code_2fa)
    driver.find_element(By.ID, "myok").click()

    print("[System] Authentication submitted, waiting for login stabilization...")
    time.sleep(10)

    # Initialize State
    savedState = load_state()

    current_bal = shake_the_piggy_bank()
    startingPocketChange = (
        savedState.get("startingPocketChange", current_bal) if savedState else current_bal
    )
    tinyPeanutSize = (
        savedState.get("tinyPeanutSize", round(startingPocketChange / 1440000.0, 8))
        if savedState
        else round(startingPocketChange / 1440000.0, 8)
    )
    backupPeanut = savedState.get("backupPeanut", tinyPeanutSize) if savedState else tinyPeanutSize
    tenPeanuts = (
        savedState.get("tenPeanuts", tinyPeanutSize * 10) if savedState else (tinyPeanutSize * 10)
    )

    walletStash = savedState.get("walletStash", startingPocketChange) if savedState else startingPocketChange
    areWeRichYet = savedState.get("areWeRichYet", False) if savedState else False
    oopsieCounter = savedState.get("oopsieCounter", 0) if savedState else 0
    previousWalletState = (
        savedState.get("previousWalletState", float(walletStash)) if savedState else float(walletStash)
    )
    oldTicketStub = savedState.get("oldTicketStub", 0) if savedState else 0
    shinyNewTicket = savedState.get("shinyNewTicket", 0) if savedState else 0

    totalSessionWins = (
        savedState.get("totalSessionWins", count_the_happy_wins())
        if savedState
        else count_the_happy_wins()
    )
    totalSessionLosses = (
        savedState.get("totalSessionLosses", count_the_sad_losses())
        if savedState
        else count_the_sad_losses()
    )
    baseWinReference = (
        savedState.get("baseWinReference", float(totalSessionWins))
        if savedState
        else float(totalSessionWins)
    )
    baseLossReference = (
        savedState.get("baseLossReference", float(totalSessionLosses))
        if savedState
        else float(totalSessionLosses)
    )
    currentWagerAmount = (
        savedState.get("currentWagerAmount", backupPeanut) if savedState else backupPeanut
    )
    previousWagerAmount = (
        savedState.get("previousWagerAmount", float(currentWagerAmount))
        if savedState
        else float(currentWagerAmount)
    )

    luckyCoinFlip = savedState.get("luckyCoinFlip", 0) if savedState else 0
    checkpointJuice = (
        savedState.get("checkpointJuice", float(startingPocketChange))
        if savedState
        else float(startingPocketChange)
    )
    wobbleFactor = savedState.get("wobbleFactor", 1.0) if savedState else 1.0
    safetyCheckpoint = (
        savedState.get(
            "safetyCheckpoint",
            float(math.floor(walletStash / (tinyPeanutSize * 10)) * (tinyPeanutSize * 10)),
        )
        if savedState
        else float(math.floor(walletStash / (tinyPeanutSize * 10)) * (tinyPeanutSize * 10))
    )

    last_observed_balance = current_bal
    last_balance_change_time = time.time()


async def runPrimaryBettingLoop():
    global driver, walletStash, last_observed_balance, last_balance_change_time
    global shinyNewTicket, oldTicketStub, oopsieCounter, previousWagerAmount
    global previousWalletState, luckyCoinFlip, baseWinReference, baseLossReference
    global totalSessionWins, totalSessionLosses

    while True:
        try:
            walletStash = shake_the_piggy_bank()
            if walletStash != last_observed_balance:
                last_observed_balance = walletStash
                last_balance_change_time = time.time()

            # Watchdog timeout check (30s balance inactivity refresh)
            if time.time() - last_balance_change_time >= 30:
                print("[Watchdog] Balance static for 30s. Reloading page...")
                last_balance_change_time = time.time()
                driver.refresh()
                await asyncio.sleep(10)
                continue

            shinyNewTicket = fetch_latest_wager_id()

            if (shinyNewTicket > oldTicketStub) or (oopsieCounter == 0):
                computedNextBet = calculate_next_progression_step(previousWagerAmount)

                if walletStash >= 144000:
                    print(f"[System] TARGET REACHED ({walletStash}). Halting execution.")
                    if os.path.exists(STATE_FILE):
                        try:
                            os.remove(STATE_FILE)
                        except Exception:
                            pass
                    driver.quit()
                    sys.exit()

                currentRollVal = inspect_roll_outcome()
                if 0 <= currentRollVal < 49.5000:
                    luckyCoinFlip = 1
                elif currentRollVal >= 49.5000:
                    luckyCoinFlip = 0

                totalSessionWins = count_the_happy_wins()
                totalSessionLosses = count_the_sad_losses()

                if oopsieCounter == 0:
                    log_bet_info(computedNextBet, walletStash - startingPocketChange, shinyNewTicket)
                    execute_placement_routine(computedNextBet, 49.5)
                    previousWagerAmount = float(computedNextBet)
                    previousWalletState = float(walletStash)
                    oldTicketStub = float(shinyNewTicket)
                    oopsieCounter += 1
                    save_state()
                elif shinyNewTicket > oldTicketStub:
                    log_bet_info(computedNextBet, walletStash - startingPocketChange, shinyNewTicket)
                    execute_placement_routine(computedNextBet, 49.5)
                    previousWagerAmount = float(computedNextBet)

                    if luckyCoinFlip == 1:
                        baseWinReference += 1
                    else:
                        baseLossReference += 1

                    previousWalletState = float(walletStash)
                    oldTicketStub = float(shinyNewTicket)
                    oopsieCounter += 1
                    save_state()

        except Exception as loopErr:
            print(f"[Error] Execution error recovered: {loopErr}")

        await asyncio.sleep(0.05)


if __name__ == "__main__":
    reset_session()

    # Prompt credentials in terminal
    username = input("User: ")
    password = pwinput.pwinput(prompt="Pass: ", mask="*")
    code_2fa = pwinput.pwinput(prompt="2FA: ", mask="*")
    print("Initializing...")

    # Options setup
    opt = Options()
    opt.add_argument("--headless")
    opt.set_preference("network.proxy.type", 0)  # Direct connection (no dummy proxy trap)

    # Optional binary location: Only override if firefox executable exists at specific path
    if os.path.exists("/usr/bin/firefox"):
        opt.binary_location = "/usr/bin/firefox"
    elif os.path.exists("/usr/bin/firefox-esr"):
        opt.binary_location = "/usr/bin/firefox-esr"

    print("[System] Initializing Firefox headless browser driver...")
    service_kwargs = {}
    if os.path.exists(GECKO_PATH):
        service_kwargs["executable_path"] = GECKO_PATH

    driver = webdriver.Firefox(service=Service(**service_kwargs), options=opt)

    try:
        init_bot()
        asyncio.run(runPrimaryBettingLoop())
    finally:
        if driver:
            driver.quit()