#!/usr/bin/env python3
import json
import math
import os
import sys
import time
import pwinput

from PyQt5.QtCore import QUrl, QTimer, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage

STATE_FILE = ".bot_state.json"
MASTER_STATE_FILE = ".bot_master_state.json"
LOG_OUT = ".bot_output.log"
LOG_ERR = ".bot_error.log"

trueOriginalBalance = 0.0
startingPocketChange = 0.0
tinyPeanutSize = 0.0
backupPeanut = 0.0
tenPeanuts = 0.0
walletStash = 0.0
previousWalletState = 0.0
currentWagerAmount = 0.0
previousWagerAmount = 0.0
checkpointJuice = 0.0
wobbleFactor = 1.0
safetyCheckpoint = 0.0
safetyCheckpointtwo = 0.0

last_balance_change_time = time.time()
last_observed_balance = 0.0
last_bet_timestamp = time.time()
last_activity_timestamp = time.time()
has_placed_first_bet = False
watchdog_threshold = 10.0

username = ""
password = ""
code_2fa = ""
logged_in = False


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Error] Failed to load state file: {e}", flush=True)
    return None


def save_state():
    bot_state = {
        "walletStash": round(float(walletStash), 8),
        "startingPocketChange": round(float(startingPocketChange), 8),
        "tinyPeanutSize": round(float(tinyPeanutSize), 8),
        "backupPeanut": round(float(backupPeanut), 8),
        "tenPeanuts": round(float(tenPeanuts), 8),
        "previousWalletState": round(float(previousWalletState), 8),
        "currentWagerAmount": round(float(currentWagerAmount), 8),
        "previousWagerAmount": round(float(previousWagerAmount), 8),
        "checkpointJuice": round(float(checkpointJuice), 8),
        "wobbleFactor": wobbleFactor,
        "safetyCheckpoint": round(float(safetyCheckpoint), 8),
        "safetyCheckpointtwo": round(float(safetyCheckpointtwo), 8),
        "last_seen_timestamp": time.time(),
    }
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(bot_state, f)
    except Exception as e:
        print(f"[Error] Failed to save state file: {e}", flush=True)


def load_master_state():
    if os.path.exists(MASTER_STATE_FILE):
        try:
            with open(MASTER_STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Error] Failed to load master state file: {e}", flush=True)
    return None


def save_master_state(balance):
    master_state = {"trueOriginalBalance": balance}
    try:
        with open(MASTER_STATE_FILE, "w") as f:
            json.dump(master_state, f)
    except Exception as e:
        print(f"[Error] Failed to save master state file: {e}", flush=True)


