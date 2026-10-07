#!/usr/init/env python3
import json
import math
import os
import sys
import time
import shutil
import tempfile
import pwinput

from PyQt5.QtCore import QUrl, QTimer, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage

STATE_FILE = "bot_state.json"
LOG_OUT = "bot_output.log"
LOG_ERR = "bot_error.log"

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
last_bet_timestamp = 0.0

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


def calculate_next_progression_step(incoming_wager):
    global walletStash, currentWagerAmount, wobbleFactor, checkpointJuice, safetyCheckpoint

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
        currentWagerAmount *= 2
        checkpointJuice = float(walletStash)

    if (currentWagerAmount < (backupPeanut * 1.5)) and (
        walletStash < (checkpointJuice - (currentWagerAmount * 2.9))
    ):
        currentWagerAmount *= 2
        checkpointJuice = float(walletStash)

    if (currentWagerAmount > (backupPeanut * 1.5)) and (
        walletStash > (checkpointJuice + (currentWagerAmount * 4.9))
    ):
        currentWagerAmount *= 2
        checkpointJuice = float(walletStash)

    if (currentWagerAmount > (backupPeanut * 1.5)) and (
        walletStash < (checkpointJuice - (currentWagerAmount * 4.9))
    ):
        currentWagerAmount *= 2
        wobbleFactor = 0.0
        checkpointJuice = float(walletStash)

    return round(float(currentWagerAmount), 8)


def log_bet_info(bet_amount, current_balance, current_profit, wager_id):
    global last_logged_wager_id
    if wager_id and wager_id > 0 and wager_id == last_logged_wager_id:
        return
    if wager_id and wager_id > 0:
        last_logged_wager_id = wager_id
    print(f"Bet: {bet_amount:.8f} | Balance: {current_balance:.8f} | Profit: {current_profit:+.8f}")


class SnowyBotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Snowy Bot - PySide5 Reset-Compounding Engine")
        self.resize(1024, 768)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.runPrimaryBettingLoop)

        self.start_full_login_sequence()

    def init_browser_engine(self):
        if hasattr(self, 'temp_dir') and self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

        self.temp_dir = tempfile.mkdtemp(prefix="snowy_profile_")
        profile_name = f"SnowyProfile_{time.time()}"
        profile = QWebEngineProfile(profile_name, self)
        profile.setPersistentStoragePath(self.temp_dir)
        profile.setCachePath(self.temp_dir)

        profile.setHttpUserAgent(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        page = QWebEnginePage(profile, self)
        self.browser = QWebEngineView()
        self.browser.setPage(page)
        self.setCentralWidget(self.browser)

    def start_full_login_sequence(self):
        global logged_in
        logged_in = False
        
        self.init_browser_engine()

        print(f"[System] Created isolated storage at {self.temp_dir}. Navigating to just-dice.com...")
        self.browser.setUrl(QUrl("https://just-dice.com"))

        print("[System] Waiting 40 seconds for page scripts and WebSocket engine to stabilize...")
        QTimer.singleShot(40000, self.open_account_tab)

    def open_account_tab(self):
        print("[System] Dismissing modals and locating Account/Login interface...")
        js_nav = """
        (function() {
            var closeBtn = document.querySelector('a.fancybox-item.fancybox-close');
            if (closeBtn) { closeBtn.click(); }
            
            if (document.getElementById('myuser')) { return 'ALREADY_VISIBLE'; }

            var elements = Array.from(document.querySelectorAll('a, button, span'));
            var target = elements.find(el => {
                var txt = el.textContent.trim().toLowerCase();
                return txt === 'account' || txt === 'login' || txt.includes('account');
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
        print(f"[System] Account tab navigation result: {status}")
        print("[System] Waiting 40 seconds for account tab and login input fields...")
        QTimer.singleShot(40000, self.submit_login_credentials)

    def submit_login_credentials(self):
        global username, password, code_2fa
        print("[System] Submitting authentication payload to DOM...")

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
                var elements = Array.from(document.querySelectorAll('a, button, span'));
                var target = elements.find(el => el.textContent.trim().toLowerCase() === 'account');
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
        print(f"[System] Credentials action: {status}")
        if status == 'MISSING_FIELDS':
            print("[System] Form elements not ready yet. Retrying submission in 5 seconds...")
            QTimer.singleShot(5000, self.submit_login_credentials)
        else:
            print("[System] Waiting 40 seconds for post-login stabilization...")
            QTimer.singleShot(40000, self.init_bot_state)

    def init_bot_state(self):
        js_init_data = """
        (function() {
            var bal = document.getElementById('pct_balance') ? document.getElementById('pct_balance').value : '0';
            var me = document.getElementById('me');
            var wagerId = 0;
            if (me && me.firstElementChild && me.firstElementChild.lastElementChild && me.firstElementChild.lastElementChild.firstElementChild) {
                var row = me.firstElementChild.lastElementChild.firstElementChild;
                wagerId = row.children[5] ? row.children[5].innerText : 0;
            }
            return JSON.stringify({balance: bal, wagerId: wagerId});
        })();
        """
        self.browser.page().runJavaScript(js_init_data, self._init_state_callback)

    def _init_state_callback(self, res_json):
        global startingPocketChange, tinyPeanutSize, backupPeanut, tenPeanuts
        global walletStash, areWeRichYet, oopsieCounter, previousWalletState
        global oldTicketStub, shinyNewTicket, totalSessionWins, totalSessionLosses
        global baseWinReference, baseLossReference, currentWagerAmount, previousWagerAmount
        global luckyCoinFlip, checkpointJuice, wobbleFactor, safetyCheckpoint
        global last_observed_balance, last_balance_change_time, logged_in, last_bet_timestamp

        try:
            data = json.loads(res_json)
            current_bal = float(str(data.get("balance", "0")).replace(",", "").strip())
            current_wager = int(float(str(data.get("wagerId", "0")).replace(",", "").strip()))
        except Exception:
            current_bal = 0.0
            current_wager = 0

        if current_bal <= 0 and not logged_in:
            print("[System] Balance read 0 or session pending... re-checking balance in 5s")
            QTimer.singleShot(5000, self.init_bot_state)
            return

        savedState = load_state()

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
        
        oldTicketStub = current_wager
        shinyNewTicket = current_wager

        totalSessionWins = savedState.get("totalSessionWins", 0) if savedState else 0
        totalSessionLosses = savedState.get("totalSessionLosses", 0) if savedState else 0
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
        last_bet_timestamp = 0.0
        logged_in = True

        print(f"[System] Login verified! Balance loaded: {walletStash:.8f} (Baseline: {startingPocketChange:.8f})")
        self.timer.start(50)

    def runPrimaryBettingLoop(self):
        if not logged_in:
            return

        js_fetch_dom = """
        (function() {
            var bal = document.getElementById('pct_balance') ? document.getElementById('pct_balance').value : '0';
            var wins = document.getElementById('wins') ? document.getElementById('wins').innerText : '0';
            var losses = document.getElementById('losses') ? document.getElementById('losses').innerText : '0';
            var me = document.getElementById('me');
            var wagerId = 0, rollVal = -1;
            if (me && me.firstElementChild && me.firstElementChild.lastElementChild && me.firstElementChild.lastElementChild.firstElementChild) {
                var row = me.firstElementChild.lastElementChild.firstElementChild;
                wagerId = row.children[5] ? row.children[5].innerText : 0;
                rollVal = row.children[7] ? row.children[7].innerText : -1;
            }
            return JSON.stringify({balance: bal, wins: wins, losses: losses, wagerId: wagerId, rollVal: rollVal});
        })();
        """
        self.browser.page().runJavaScript(js_fetch_dom, self._process_loop_data)

    def _process_loop_data(self, res_json):
        global walletStash, last_observed_balance, last_balance_change_time
        global shinyNewTicket, oldTicketStub, oopsieCounter, previousWagerAmount
        global previousWalletState, luckyCoinFlip, baseWinReference, baseLossReference
        global totalSessionWins, totalSessionLosses, last_bet_timestamp

        try:
            data = json.loads(res_json)
            walletStash = float(str(data.get("balance", "0")).replace(",", "").strip())
            totalSessionWins = int(float(str(data.get("wins", "0")).replace(",", "").strip()))
            totalSessionLosses = int(float(str(data.get("losses", "0")).replace(",", "").strip()))
            shinyNewTicket = int(float(str(data.get("wagerId", "0")).replace(",", "").strip()))
            currentRollVal = float(str(data.get("rollVal", "-1")).replace(",", "").strip())
        except Exception:
            return

        if walletStash != last_observed_balance:
            last_observed_balance = walletStash
            last_balance_change_time = time.time()

        # Compounding Milestone Check: 10% profit reached -> wipe state file & restart login sequence
        if walletStash >= (startingPocketChange * 1.10):
            profit = walletStash - startingPocketChange
            print(f"\n[Compound Milestone] 10% profit reached (+{profit:.8f})!")
            print(f"[Compound Milestone] Wiping state file and restarting login with new baseline: {walletStash:.8f}")
            
            self.timer.stop()
            if os.path.exists(STATE_FILE):
                try:
                    os.remove(STATE_FILE)
                except Exception:
                    pass
            
            # Restart full login sequence with a clean state
            self.start_full_login_sequence()
            return

        if time.time() - last_balance_change_time >= 30:
            print("[Watchdog] Timeout: No successful activity for 30s. Restarting full login sequence...")
            self.timer.stop()
            last_balance_change_time = time.time()
            self.start_full_login_sequence()
            return

        time_since_last_bet = time.time() - last_bet_timestamp
        can_bet_by_time = (last_bet_timestamp == 0 or time_since_last_bet >= 0.01)

        if (shinyNewTicket > oldTicketStub) or (oopsieCounter == 0) or can_bet_by_time:
            computedNextBet = calculate_next_progression_step(previousWagerAmount)

            if walletStash >= 144000:
                print(f"[System] TARGET REACHED ({walletStash:.8f}). Halting execution.")
                if os.path.exists(STATE_FILE):
                    try:
                        os.remove(STATE_FILE)
                    except Exception:
                        pass
                sys.exit(0)

            if 0 <= currentRollVal < 49.5000:
                luckyCoinFlip = 1
            elif currentRollVal >= 49.5000:
                luckyCoinFlip = 0

            should_place_bet = False

            if oopsieCounter == 0 or can_bet_by_time:
                should_place_bet = True
            elif shinyNewTicket > oldTicketStub and luckyCoinFlip == 0 and totalSessionLosses == baseLossReference + 1 and totalSessionWins == baseWinReference:
                should_place_bet = True
                baseLossReference = float(totalSessionLosses)
            elif shinyNewTicket > oldTicketStub and luckyCoinFlip == 1 and totalSessionWins == baseWinReference + 1 and totalSessionLosses == baseLossReference:
                should_place_bet = True
                baseWinReference = float(totalSessionWins)

            if should_place_bet:
                log_bet_info(computedNextBet, walletStash, walletStash - startingPocketChange, shinyNewTicket)

                js_place_bet = f"""
                (function() {{
                    var bMin = document.getElementById('b_min');
                    var pChance = document.getElementById('pct_chance');
                    var pBet = document.getElementById('pct_bet');
                    var aLo = document.getElementById('a_lo');

                    if (bMin) bMin.click();
                    if (pChance) {{ pChance.value = '49.5'; }}
                    if (pBet) {{ pBet.value = '{computedNextBet:.8f}'; }}
                    if (aLo) aLo.click();
                }})();
                """
                self.browser.page().runJavaScript(js_place_bet)

                previousWagerAmount = float(computedNextBet)
                previousWalletState = float(walletStash)
                if shinyNewTicket > 0:
                    oldTicketStub = float(shinyNewTicket)
                oopsieCounter += 1
                
                last_bet_timestamp = time.time()
                last_balance_change_time = time.time()
                save_state()


def main():
    global username, password, code_2fa

    username = input("User: ")
    password = pwinput.pwinput(prompt="Pass: ", mask="*")
    code_2fa = pwinput.pwinput(prompt="2FA (optional, press Enter to skip): ", mask="*")
    print("Initializing PySide5 Reset-Compounding Headless Engine...")

    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    app = QApplication(sys.argv)
    window = SnowyBotWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
