#!/usr/bin/env python3
import json
import math
import os
import sys
import time
import pwinput

# Enforce software rendering, disable GPU/hardware acceleration, and mute audio
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--disable-gpu "
    "--disable-software-rasterizer "
    "--disable-dev-shm-usage "
    "--no-sandbox "
    "--mute-audio "
    "--disable-speech-api"
)

from PyQt5.QtCore import QUrl, QTimer, Qt, QEventLoop
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage

STATE_FILE = "bot_state.json"
MASTER_STATE_FILE = "bot_master_state.json"
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
watchdog_threshold = 15.0

username = ""
password = ""
code_2fa = ""
logged_in = False

_active_window = None

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

def get_balance():
    global _active_window
    if not _active_window or not hasattr(_active_window, "browser"):
        return float(walletStash)

    loop = QEventLoop()
    bal_result = [0.0]

    def callback(res_json):
        try:
            data = json.loads(res_json)
            if data.get("error") != "DOM_NOT_READY":
                bal_result[0] = round(float(str(data.get("balance", "0")).replace(",", "").strip()), 8)
        except Exception as e:
            print(f"[Debug] Get balance parse error: {e} | Raw JSON: {res_json}", flush=True)
        loop.quit()

    js_fetch_dom = """
    (function() {
        var bElem = document.getElementById('pct_balance');
        if (!bElem) { return JSON.stringify({error: 'DOM_NOT_READY'}); }
        var bal = bElem.value || '0';
        return JSON.stringify({balance: bal});
    })();
    """
    _active_window.browser.page().runJavaScript(js_fetch_dom, callback)
    loop.exec_()
    return bal_result[0]

def calculate_next_progression_step(incoming_wager):
    global walletStash, currentWagerAmount, wobbleFactor, checkpointJuice, safetyCheckpoint, tinyPeanutSize, backupPeanut, safetyCheckpointtwo, startingPocketChange

    base_wager = round(float(incoming_wager), 8)
    walletStash = get_balance()
    checkpointJuice = float(checkpointJuice)
    safetyCheckpoint = float(safetyCheckpoint)
    safetyCheckpointtwo = float(safetyCheckpointtwo)
    
    backupPeanut = tinyPeanutSize

    if walletStash >= round(safetyCheckpoint + ((tinyPeanutSize * 10) * wobbleFactor), 8):
        currentWagerAmount = round(float(tinyPeanutSize), 8)
        wobbleFactor = 1.0
        checkpointJuice = round(float((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)), 8)
        safetyCheckpoint = round(float((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)), 8)
        return currentWagerAmount
    
    if base_wager > backupPeanut:
        if walletStash > round(checkpointJuice + (base_wager * 5.0), 8):
            currentWagerAmount = round(float(base_wager * 2.0), 8)
            checkpointJuice = round(float(walletStash), 8)
        elif walletStash < round(checkpointJuice - (base_wager * 5.0), 8):
            currentWagerAmount = round(float(base_wager * 2.0), 8)
            wobbleFactor = 0.0
            checkpointJuice = round(float(walletStash), 8)
        else:
            currentWagerAmount = base_wager
            
    if base_wager <= backupPeanut:
        if walletStash > round(checkpointJuice + round(base_wager * 7.0, 8), 8):
            currentWagerAmount = round(float(base_wager * 2.0), 8)
            checkpointJuice = round(float(walletStash), 8)
        elif walletStash < round(checkpointJuice - round(base_wager * 3.0, 8), 8):
            currentWagerAmount = round(float(base_wager * 2.0), 8)
            checkpointJuice = round(float(walletStash), 8)
        else:
            currentWagerAmount = base_wager

    return round(float(currentWagerAmount), 8)

def log_bet_info(bet_amount, current_balance, total_profit):
    print(f"Bet: {bet_amount:.8f} | Balance: {current_balance:.8f} | Total Profit: {total_profit:+.8f}", flush=True)

class SnowyBotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        global _active_window
        _active_window = self

        self.setWindowTitle("Snowy Bot - WolfBet Logic Engine (QtWebEngine)")
        self.resize(1024, 768)

        self.watchdog_fail_count = 0
        self.login_fail_count = 0

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
            profile.cookieStore().deleteAllCookies()

        ua_string = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            if sys.platform == "win32"
            else "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        profile.setHttpUserAgent(ua_string)

        page = QWebEnginePage(profile, self)
        self.browser = QWebEngineView()
        self.browser.setPage(page)
        
        self.is_loaded = False
        page.loadFinished.connect(self._handle_load_finished)
        
        self.setCentralWidget(self.browser)

    def _handle_load_finished(self, ok):
        if ok:
            print("[Watchdog] Webview successfully finished loading page content.", flush=True)
            self.is_loaded = True
        else:
            print("[Watchdog Warning] Webview page load signal received with errors.", flush=True)
            self.is_loaded = False

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
            self.login_fail_count += 1
            if self.login_fail_count >= 2:
                print("[System] Form elements still missing. Reloading webview...", flush=True)
                self.login_fail_count = 0
                self.browser.reload()
                print("[System] Waiting 10 seconds after reload for page stabilization...", flush=True)
                QTimer.singleShot(10000, self.open_account_tab)
            else:
                print(f"[System] Form elements not ready yet (Attempt {self.login_fail_count}/2). Retrying submission in 5 seconds...", flush=True)
                QTimer.singleShot(5000, self.submit_login_credentials)
        else:
            self.login_fail_count = 0  # Reset on successful submission
            print("[System] Waiting 10 seconds for post-login stabilization...", flush=True)
            QTimer.singleShot(10000, self.init_bot_state)

    def init_bot_state(self):
        global trueOriginalBalance, startingPocketChange, tinyPeanutSize, backupPeanut, tenPeanuts
        global walletStash, previousWalletState, safetyCheckpoint
        global currentWagerAmount, previousWagerAmount
        global checkpointJuice, wobbleFactor, safetyCheckpointtwo
        global last_observed_balance, last_balance_change_time, logged_in, last_bet_timestamp, last_activity_timestamp, watchdog_threshold, has_placed_first_bet

        current_bal = get_balance()

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

        startingPocketChange = float(current_bal)
        walletStash = float(current_bal)

        calculated_tiny = float(startingPocketChange / 1440000.0)

        tinyPeanutSize = (
            float(savedState.get("tinyPeanutSize", calculated_tiny))
            if savedState
            else calculated_tiny
        )
        backupPeanut = tinyPeanutSize
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
            float(savedState.get("safetyCheckpointtwo", float((math.floor(default_chk / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10))))
            if savedState
            else float((math.floor(default_chk / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10))
        )

        last_observed_balance = current_bal
        current_time = time.time()
        last_balance_change_time = current_time
        last_bet_timestamp = current_time
        last_activity_timestamp = current_time
        has_placed_first_bet = False
        watchdog_threshold = 15.0
        logged_in = True

        total_profit_init = walletStash - trueOriginalBalance
        print(f"[System] Login verified! Balance: {walletStash:.8f} | Master Original: {trueOriginalBalance:.8f} | Total Profit: {total_profit_init:+.8f}", flush=True)
        print("[Watchdog] Dynamic 15-second activity & betting stall watchdog is active and monitoring.", flush=True)
        self.timer.start(1000)

    def runPrimaryBettingLoop(self):
        global logged_in
        if not logged_in:
            return

        if not getattr(self, "is_loaded", False):
            return

        global walletStash, last_observed_balance, last_balance_change_time
        global previousWagerAmount, previousWalletState
        global trueOriginalBalance, startingPocketChange, tinyPeanutSize, backupPeanut, tenPeanuts
        global currentWagerAmount, checkpointJuice, wobbleFactor, safetyCheckpoint, safetyCheckpointtwo
        global watchdog_threshold, last_bet_timestamp, last_activity_timestamp, has_placed_first_bet

        walletStash = get_balance()
        if walletStash <= 0:
            print("[Watchdog Warning] Session unauthenticated or balance unavailable. Triggering relogin watchdog...", flush=True)
            logged_in = False
            self.trigger_watchdog_refresh()
            return

        current_time = time.time()

        balance_changed = (walletStash == round((last_observed_balance + previousWagerAmount), 8) or walletStash == round((last_observed_balance - previousWagerAmount), 8))
        
        seriously_retarded_hacker_stopper_threshold = ((walletStash == last_observed_balance) or balance_changed)
        if not seriously_retarded_hacker_stopper_threshold:
            print("seriously_retarded_hacker_stopper activated, exiting...")
            sys.exit(0)

        if walletStash > 0 and balance_changed:
            self.watchdog_fail_count = 0  
            last_balance_change_time = current_time
            last_observed_balance = walletStash
            last_activity_timestamp = current_time

        elapsed_stagnation = current_time - last_balance_change_time

        if elapsed_stagnation >= watchdog_threshold:
            print(f"[Watchdog] Balance has stalled, triggering cookie wipe and relogin sequence...", flush=True)
            self.trigger_watchdog_refresh()
            return

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
            watchdog_threshold = 15.0
            save_state()

    def trigger_watchdog_refresh(self):
        global logged_in, has_placed_first_bet, watchdog_threshold
        self.timer.stop()
        logged_in = False
        self.is_loaded = False 
        self.watchdog_fail_count += 1

        print("[Watchdog] Clearing cookies, site data, and restarting full login sequence...", flush=True)
        
        self.browser.page().profile().cookieStore().deleteAllCookies()
        self.browser.page().profile().clearHttpCache()

        has_placed_first_bet = False
        watchdog_threshold = min(watchdog_threshold + 5.0, 30.0)
        
        self.start_full_login_sequence(wipe_data=True)

def main():
    global username, password, code_2fa

    username = input("User: ")
    password = pwinput.pwinput(prompt="Pass: ", mask="*")
    code_2fa = pwinput.pwinput(prompt="2FA (optional, press Enter to skip): ", mask="*")

    if sys.platform == "win32":
        os.environ["QT_OPENGL"] = "angle"
    else:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["PULSE_SERVER"] = ""
        os.environ["SDL_AUDIODRIVER"] = "dummy"

    app = QApplication(sys.argv)
    window = SnowyBotWindow()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()