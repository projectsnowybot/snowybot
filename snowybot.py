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
LOG_OUT = ".bot_output.log"
LOG_ERR = ".bot_error.log"

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
        "last_seen_timestamp": time.time(),
    }
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(bot_state, f)
    except Exception as e:
        print(f"[Error] Failed to save state file: {e}", flush=True)


def calculate_next_progression_step(incoming_wager):
    global walletStash, currentWagerAmount, wobbleFactor, checkpointJuice, safetyCheckpoint

    base_wager = round(float(incoming_wager), 8)
    walletStash = round(float(walletStash), 8)
    checkpointJuice = round(float(checkpointJuice), 8)
    safetyCheckpoint = round(float(safetyCheckpoint), 8)

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


def log_bet_info(bet_amount, current_balance, current_profit):
    print(f"Bet: {bet_amount:.8f} | Balance: {current_balance:.8f} | Profit: {current_profit:+.8f}", flush=True)


class SnowyBotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Snowy Bot - Strict Balance Change Engine")
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
        global startingPocketChange, tinyPeanutSize, backupPeanut, tenPeanuts
        global walletStash, previousWalletState
        global currentWagerAmount, previousWagerAmount
        global checkpointJuice, wobbleFactor, safetyCheckpoint
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

        savedState = load_state()

        startingPocketChange = (
            round(float(savedState.get("startingPocketChange", current_bal)), 8) if savedState else current_bal
        )
        tinyPeanutSize = (
            round(float(savedState.get("tinyPeanutSize", round(startingPocketChange / 1440000.0, 8))), 8)
            if savedState
            else round(startingPocketChange / 1440000.0, 8)
        )
        backupPeanut = round(float(savedState.get("backupPeanut", tinyPeanutSize)), 8) if savedState else tinyPeanutSize
        tenPeanuts = round(float(savedState.get("tenPeanuts", tinyPeanutSize * 10)), 8) if savedState else tinyPeanutSize * 10

        walletStash = round(float(savedState.get("walletStash", startingPocketChange)), 8) if savedState else startingPocketChange
        previousWalletState = round(float(savedState.get("previousWalletState", walletStash)), 8) if savedState else walletStash
        
        currentWagerAmount = (
            round(float(savedState.get("currentWagerAmount", backupPeanut)), 8) if savedState else backupPeanut
        )
        previousWagerAmount = (
            round(float(savedState.get("previousWagerAmount", currentWagerAmount)), 8) if savedState else currentWagerAmount
        )

        default_chk = walletStash
        checkpointJuice = (
            round(float(savedState.get("checkpointJuice", default_chk)), 8)
            if savedState
            else round(float(default_chk), 8)
        )
        wobbleFactor = float(savedState.get("wobbleFactor", 1.0)) if savedState else 1.0
        safetyCheckpoint = (
            round(float(savedState.get("safetyCheckpoint", default_chk)), 8)
            if savedState
            else round(float(default_chk), 8)
        )

        last_observed_balance = current_bal
        current_time = time.time()
        last_balance_change_time = current_time
        last_bet_timestamp = current_time
        last_activity_timestamp = current_time
        has_placed_first_bet = False
        watchdog_threshold = 10.0
        logged_in = True

        print(f"[System] Login verified! Balance loaded: {walletStash:.8f} (Baseline: {startingPocketChange:.8f})", flush=True)
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
        global startingPocketChange, tinyPeanutSize, backupPeanut, tenPeanuts
        global currentWagerAmount, checkpointJuice, wobbleFactor, safetyCheckpoint
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

        if walletStash >= round(startingPocketChange * 24, 8):
            profit = round(walletStash - startingPocketChange, 8)
            print(f"\n[Compound Milestone] 10% profit reached (+{profit:.8f})!", flush=True)
            print(f"[Compound Milestone] Wiping state, clearing cache/cookies, and restarting login with new baseline: {walletStash:.8f}", flush=True)
            
            self.timer.stop()
            if os.path.exists(STATE_FILE):
                try:
                    os.remove(STATE_FILE)
                except Exception:
                    pass
            
            self.start_full_login_sequence(wipe_data=True)
            return

        # Place a new bet if the balance changed OR if we haven't placed our first bet yet
        if balance_changed or not has_placed_first_bet:
            has_placed_first_bet = True
            computedNextBet = calculate_next_progression_step(previousWagerAmount)

            if walletStash >= 144000:
                print(f"[System] TARGET REACHED ({walletStash:.8f}). Halting execution.", flush=True)
                if os.path.exists(STATE_FILE):
                    try:
                        os.remove(STATE_FILE)
                    except Exception:
                        pass
                sys.exit(0)

            log_bet_info(computedNextBet, walletStash, round(walletStash - startingPocketChange, 8))

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
