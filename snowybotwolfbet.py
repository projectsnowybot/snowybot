#!/usr/bin/env python3
asyncio_import_ok = True
import asyncio
import json
import math
import os
import sys
import time
import aiohttp
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

last_observed_balance = 0.0
last_balance_change_time = time.time()
watchdog_threshold = 10.0

api_token = ""
currency_symbol = "ltc"

def load_state():
    global walletStash, currentWagerAmount, previousWagerAmount, checkpointJuice, wobbleFactor, safetyCheckpoint, safetyCheckpointtwo, tinyPeanutSize, backupPeanut, tenPeanuts, startingPocketChange, previousWalletState
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                walletStash = float(data.get("walletStash", walletStash))
                startingPocketChange = float(data.get("startingPocketChange", startingPocketChange))
                tinyPeanutSize = float(data.get("tinyPeanutSize", tinyPeanutSize))
                backupPeanut = float(data.get("backupPeanut", backupPeanut))
                tenPeanuts = float(data.get("tenPeanuts", tenPeanuts))
                previousWalletState = float(data.get("previousWalletState", previousWalletState))
                currentWagerAmount = float(data.get("currentWagerAmount", currentWagerAmount))
                previousWagerAmount = float(data.get("previousWagerAmount", previousWagerAmount))
                checkpointJuice = float(data.get("checkpointJuice", checkpointJuice))
                wobbleFactor = float(data.get("wobbleFactor", wobbleFactor))
                safetyCheckpoint = float(data.get("safetyCheckpoint", safetyCheckpoint))
                safetyCheckpointtwo = float(data.get("safetyCheckpointtwo", safetyCheckpointtwo))
                print(f"[Watchdog] State file reloaded successfully from disk.", flush=True)
        except Exception as e:
            print(f"[Error] Failed to load state file: {e}", flush=True)

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

async def api_request_async(session, endpoint, method="GET", payload=None, max_retries=3):
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    url = f"{API_BASE_URL}/{endpoint}"
    backoff_factor = 0.05

    for attempt in range(max_retries):
        try:
            if method == "GET":
                async with session.get(url, headers=headers, timeout=10) as response:
                    text = await response.text()
                    if response.status == 200:
                        return json.loads(text)
                    elif response.status == 429:
                        await asyncio.sleep(backoff_factor * (2 ** attempt))
                    else:
                        await asyncio.sleep(backoff_factor * (2 ** attempt))
            elif method == "POST":
                async with session.post(url, headers=headers, json=payload, timeout=10) as response:
                    text = await response.text()
                    if response.status == 200:
                        return json.loads(text)
                    elif response.status == 429:
                        await asyncio.sleep(backoff_factor * (2 ** attempt))
                    else:
                        await asyncio.sleep(backoff_factor * (2 ** attempt))
        except Exception as e:
            await asyncio.sleep(backoff_factor * (2 ** attempt))

    return None

async def get_user_balance_async(session):
    data = await api_request_async(session, "user/balances", method="GET")
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
                
    return None

async def calculate_next_progression_step(session, incoming_wager):
    global walletStash, currentWagerAmount, wobbleFactor, checkpointJuice, safetyCheckpoint, tinyPeanutSize, backupPeanut, safetyCheckpointtwo, base_wager

    currentWagerAmount = round(float(incoming_wager), 8)
    checkpointJuice = float(checkpointJuice)
    safetyCheckpoint = float(safetyCheckpoint)
    safetyCheckpointtwo = float(safetyCheckpointtwo)
    base_wager = currentWagerAmount
    backupPeanut = tinyPeanutSize

    if walletStash >= round(safetyCheckpoint + ((tinyPeanutSize * 10) * wobbleFactor), 8):
        currentWagerAmount = round(float(tinyPeanutSize), 8)
        wobbleFactor = 1.0
        checkpointJuice = round(float((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)), 8)
        safetyCheckpoint = round(float((math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)), 8)
        return currentWagerAmount
    
    if base_wager > backupPeanut:
        if walletStash > round(checkpointJuice + (base_wager * 4.9), 8):
            currentWagerAmount = round(float(base_wager * 2.0), 8)
            checkpointJuice = round(float(walletStash), 8)
        elif walletStash < round(checkpointJuice - (base_wager * 4.9), 8):
            currentWagerAmount = round(float(base_wager * 2.0), 8)
            wobbleFactor = 0.0
            checkpointJuice = round(float(walletStash), 8)
        else:
            currentWagerAmount = base_wager
            
    if base_wager <= backupPeanut:
        if walletStash > round(checkpointJuice + round(base_wager * 6.9, 8), 8):
            currentWagerAmount = round(float(base_wager * 2.0), 8)
            checkpointJuice = round(float(walletStash), 8)
        elif walletStash < round(checkpointJuice - round(base_wager * 2.9, 8), 8):
            currentWagerAmount = round(float(base_wager * 2.0), 8)
            checkpointJuice = round(float(walletStash), 8)
        else:
            currentWagerAmount = base_wager

    return round(float(currentWagerAmount), 8)

