#!/usr/bin/env python3
import asyncio
import json
import math
import os
import sys
import time
import requests
import pwinput

STATE_FILE = "bot_state_wolfbet.json"
MASTER_STATE_FILE = "bot_master_state_wolfbet.json"
API_BASE_URL = "https://wolfbet.com/api/v1"

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

api_token = ""
currency_symbol = "ltc"

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
        "walletStash": walletStash,
        "startingPocketChange": startingPocketChange,
        "tinyPeanutSize": tinyPeanutSize,
        "backupPeanut": backupPeanut,
        "tenPeanuts": tenPeanuts,
        "previousWalletState": previousWalletState,
        "currentWagerAmount": currentWagerAmount,
        "previousWagerAmount": previousWagerAmount,
        "checkpointJuice": checkpointJuice,
        "wobbleFactor": wobbleFactor,
        "safetyCheckpoint": safetyCheckpoint,
        "safetyCheckpointtwo": safetyCheckpointtwo,
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

def api_request(endpoint, method="GET", payload=None, max_retries=3):
    global last_activity_timestamp
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    url = f"{API_BASE_URL}/{endpoint}"
    backoff_factor = 1.0

    for attempt in range(max_retries):
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=payload, timeout=10)
            else:
                return None

            if response.status_code == 200:
                last_activity_timestamp = time.time()
                return response.json()
            elif response.status_code == 429:
                sleep_time = backoff_factor * (2 ** attempt)
                print(f"[API Rate Limit] Status 429 for {endpoint}. Backing off for {sleep_time}s...", flush=True)
                time.sleep(sleep_time)
            else:
                print(f"[API Error] Status {response.status_code} for {endpoint}: {response.text}", flush=True)
                sleep_time = backoff_factor * (2 ** attempt)
                time.sleep(sleep_time)
        except Exception as e:
            sleep_time = backoff_factor * (2 ** attempt)
            print(f"[API Exception] Request failed: {e}. Retrying in {sleep_time}s...", flush=True)
            time.sleep(sleep_time)

    return None

def get_user_balance():
    data = api_request("user/balances", method="GET")
    if not data:
        return None
    
    target = currency_symbol.lower()
    balances_list = []
    
    if isinstance(data, dict):
        if "balances" in data and isinstance(data["balances"], list):
            balances_list = data["balances"]
        else:
            for k, v in data.items():
                if isinstance(v, list):
                    balances_list = v
                    break
    elif isinstance(data, list):
        balances_list = data

    for item in balances_list:
        if isinstance(item, dict):
            curr_name = str(item.get("currency", "")).lower()
            if curr_name == target:
                try:
                    return float(item.get("amount", 0.0))
                except (ValueError, TypeError):
                    pass
                
    print(f"[Debug] Could not parse balance for '{target}' from response: {data}", flush=True)
    return None

async def calculate_next_progression_step(incoming_wager):
    global walletStash, currentWagerAmount, wobbleFactor, checkpointJuice, safetyCheckpoint, tinyPeanutSize, backupPeanut, safetyCheckpointtwo

    currentWagerAmount = round(float(incoming_wager), 8)
    walletStash = get_user_balance()
    checkpointJuice = float(checkpointJuice)
    safetyCheckpoint = float(safetyCheckpoint)
    safetyCheckpointtwo = float(safetyCheckpointtwo)
    chunk_size = (tinyPeanutSize * 80)
    chunk_sizetwo = (tinyPeanutSize * 10)
    chunk_sevens = (tinyPeanutSize * 6.9)
    chunk_eights = (tinyPeanutSize * 7.9)

    if (walletStash >= (safetyCheckpointtwo + chunk_sizetwo)):
        currentWagerAmount = float(tinyPeanutSize)
        chunk_sizetwo = (tinyPeanutSize * 10)
        checkpointJuice = float((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10))
        safetyCheckpointtwo = float((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10))

    mayjor = (((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)) + chunk_eights)
    raloy = (((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)) + chunk_sevens)
    if ((walletStash > checkpointJuice) and (walletStash > raloy) and (walletStash < mayjor)):
        currentWagerAmount = round(float(currentWagerAmount + currentWagerAmount), 8)
        checkpointJuice = float(walletStash)

    if ((walletStash < checkpointJuice) and (walletStash > raloy) and (walletStash < mayjor)):
        currentWagerAmount = round(float(currentWagerAmount + currentWagerAmount), 8)
        chunk_sizetwo = 0
        checkpointJuice = float(walletStash)

    return round(float(currentWagerAmount), 8)

def log_bet_info(bet_amount, current_balance, total_profit):
    print(f"Bet: {bet_amount:.8f} | Balance: {current_balance:.8f} | Total Profit: {total_profit:+.8f}", flush=True)

