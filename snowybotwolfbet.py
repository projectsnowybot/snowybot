#!/usr/bin/env python3
import json
import math
import os
import sys
import time
import requests
import pwinput

STATE_FILE = ".bot_state_wolfbet.json"
API_BASE_URL = "https://wolfbet.com/api/v1"

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

api_token = ""
currency_symbol = "btc"  # Change to your target currency (e.g., 'doge', 'ltc', 'eth', etc.)

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

def api_request(endpoint, method="GET", payload=None):
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    url = f"{API_BASE_URL}/{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=payload, timeout=10)
        else:
            return None

        if response.status_code == 200:
            return response.json()
        else:
            print(f"[API Error] Status {response.status_code}: {response.text}", flush=True)
            return None
    except Exception as e:
        print(f"[API Exception] Request failed: {e}", flush=True)
        return None

def get_user_balance():
    data = api_request("user/balances", method="GET")
    if data and isinstance(data, dict):
        # WolfBet returns balances dictionary keyed by currency
        curr_data = data.get(currency_symbol.lower())
        if curr_data:
            return round(float(curr_data.get("amount", 0.0)), 8)
    return None

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

def initialize_bot_state():
    global startingPocketChange, tinyPeanutSize, backupPeanut, tenPeanuts
    global walletStash, previousWalletState, currentWagerAmount, previousWagerAmount
    global checkpointJuice, wobbleFactor, safetyCheckpoint
    global last_observed_balance, last_balance_change_time, last_bet_timestamp, last_activity_timestamp

    current_bal = get_user_balance()
    if current_bal is None:
        print("[System] Failed to fetch initial balance from WolfBet API. Please check your API token.", flush=True)
        sys.exit(1)

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

    print(f"[System] Connected to WolfBet! Balance loaded: {walletStash:.8f} {currency_symbol.upper()} (Baseline: {startingPocketChange:.8f})", flush=True)

def run_betting_loop():
    global walletStash, last_observed_balance, last_balance_change_time
    global previousWagerAmount, previousWalletState
    global startingPocketChange, tinyPeanutSize, backupPeanut, tenPeanuts
    global currentWagerAmount, checkpointJuice, wobbleFactor, safetyCheckpoint
    global watchdog_threshold, last_bet_timestamp, last_activity_timestamp, has_placed_first_bet

    print("[Watchdog] Starting headless betting engine loop...", flush=True)

    while True:
        current_time = time.time()
        current_bal = get_user_balance()

        if current_bal is None:
            print("[Warning] Could not fetch balance. Retrying in 5 seconds...", flush=True)
            time.sleep(5)
            continue

        walletStash = current_bal

        # Check if balance changed
        balance_changed = (
            walletStash == round((last_observed_balance + previousWagerAmount), 8) or 
            walletStash == round((last_observed_balance - previousWagerAmount), 8) or
            walletStash != last_observed_balance
        )

        if walletStash > 0 and balance_changed:
            last_balance_change_time = current_time
            last_observed_balance = walletStash
            last_activity_timestamp = current_time

        elapsed_stagnation = current_time - last_balance_change_time

        if elapsed_stagnation >= watchdog_threshold or walletStash <= 0:
            print(f"[Watchdog] Balance check stalled or depleted. Waiting/re-syncing...", flush=True)
            time.sleep(5)
            last_balance_change_time = time.time()
            continue

        if walletStash >= round(startingPocketChange * 24, 8):
            profit = round(walletStash - startingPocketChange, 8)
            print(f"\n[Compound Milestone] Target profit reached (+{profit:.8f})!", flush=True)
            if os.path.exists(STATE_FILE):
                try:
                    os.remove(STATE_FILE)
                except Exception:
                    pass
            print("[System] Resetting baseline with new balance and continuing...", flush=True)
            startingPocketChange = walletStosh

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

            # WolfBet API place bet payload specification
            bet_payload = {
                "currency": currency_symbol.lower(),
                "game": "dice",
                "amount": f"{computedNextBet:.8f}",
                "rule": "over",          # or "under"
                "multiplier": "1.98",    # Corresponds to ~49.5% win chance
                "bet_value": "49.99"     # Roll target
            }

            bet_response = api_request("bet", method="POST", payload=bet_payload)
            
            if bet_response and "bet" in bet_response:
                res_data = bet_response["bet"]
                actual_profit = float(res_data.get("profit", 0.0))
                new_balance = float(bet_response.get("user_balance", {}).get("amount", walletStash))
                
                walletStash = round(new_balance, 8)
                last_observed_balance = walletStash
                last_balance_change_time = time.time()
                
                previousWagerAmount = computedNextBet
                previousWalletState = walletStash
                last_bet_timestamp = time.time()
                save_state()
            else:
                print("[Error] Failed to execute bet via API. Retrying in 3 seconds...", flush=True)
                time.sleep(3)
                continue

        time.sleep(1.0) # Control loop polling frequency

def main():
    global api_token, currency_symbol

    print("=== SnowyBot WolfBet API Edition ===")
    api_token = pwinput.pwinput(prompt="WolfBet API Token / Bearer: ", mask="*")
    currency_input = input("Currency symbol (e.g. btc, lth, doge, eth) [default: btc]: ").strip()
    if currency_input:
        currency_symbol = currency_input

    initialize_bot_state()
    run_betting_loop()

if __name__ == "__main__":
    main()