def log_bet_info(bet_amount, current_balance, total_profit):
    print(f"Bet: {bet_amount:.8f} | Balance: {current_balance:.8f} | Total Profit: {total_profit:+.8f}", flush=True)

async def initialize_bot_state_async(session):
    global trueOriginalBalance, startingPocketChange, tinyPeanutSize, backupPeanut, tenPeanuts
    global walletStash, previousWalletState, currentWagerAmount, previousWagerAmount
    global checkpointJuice, wobbleFactor, safetyCheckpoint, last_observed_balance, last_balance_change_time

    current_bal = await get_user_balance_async(session)
    if current_bal is None:
        print(f"[System] Failed to fetch initial balance for '{currency_symbol.upper()}' from WolfBet API.", flush=True)
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

    tinyPeanutSize = float(savedState.get("tinyPeanutSize", calculated_tiny)) if savedState else calculated_tiny
    backupPeanut = float(savedState.get("backupPeanut", tinyPeanutSize)) if savedState else tinyPeanutSize
    tenPeanuts = float(savedState.get("tenPeanuts", tinyPeanutSize * 10)) if savedState else tinyPeanutSize * 10

    previousWalletState = float(savedState.get("previousWalletState", walletStash)) if savedState else walletStash
    currentWagerAmount = float(savedState.get("currentWagerAmount", backupPeanut)) if savedState else backupPeanut
    previousWagerAmount = float(savedState.get("previousWagerAmount", currentWagerAmount)) if savedState else currentWagerAmount

    default_chk = walletStash
    checkpointJuice = float(savedState.get("checkpointJuice", float((math.floor(default_chk / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)))) if savedState else float((math.floor(default_chk / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10))
    wobbleFactor = float(savedState.get("wobbleFactor", 1.0)) if savedState else 1.0
    safetyCheckpoint = float(savedState.get("safetyCheckpoint", float(((math.floor(default_chk / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10))))) if savedState else float(((math.floor(default_chk / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)))
    global safetyCheckpointtwo
    safetyCheckpointtwo = float(savedState.get("safetyCheckpointtwo", float((math.floor(default_chk / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10)))) if savedState else float((math.floor(default_chk / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10))

    last_observed_balance = current_bal
    last_balance_change_time = time.time()

    total_profit_init = walletStash - trueOriginalBalance
    print(f"[System] Connected to WolfBet! Balance: {walletStash:.8f} {currency_symbol.upper()} | Master Original: {trueOriginalBalance:.8f} | Total Profit: {total_profit_init:+.8f}", flush=True)

async def watchdog_loop(session):
    global last_balance_change_time, walletStash, last_observed_balance
    while True:
        await asyncio.sleep(1.0)
        if (time.time() - last_balance_change_time) > watchdog_threshold:
            print(f"[Watchdog] Balance has not changed for {watchdog_threshold}s. Reloading state files and verifying balance...", flush=True)
            load_state()
            bal_check = await get_user_balance_async(session)
            if bal_check is not None:
                if bal_check != walletStash:
                    walletStash = bal_check
                    last_observed_balance = walletStash
                    last_balance_change_time = time.time()
                    print(f"[Watchdog] Balance updated during check: {walletStash:.8f}", flush=True)
                else:
                    print(f"[Watchdog] Balance verified unchanged at {walletStash:.8f}. Resetting watchdog timer.", flush=True)
                    last_balance_change_time = time.time()

async def run_betting_loop():
    connector = aiohttp.TCPConnector(limit=50, limit_per_host=50)
    async with aiohttp.ClientSession(connector=connector) as session:
        await initialize_bot_state_async(session)
        asyncio.create_task(watchdog_loop(session))
        
        global walletStash, last_observed_balance, previousWagerAmount, trueOriginalBalance, last_balance_change_time
        
        print("[System] Entering 1ms micro-sleep balance check loop...", flush=True)

        # Place initial first bet
        computedNextBet = await calculate_next_progression_step(session, previousWagerAmount)
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
        previousWagerAmount = computedNextBet
        bet_response = await api_request_async(session, "bet/place/", method="POST", payload=bet_payload)
        if bet_response and "bet" in bet_response:
            user_bal_obj = bet_response.get("user_balance")
            if isinstance(user_bal_obj, dict):
                for k in ["amount", "balance", "value"]:
                    if k in user_bal_obj:
                        try:
                            walletStash = float(user_bal_obj[k])
                            break
                        except (ValueError, TypeError):
                            pass
            elif isinstance(user_bal_obj, (int, float)):
                walletStash = float(user_bal_obj)
            elif "balance" in bet_response:
                try:
                    walletStash = float(bet_response["balance"])
                except (ValueError, TypeError):
                    pass
            last_observed_balance = walletStash
            last_balance_change_time = time.time()
            save_state()

        while True:
            if walletStash >= 14.4:
                total_profit = walletStash - trueOriginalBalance
                print(f"\n[System] TARGET REACHED ({walletStash:.8f}). Total Cumulative Profit: {total_profit:+.8f}. Halting.", flush=True)
                for f_path in [STATE_FILE, MASTER_STATE_FILE]:
                    if os.path.exists(f_path):
                        try:
                            os.remove(f_path)
                        except Exception:
                            pass
                sys.exit(0)

            current_balance = last_observed_balance
            bal_check = await get_user_balance_async(session)
            
            if bal_check is not None and bal_check != current_balance:
                # Balance changed! Update state and execute logic + next bet immediately
                walletStash = bal_check
                last_observed_balance = walletStash
                last_balance_change_time = time.time()

                computedNextBet = await calculate_next_progression_step(session, previousWagerAmount)
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

                previousWagerAmount = computedNextBet
                bet_response = await api_request_async(session, "bet/place/", method="POST", payload=bet_payload)
                
                if bet_response and "bet" in bet_response:
                    user_bal_obj = bet_response.get("user_balance")
                    if isinstance(user_bal_obj, dict):
                        for k in ["amount", "balance", "value"]:
                            if k in user_bal_obj:
                                try:
                                    walletStash = float(user_bal_obj[k])
                                    break
                                except (ValueError, TypeError):
                                    pass
                    elif isinstance(user_bal_obj, (int, float)):
                        walletStash = float(user_bal_obj)
                    elif "balance" in bet_response:
                        try:
                            walletStash = float(bet_response["balance"])
                        except (ValueError, TypeError):
                            pass
                    last_observed_balance = walletStash
                    save_state()
            else:
                # 1 millisecond micro-sleep when balance has not changed yet
                await asyncio.sleep(0.001)

def main():
    global api_token, currency_symbol

    print("=== SnowyBot WolfBet API Edition (1ms Balance-Check Loop) ===")
    api_token = pwinput.pwinput(prompt="WolfBet API Token / Bearer: ", mask="*")
    
    currency_input = input("Currency symbol [default: ltc]: ").strip().lower()
    if currency_input:
        currency_symbol = currency_input

    try:
        asyncio.run(run_betting_loop())
    except KeyboardInterrupt:
        print("\n[System] Bot stopped by user. Saving final state...", flush=True)
        save_state()

if __name__ == "__main__":
    main()