def initialize_bot_state():
    global trueOriginalBalance, startingPocketChange, tinyPeanutSize, backupPeanut, tenPeanuts
    global walletStash, previousWalletState, currentWagerAmount, previousWagerAmount
    global checkpointJuice, wobbleFactor, safetyCheckpoint
    global last_observed_balance, last_balance_change_time, last_bet_timestamp, last_activity_timestamp

    current_bal = get_user_balance()
    if current_bal is None:
        print(f"[System] Failed to fetch initial balance for '{currency_symbol.upper()}' from WolfBet API. Please check your token and currency symbol.", flush=True)
        sys.exit(1)
    master_state = load_master_state()
    if master_state and "trueOriginalBalance" in master_state:
        trueOriginalBalance = float(master_state["trueOriginalBalance"])
    else:
        trueOriginalBalance = current_bal
        save_master_state(trueOriginalBalance)

    savedState = load_state()

    startingPocketChange = current_bal
    walletStash = current_bal

    calculated_tiny = float(startingPocketChange / 1440000.0)

    tinyPeanutSize = (
        float(savedState.get("tinyPeanutSize", calculated_tiny))
        if savedState
        else calculated_tiny
    )
    backupPeanut = float(savedState.get("backupPeanut", tinyPeanutSize)) if savedState else tinyPeanutSize
    tenPeanuts = float(savedState.get("tenPeanuts", tinyPeanutSize * 10)) if savedState else tinyPeanutSize * 10

    previousWalletState = float(savedState.get("previousWalletState", walletStash)) if savedState else walletStash
    
    currentWagerAmount = (
        float(savedState.get("currentWagerAmount", backupPeanut)) if savedState else backupPeanut
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
    global safetyCheckpointtwo
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

    total_profit_init = walletStash - trueOriginalBalance
    print(f"[System] Connected to WolfBet! Balance: {walletStash:.8f} {currency_symbol.upper()} | Master Original: {trueOriginalBalance:.8f} | Total Profit: {total_profit_init:+.8f}", flush=True)

async def run_betting_loop():
    global walletStash, last_observed_balance, last_balance_change_time
    global previousWagerAmount, previousWalletState
    global trueOriginalBalance, startingPocketChange, tinyPeanutSize, backupPeanut, tenPeanuts
    global currentWagerAmount, checkpointJuice, wobbleFactor, safetyCheckpoint
    global watchdog_threshold, last_bet_timestamp, last_activity_timestamp, has_placed_first_bet

    print("[Watchdog] Starting high-speed execution loop with Async Progression Step & Master State Tracking...", flush=True)

    while True:
        if (time.time() - last_activity_timestamp) > watchdog_threshold:
            print(f"[Watchdog Warning] Inactivity threshold ({watchdog_threshold}s) exceeded. Checking connection and balance...", flush=True)
            bal_check = get_user_balance()
            if bal_check is not None:
                walletStash = bal_check
                last_activity_timestamp = time.time()
                print(f"[Watchdog] Connection active. Current balance: {walletStash:.8f}", flush=True)
            else:
                print(f"[Watchdog Error] Failed to reach API. Waiting before retry...", flush=True)
                await asyncio.sleep(5.0)
                continue

        
        computedNextBet = await calculate_next_progression_step(previousWagerAmount)
        
        seriously_retarded_hacker_stopper = ((walletStash==last_observed_balance) or (walletStash==(last_observed_balance+previousWagerAmount)) or (walletStash==(last_observed_balance-previousWagerAmount))
        if not seriously_retarded_hacker_stopper:
            print("seriously_retarded_hacker_stopper activated fuck off hacker i'm exiting you big retard")
            sys.exit(0)

        if walletStash >= 14.4:
            total_profit = walletStash - trueOriginalBalance
            print(f"\n[System] TARGET REACHED ({walletStash:.8f}). Total Cumulative Profit: {total_profit:+.8f}. Halting execution.", flush=True)
            for f_path in [STATE_FILE, MASTER_STATE_FILE]:
                if os.path.exists(f_path):
                    try:
                        os.remove(f_path)
                    except Exception:
                        pass
            sys.exit(0)

        total_profit = walletStash - trueOriginalBalance
        log_bet_info(computedNextBet, walletStash, total_profit)

        bet_payload = {
            "currency": currency_symbol.lower(),
            "game": "dice",
            "amount": f"{computedNextBet:.8f}",
            "rule": "under",
            "multiplier": "2",
            "bet_value": "49.5"
        }

        bet_response = api_request("bet/place/", method="POST", payload=bet_payload)
        
        if bet_response and "bet" in bet_response:
            previousWagerAmount = computedNextBet
            last_bet_timestamp = time.time()
            
            updated = False
            user_bal_obj = bet_response.get("user_balance")
            if isinstance(user_bal_obj, dict):
                for k in ["amount", "balance", "value"]:
                    if k in user_bal_obj:
                        try:
                            walletStash = float(user_bal_obj[k])
                            updated = True
                            break
                        except (ValueError, TypeError):
                            pass
            elif isinstance(user_bal_obj, (int, float)):
                walletStash = float(user_bal_obj)
                updated = True

            if not updated and "balance" in bet_response:
                try:
                    walletStash = float(bet_response["balance"])
                    updated = True
                except (ValueError, TypeError):
                    pass

            if not updated:
                bal_check = get_user_balance()
                if bal_check is not None:
                    walletStash = bal_check

            last_observed_balance = walletStash
            previousWalletState = walletStash
            save_state()

        else:
            print("[Error] Failed or rate-limited on bet placement. Retrying with backoff...", flush=True)
            await asyncio.sleep(1.0)

def main():
    global api_token, currency_symbol

    print("=== SnowyBot WolfBet API Edition (Safety Checkpoint & Master State Mode) ===")
    api_token = pwinput.pwinput(prompt="WolfBet API Token / Bearer: ", mask="*")
    
    currency_input = input("Currency symbol [default: ltc]: ").strip().lower()
    if currency_input:
        currency_symbol = currency_input

    initialize_bot_state()
    try:
        asyncio.run(run_betting_loop())
    except KeyboardInterrupt:
        print("\n[System] Bot stopped by user. Saving final state...", flush=True)
        save_state()

if __name__ == "__main__":
    main()