def calculate_next_progression_step(incoming_wager):
    global walletStash, currentWagerAmount, wobbleFactor, checkpointJuice, safetyCheckpoint, tinyPeanutSize, backupPeanut, safetyCheckpointtwo

    currentWagerAmount = round(float(incoming_wager), 8)
    walletStash = float(walletStash)
    checkpointJuice = float(checkpointJuice)
    safetyCheckpoint = float(safetyCheckpoint)
    safetyCheckpointtwo = float(safetyCheckpointtwo)

    if (walletStash > safetyCheckpointtwo):
        safetyCheckpointtwo = float(walletStash)

    if (walletStash>(safetyCheckpoint+(tinyPeanutSize*70))):
        currentWagerAmount = float(round(float(tinyPeanutSize), 8))
        checkpointJuice = float((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10))
        safetyCheckpointtwo = float(((math.ceil(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)) + (tinyPeanutSize * 10))
        safetyCheckpoint = float(((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)) - (tinyPeanutSize * 10))
       
    if (((walletStash - (safetyCheckpoint + (currentWagerAmount * 2))) < tinyPeanutSize) and (walletStash != checkpointJuice) and ((math.floor(walletStash / (tinyPeanutSize * 10))) >=1)):
        currentWagerAmount = float(round(float(tinyPeanutSize), 8))
        checkpointJuice = float((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10))
        safetyCheckpoint = float((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10))
        safetyCheckpointtwo = float(((math.ceil(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)) + (tinyPeanutSize * 10))

    if (((walletStash - (currentWagerAmount * 2)) < tinyPeanutSize) and (walletStash != checkpointJuice) and ((math.floor(walletStash / (tinyPeanutSize * 10))) <=0)):
        currentWagerAmount = float(round(float(tinyPeanutSize), 8))
        checkpointJuice = 0
        safetyCheckpoint = 0
        safetyCheckpointtwo = (tinyPeanutSize * 10)

    if ((walletStash != checkpointJuice) and (walletStash < (((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)) + (tinyPeanutSize * 7.9))) and (walletStash > (((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)) + (tinyPeanutSize * 6.9)))):
        currentWagerAmount = float(round(((round(float(currentWagerAmount), 8))*2), 8))
        checkpointJuice = float(walletStash)

    if (((walletStash - (safetyCheckpoint + (currentWagerAmount * 4))) < currentWagerAmount) and (walletStash == checkpointJuice)):
        currentWagerAmount = float(round(float(tinyPeanutSize), 8))
        checkpointJuice = float(walletStash)
        safetyCheckpointtwo = float(((math.ceil(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)) + (tinyPeanutSize * 10))
        safetyCheckpoint = float(((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)) - (tinyPeanutSize * 10))

    if (((walletStash - (currentWagerAmount * 4)) < currentWagerAmount) and (walletStash == checkpointJuice)):
        currentWagerAmount = float(round(((round(float(tinyPeanutSize), 8))*2), 8))
        checkpointJuice = float(walletStash)
        safetyCheckpointtwo = float(((math.ceil(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)) + (tinyPeanutSize * 10))
        safetyCheckpoint = float(((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)) - (tinyPeanutSize * 10))

    return round(float(currentWagerAmount), 8)



def log_bet_info(bet_amount, current_balance, total_profit):
    print(f"Bet: {bet_amount:.8f} | Balance: {current_balance:.8f} | Total Profit: {total_profit:+.8f}", flush=True)


class SnowyBotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Snowy Bot - WolfBet Logic Engine (QtWebEngine)")
        self.resize(1024, 768)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.runPrimaryBettingLoop)

        self.start_full_login_sequence(wipe_data=True)

    def init_browser_engine(self, wipe_data=False):
        profile_name = f"SnowyProfile_{time.time()}"
        profile = QWebEngineProfile(profile_name, self)

        if wipe_data:
            print("[System] Wiping browser cache, cookies, and site data...", flush=True)
            profile.clearHttpCache()
            profile.clearAllVisitedLinks()

        ua_string = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            if sys.platform == "win32"
            else "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        profile.setHttpUserAgent(ua_string)

        page = QWebEnginePage(profile, self)
        self.browser = QWebEngineView()
        self.browser.setPage(page)
        self.setCentralWidget(self.browser)

    def start_full_login_sequence(self, wipe_data=True):
        global logged_in, has_placed_first_bet
        logged_in = False
        has_placed_first_bet = False
        
        self.init_browser_engine(wipe_data=wipe_data)

        print("[System] Navigating to just-dice.com...", flush=True)
        self.browser.setUrl(QUrl("https://just-dice.com"))

        print("[System] Waiting 10 seconds for page scripts and WebSocket engine to stabilize...", flush=True)
        QTimer.singleShot(10000, self.open_account_tab)

    def open_account_tab(self):
        print("[System] Dismissing modals and locating Account/Login interface...", flush=True)
        js_nav = """
        (function() {
            var closeBtn = document.querySelector('a.fancybox-item.fancybox-close');
            if (closeBtn) { closeBtn.click(); }
            
            if (document.getElementById('myuser')) { return 'ALREADY_VISIBLE'; }

            var elements = Array.from(document.querySelectorAll('a, button, span, div'));
            var target = elements.find(el => {
                var txt = el.textContent.trim().toLowerCase();
                return txt === 'account' || txt === 'login' || txt.includes('account') || txt.includes('login');
            });

            if (target) { 
                target.click(); 
                return 'CLICKED'; 
            }
            return 'NOT_FOUND';
        })();
        """
        self.browser.page().runJavaScript(js_nav, self._after_account_click)

    def _after_account_click(self, status):
        print(f"[System] Account tab navigation result: {status}", flush=True)
        print("[System] Waiting 10 seconds for account tab and login input fields...", flush=True)
        QTimer.singleShot(10000, self.submit_login_credentials)

    def submit_login_credentials(self):
        global username, password, code_2fa
        print("[System] Submitting authentication payload to DOM...", flush=True)

        tfa_val = code_2fa.strip() if code_2fa else ""

        js_login = f"""
        (function() {{
            var closeBtn = document.querySelector('a.fancybox-item.fancybox-close');
            if (closeBtn) {{ closeBtn.click(); }}

            var uEl = document.getElementById('myuser');
            var pEl = document.getElementById('mypass');
            var cEl = document.getElementById('mycode');
            var okEl = document.getElementById('myok');

            if (!uEl || !pEl || !okEl) {{
                var elements = Array.from(document.querySelectorAll('a, button, span, div'));
                var target = elements.find(el => {{
                    var txt = el.textContent.trim().toLowerCase();
                    return txt === 'account' || txt === 'login' || txt.includes('account') || txt.includes('login');
                }});
                if (target) {{ target.click(); }}
                return 'MISSING_FIELDS';
            }}

            uEl.value = "{username}";
            uEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
            uEl.dispatchEvent(new Event('change', {{ bubbles: true }}));

            pEl.value = "{password}";
            pEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
            pEl.dispatchEvent(new Event('change', {{ bubbles: true }}));

            var tfa = "{tfa_val}";
            if (cEl && tfa !== "") {{ 
                cEl.value = tfa; 
                cEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
                cEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}

            okEl.click();
            return 'SUBMITTED';
        }})();
        """
        self.browser.page().runJavaScript(js_login, self._after_login_submitted)

    def _after_login_submitted(self, status):
        print(f"[System] Credentials action: {status}", flush=True)
        if status == 'MISSING_FIELDS':
            print("[System] Form elements not ready yet. Retrying submission in 5 seconds...", flush=True)
            QTimer.singleShot(5000, self.submit_login_credentials)
        else:
            print("[System] Waiting 10 seconds for post-login stabilization...", flush=True)
            QTimer.singleShot(10000, self.init_bot_state)

    def init_bot_state(self):
        js_init_data = """
        (function() {
            var bal = document.getElementById('pct_balance') ? document.getElementById('pct_balance').value : '0';
            return JSON.stringify({balance: bal});
        })();
        """
        self.browser.page().runJavaScript(js_init_data, self._init_state_callback)

    def _init_state_callback(self, res_json):
        global trueOriginalBalance, startingPocketChange, tinyPeanutSize, backupPeanut, tenPeanuts
        global walletStash, previousWalletState
        global currentWagerAmount, previousWagerAmount
        global checkpointJuice, wobbleFactor, safetyCheckpoint, safetyCheckpointtwo
        global last_observed_balance, last_balance_change_time, logged_in, last_bet_timestamp, last_activity_timestamp, watchdog_threshold, has_placed_first_bet

        try:
            data = json.loads(res_json)
            current_bal = round(float(str(data.get("balance", "0")).replace(",", "").strip()), 8)
        except Exception as e:
            print(f"[Debug] Init state parse error: {e} | Raw JSON: {res_json}", flush=True)
            current_bal = 0.0

        if current_bal <= 0 and not logged_in:
            print(f"[System] Balance read {current_bal} or session pending... re-checking balance in 5s", flush=True)
            QTimer.singleShot(5000, self.init_bot_state)
            return

        master_state = load_master_state()
        if master_state and "trueOriginalBalance" in master_state:
            trueOriginalBalance = float(master_state["trueOriginalBalance"])
        else:
            trueOriginalBalance = current_bal
            save_master_state(trueOriginalBalance)

        savedState = load_state()

        startingPocketChange = current_bal
        walletStash = current_bal

        calculated_tiny = float(startingPocketChange / 100.0)

        tinyPeanutSize = (
            float(savedState.get("tinyPeanutSize", calculated_tiny))
            if savedState
            else calculated_tiny
        )
        backupPeanut = float(savedState.get("backupPeanut", tinyPeanutSize)) if savedState else tinyPeanutSize
        tenPeanuts = float(savedState.get("tenPeanuts", tinyPeanutSize * 10)) if savedState else tinyPeanutSize * 10

        previousWalletState = float(savedState.get("previousWalletState", walletStash)) if savedState else walletStash
        
        currentWagerAmount = (
            float(savedState.get("currentWagerAmount", tinyPeanutSize)) if savedState else backupPeanut
        )
        previousWagerAmount = (
            float(savedState.get("previousWagerAmount", currentWagerAmount)) if savedState else currentWagerAmount
        )

        default_chk = walletStash
        checkpointJuice = (
            float(savedState.get("checkpointJuice", float((math.floor(default_chk / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10))))
            if savedState
            else float((math.floor(default_chk / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10))
        )
        wobbleFactor = float(savedState.get("wobbleFactor", 1.0)) if savedState else 1.0
        safetyCheckpoint = (
            float(savedState.get("safetyCheckpoint", float(((math.floor(default_chk / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)) - (tinyPeanutSize * 10))))
            if savedState
            else float(((math.floor(default_chk / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)) - (tinyPeanutSize * 10))
        )
        safetyCheckpointtwo = (
            float(savedState.get("safetyCheckpointtwo", float(((math.ceil(default_chk / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)) + (tinyPeanutSize * 10))))
            if savedState
            else float(((math.ceil(default_chk / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)) + (tinyPeanutSize * 10))
        )

        last_observed_balance = current_bal
        current_time = time.time()
        last_balance_change_time = current_time
        last_bet_timestamp = current_time
        last_activity_timestamp = current_time
        has_placed_first_bet = False
        watchdog_threshold = 10.0
        logged_in = True

        total_profit_init = walletStash - trueOriginalBalance
        print(f"[System] Login verified! Balance: {walletStash:.8f} | Master Original: {trueOriginalBalance:.8f} | Total Profit: {total_profit_init:+.8f}", flush=True)
        print("[Watchdog] Dynamic 10-second activity & betting stall watchdog is active and monitoring.", flush=True)
        self.timer.start(50)

    def runPrimaryBettingLoop(self):
        if not logged_in:
            return

        js_fetch_dom = """
        (function() {
            var bElem = document.getElementById('pct_balance');
            if (!bElem) { return JSON.stringify({error: 'DOM_NOT_READY'}); }
            var bal = bElem.value || '0';
            return JSON.stringify({balance: bal});
        })();
        """
        self.browser.page().runJavaScript(js_fetch_dom, self._process_loop_data)

    def _process_loop_data(self, res_json):
        global walletStash, last_observed_balance, last_balance_change_time
        global previousWagerAmount, previousWalletState
        global trueOriginalBalance, startingPocketChange, tinyPeanutSize, backupPeanut, tenPeanuts
        global currentWagerAmount, checkpointJuice, wobbleFactor, safetyCheckpoint, safetyCheckpointtwo
        global watchdog_threshold, last_bet_timestamp, last_activity_timestamp, has_placed_first_bet

        try:
            data = json.loads(res_json)
            if data.get("error") == "DOM_NOT_READY":
                return
            walletStash = round(float(str(data.get("balance", "0")).replace(",", "").strip()), 8)
        except Exception as e:
            print(f"[Debug] Loop parse error: {e} | Raw JSON: {res_json}", flush=True)
            return

        current_time = time.time()

        # Check if balance changed
        balance_changed = (walletStash == round((last_observed_balance + previousWagerAmount), 8) or walletStash == round((last_observed_balance - previousWagerAmount), 8))

        if walletStash > 0 and balance_changed:
            last_balance_change_time = current_time
            last_observed_balance = walletStash
            last_activity_timestamp = current_time

        elapsed_stagnation = current_time - last_balance_change_time

        if elapsed_stagnation >= watchdog_threshold or walletStash <= 0:
            print(f"[Watchdog] Balance has stalled, reloading page...", flush=True)
            self.trigger_watchdog_refresh()
            return

        # Target reached check (matching target threshold: startingPocketChange * 3)
        if walletStash >= (startingPocketChange * 3):
            total_profit = walletStash - trueOriginalBalance
            print(f"\n[System] TARGET REACHED ({walletStash:.8f}). Total Cumulative Profit: {total_profit:+.8f}. Halting execution.", flush=True)
            for f_path in [STATE_FILE, MASTER_STATE_FILE]:
                if os.path.exists(f_path):
                    try:
                        os.remove(f_path)
                    except Exception:
                        pass
            sys.exit(0)

        # Place a new bet if the balance changed OR if we haven't placed our first bet yet
        if balance_changed or not has_placed_first_bet:
            has_placed_first_bet = True
            computedNextBet = calculate_next_progression_step(previousWagerAmount)

            total_profit = walletStash - trueOriginalBalance
            log_bet_info(computedNextBet, walletStash, total_profit)

            js_place_bet = f"""
            (function() {{
                var bMin = document.getElementById('b_min');
                var pChance = document.getElementById('pct_chance');
                var pBet = document.getElementById('pct_bet');
                var aLo = document.getElementById('a_lo');

                if (!bMin || !pBet || !aLo) {{ return; }}

                bMin.click();
                if (pChance) {{ pChance.value = '49.5'; }}
                pBet.value = '{computedNextBet:.8f}';
                aLo.click();
            }})();
            """
            self.browser.page().runJavaScript(js_place_bet)
            previousWagerAmount = computedNextBet
            previousWalletState = walletStash
            last_bet_timestamp = time.time()
            watchdog_threshold = 10.0
            save_state()

    def trigger_watchdog_refresh(self):
        global watchdog_threshold, has_placed_first_bet
        self.timer.stop()
        self.browser.reload()
        
        has_placed_first_bet = False
        watchdog_threshold = min(watchdog_threshold + 5.0, 30.0)
        reload_delay = 30000 if walletStash <= 0 else 10000
        
        def resume_after_refresh():
            global last_balance_change_time, last_bet_timestamp, last_activity_timestamp
            t_now = time.time()
            last_balance_change_time = t_now
            last_bet_timestamp = t_now
            last_activity_timestamp = t_now
            self.timer.start(50)
            print(f"[Watchdog] Stream stabilized. Resuming betting loop.", flush=True)

        QTimer.singleShot(reload_delay, resume_after_refresh)


def main():
    global username, password, code_2fa

    username = input("User: ")
    password = pwinput.pwinput(prompt="Pass: ", mask="*")
    code_2fa = pwinput.pwinput(prompt="2FA (optional, press Enter to skip): ", mask="*")

    if sys.platform == "win32":
        os.environ["QT_OPENGL"] = "angle"
    else:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    app = QApplication(sys.argv)
    window = SnowyBotWindow()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()