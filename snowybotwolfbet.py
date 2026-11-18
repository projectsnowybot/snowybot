#!/usr/bin/env python3
import asyncio
from decimal import Decimal, ROUND_DOWN
import json
import os
import random
import string
import sys
import time
import aiohttp
import pwinput

STATE_FILE = "bot_state_wolfbet.json"
MASTER_STATE_FILE = "bot_master_state_wolfbet.json"
API_BASE_URL = "https://wolfbet.com/api/v1"

# Financial variables initialized safely as Decimals
trueOriginalBalance = Decimal('0.0')
startingPocketChange = Decimal('0.0')
tinyPeanutSize = Decimal('0.0')
backupPeanut = Decimal('0.0')
tenPeanuts = Decimal('0.0')
walletStash = Decimal('0.0')
bob = Decimal('0.0')
previousWalletState = Decimal('0.0')
currentWagerAmount = Decimal('0.0')
previousWagerAmount = Decimal('0.0')
checkpointJuice = Decimal('0.0')
wobbleFactor = Decimal('1.0')
safetyCheckpoint = Decimal('0.0')
safetyCheckpointtwo = Decimal('0.0')
last_observed = Decimal('0.0')
beat = 0
forker = Decimal('0.0')

last_observed_balance = Decimal('0.0')
last_balance_change_time = time.time()
watchdog_threshold = 10.0

api_token = ""
currency_symbol = "usdt"
active_client_seed = ""
auto_rotate_interval = 0
total_bets_placed = 0

def load_state():
    global walletStash, currentWagerAmount, bob, previousWagerAmount, last_observed, forker, checkpointJuice, wobbleFactor, safetyCheckpoint, safetyCheckpointtwo, tinyPeanutSize, backupPeanut, tenPeanuts, startingPocketChange, previousWalletState
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                walletStash = Decimal(str(data.get("walletStash", walletStash)))
                forker = Decimal(str(data.get("forker", forker)))
                bob = Decimal(str(data.get("bob", bob)))
                startingPocketChange = Decimal(str(data.get("startingPocketChange", startingPocketChange)))
                tinyPeanutSize = Decimal(str(data.get("tinyPeanutSize", tinyPeanutSize)))
                backupPeanut = Decimal(str(data.get("backupPeanut", backupPeanut)))
                tenPeanuts = Decimal(str(data.get("tenPeanuts", tenPeanuts)))
                previousWalletState = Decimal(str(data.get("previousWalletState", previousWalletState)))
                currentWagerAmount = Decimal(str(data.get("currentWagerAmount", currentWagerAmount)))
                previousWagerAmount = Decimal(str(data.get("previousWagerAmount", previousWagerAmount)))
                checkpointJuice = Decimal(str(data.get("checkpointJuice", checkpointJuice)))
                wobbleFactor = Decimal(str(data.get("wobbleFactor", wobbleFactor)))
                safetyCheckpoint = Decimal(str(data.get("safetyCheckpoint", safetyCheckpoint)))
                safetyCheckpointtwo = Decimal(str(data.get("safetyCheckpointtwo", safetyCheckpointtwo)))
                last_observed = Decimal(str(data.get("last_observed", last_observed)))
        except Exception as e:
            pass

def save_state():
    bot_state = {
        "walletStash": str(walletStash),
        "startingPocketChange": str(startingPocketChange),
        "last_observed": str(last_observed),
        "bob": str(bob),
        "tinyPeanutSize": str(tinyPeanutSize),
        "backupPeanut": str(backupPeanut),
        "tenPeanuts": str(tenPeanuts),
        "previousWalletState": str(previousWalletState),
        "currentWagerAmount": str(currentWagerAmount),
        "previousWagerAmount": str(previousWagerAmount),
        "checkpointJuice": str(checkpointJuice),
        "wobbleFactor": str(wobbleFactor),
        "safetyCheckpoint": str(safetyCheckpoint),
        "safetyCheckpointtwo": str(safetyCheckpointtwo),
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
    master_state = {"trueOriginalBalance": str(balance)}
    try:
        with open(MASTER_STATE_FILE, "w") as f:
            json.dump(master_state, f)
    except Exception as e:
        print(f"[Error] Failed to save master state file: {e}", flush=True)

def generate_random_seed(length=16):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

async def api_request_async(session, endpoint, method="GET", payload=None, max_retries=3):
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    url = f"{API_BASE_URL}/{endpoint}"
    backoff_factor = 0.5

    for attempt in range(max_retries):
        try:
            if method == "GET":
                async with session.get(url, headers=headers, timeout=10) as response:
                    text = await response.text()
                    if response.status == 200:
                        return json.loads(text) if text else {}
                    else:
                        await asyncio.sleep(backoff_factor * (2 ** attempt))
            elif method == "POST":
                async with session.post(url, headers=headers, json=payload, timeout=10) as response:
                    text = await response.text()
                    if response.status == 200:
                        return json.loads(text) if text else {}
                    else:
                        print(f"\n[API Error {response.status}] Server response: {text}", flush=True)
                        await asyncio.sleep(backoff_factor * (2 ** attempt))
        except Exception as e:
            print(f"\n[API Exception] {e}", flush=True)
            await asyncio.sleep(backoff_factor * (2 ** attempt))

    return None

async def set_client_seed_async(session, seed_string):
    if not seed_string:
        return False
    payload = {"client_seed": seed_string}
    response = await api_request_async(session, "user/seed/refresh", method="POST", payload=payload)
    if response is not None:
        print(f"\n[Provably Fair] Client seed successfully updated to: {seed_string}", flush=True)
        return True
    else:
        print(f"\n[Warning] Failed to update client seed.", flush=True)
        return False

async def console_seed_input_listener(session):
    global active_client_seed
    loop = asyncio.get_running_loop()
    print("\n[Console] Press [Enter] anytime to manually generate and rotate a random client seed.", flush=True)
    while True:
        try:
            await loop.run_in_executor(None, input, "")
            new_seed = generate_random_seed()
            success = await set_client_seed_async(session, new_seed)
            if success:
                active_client_seed = new_seed
        except Exception as e:
            await asyncio.sleep(1.0)

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
                    return Decimal(str(item.get("amount", "0.0")))
                except (ValueError, TypeError):
                    pass
                
    return None
    
async def calculate_next_progression_step(session, incoming_wager):
    global walletStash, currentWagerAmount, bob, wobbleFactor, forker, checkpointJuice, safetyCheckpoint, tinyPeanutSize, backupPeanut, safetyCheckpointtwo, base_wager, last_observed, beat
    
    currentWagerAmount = incoming_wager
    checkpointJuice = Decimal(str(checkpointJuice))
    forker = Decimal(str(forker))
    safetyCheckpoint = Decimal(str(safetyCheckpoint))
    safetyCheckpointtwo = Decimal(str(safetyCheckpointtwo))
    base_wager = currentWagerAmount
    backupPeanut = tinyPeanutSize
    bob = Decimal(str(bob))
    
    if beat > 0:
        soulp = walletStash - last_observed
        souly = last_observed - walletStash
        tolerance = Decimal('1e-8')
        if soulp > 0:
            if (abs((soulp - currentWagerAmount)) <= tolerance) or (abs((soulp + currentWagerAmount)) <= tolerance):
                last_observed = walletStash
            else:
                bob = bob + souly
                last_observed = walletStash
        elif souly > 0:
            if (abs((soulp - currentWagerAmount)) <= tolerance) or (abs((soulp + currentWagerAmount)) <= tolerance):
                last_observed = walletStash
            else:
                print(f"[Security] External balance change detected! Halting for security.")
                save_state()
                sys.exit(1)

    if beat <= 0:
        last_observed = walletStash

    dopey = safetyCheckpoint - (tinyPeanutSize * Decimal('10'))
    frack = walletStash + bob 
    freak = frack - dopey
    if freak <= 0:
        safetyCheckpoint = walletStash + bob
        dopey = safetyCheckpoint - (tinyPeanutSize * Decimal('10'))
        frack = walletStash + bob 
        freak = frack - dopey

    ten_peanuts_val = tinyPeanutSize * Decimal('10')

    if (freak - ((currentWagerAmount * Decimal('2')) + tinyPeanutSize)) <= 0:
        currentWagerAmount = tinyPeanutSize
        forker = freak
        checkpointJuice = ((freak / ten_peanuts_val).quantize(Decimal('1'), rounding=ROUND_DOWN)) * ten_peanuts_val

    if ((freak - ((currentWagerAmount * Decimal('4')) + tinyPeanutSize)) <= 0) and (freak >= (forker + ten_peanuts_val)):
        currentWagerAmount = tinyPeanutSize
        forker = freak
        checkpointJuice = ((freak / ten_peanuts_val).quantize(Decimal('1'), rounding=ROUND_DOWN)) * ten_peanuts_val
        
    if (currentWagerAmount > tinyPeanutSize) and (freak < (checkpointJuice - (currentWagerAmount * Decimal('4.9')))):
        currentWagerAmount = currentWagerAmount * Decimal('2')
        checkpointJuice = freak

    if (((currentWagerAmount <= tinyPeanutSize) and (freak > (checkpointJuice + (currentWagerAmount * Decimal('6.9'))))) or 
        ((currentWagerAmount <= tinyPeanutSize) and (freak < (checkpointJuice - (currentWagerAmount * Decimal('2.9'))))) or 
        ((currentWagerAmount > tinyPeanutSize) and (freak > (checkpointJuice + (currentWagerAmount * Decimal('4.9')))))):
        currentWagerAmount = currentWagerAmount * Decimal('2')
        checkpointJuice = freak

    beat = beat + 1
    currentWagerAmount = currentWagerAmount.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
    return currentWagerAmount

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

    if active_client_seed:
        await set_client_seed_async(session, active_client_seed)

    master_state = load_master_state()
    if master_state and "trueOriginalBalance" in master_state:
        trueOriginalBalance = Decimal(str(master_state["trueOriginalBalance"]))
    else:
        trueOriginalBalance = current_bal
        save_master_state(trueOriginalBalance)

    savedState = load_state()

    startingPocketChange = current_bal
    walletStash = current_bal

    calculated_tiny = startingPocketChange / Decimal('1000')

    tinyPeanutSize = Decimal(str(savedState.get("tinyPeanutSize", calculated_tiny))) if savedState else calculated_tiny
    backupPeanut = Decimal(str(savedState.get("backupPeanut", tinyPeanutSize))) if savedState else tinyPeanutSize
    tenPeanuts = Decimal(str(savedState.get("tenPeanuts", tinyPeanutSize * Decimal('10')))) if savedState else tinyPeanutSize * Decimal('10')

    previousWalletState = Decimal(str(savedState.get("previousWalletState", walletStash))) if savedState else walletStash
    currentWagerAmount = Decimal(str(savedState.get("currentWagerAmount", backupPeanut))) if savedState else backupPeanut
    previousWagerAmount = Decimal(str(savedState.get("previousWagerAmount", currentWagerAmount))) if savedState else currentWagerAmount

    default_chk = walletStash
    chk_calc = ((default_chk / (tinyPeanutSize * Decimal('10'))).quantize(Decimal('1'), rounding=ROUND_DOWN)) * (tinyPeanutSize * Decimal('10'))
    checkpointJuice = Decimal(str(savedState.get("checkpointJuice", chk_calc))) if savedState else chk_calc
    wobbleFactor = Decimal(str(savedState.get("wobbleFactor", "1.0"))) if savedState else Decimal('1.0')
    safetyCheckpoint = Decimal(str(savedState.get("safetyCheckpoint", chk_calc))) if savedState else chk_calc
    
    global safetyCheckpointtwo
    safetyCheckpointtwo = Decimal(str(savedState.get("safetyCheckpointtwo", "999999999999999999999999999999999999.0"))) if savedState else Decimal('999999999999999999999999999999999999.0')

    last_observed_balance = current_bal
    global forker
    forker = current_bal
    last_observed = Decimal(str(savedState.get("last_observed", current_bal))) if savedState else current_bal
    global bob
    bob = Decimal(str(savedState.get("bob", "0.0"))) if savedState else Decimal('0.0')
    last_balance_change_time = time.time()

    total_profit_init = walletStash - trueOriginalBalance
    print(f"[System] Connected to WolfBet! Balance: {walletStash:.8f} {currency_symbol.upper()} | Master Original: {trueOriginalBalance:.8f} | Total Profit: {total_profit_init:+.8f}", flush=True)

async def watchdog_loop(session):
    global last_balance_change_time, walletStash, last_observed_balance
    while True:
        await asyncio.sleep(2.0)
        if (time.time() - last_balance_change_time) > watchdog_threshold:
            load_state()
            bal_check = await get_user_balance_async(session)
            if bal_check is not None:
                if bal_check != walletStash:
                    walletStash = bal_check
                    last_observed_balance = walletStash
                    last_balance_change_time = time.time()
                    print(f"[Watchdog] Balance updated: {walletStash:.8f}", flush=True)
                else:
                    last_balance_change_time = time.time()

async def run_betting_loop():
    global walletStash, last_observed_balance, previousWagerAmount, trueOriginalBalance, last_balance_change_time, total_bets_placed
    
    connector = aiohttp.TCPConnector(limit=1, limit_per_host=1)
    async with aiohttp.ClientSession(connector=connector) as session:
        await initialize_bot_state_async(session)
        
        asyncio.create_task(watchdog_loop(session))
        asyncio.create_task(console_seed_input_listener(session))
        
        print("[System] Entering safe 100ms polling balance check loop...", flush=True)

        computedNextBet = await calculate_next_progression_step(session, previousWagerAmount)
        total_profit = walletStash - trueOriginalBalance
        log_bet_info(computedNextBet, walletStash, total_profit)

        bet_payload = {
            "currency": currency_symbol.lower(),
            "game": "dice",  # Fixed game configuration slug
            "amount": f"{computedNextBet:.8f}",
            "rule": "over",
            "multiplier": "2",
            "bet_value": "50.49"
        }
        previousWagerAmount = computedNextBet
        bet_response = await api_request_async(session, "bet/place", method="POST", payload=bet_payload)
        total_bets_placed += 1

        if bet_response and "bet" in bet_response:
            user_bal_obj = bet_response.get("user_balance")
            if isinstance(user_bal_obj, dict):
                for k in ["amount", "balance", "value"]:
                    if k in user_bal_obj:
                        try:
                            walletStash = Decimal(str(user_bal_obj[k]))
                            break
                        except (ValueError, TypeError):
                            pass
            elif isinstance(user_bal_obj, (int, float, str)):
                walletStash = Decimal(str(user_bal_obj))
            elif "balance" in bet_response:
                try:
                    walletStash = Decimal(str(bet_response["balance"]))
                except (ValueError, TypeError):
                    pass
            last_observed_balance = walletStash
            last_balance_change_time = time.time()
            save_state()

        while True:
            if walletStash >= Decimal('144.0'):
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
                walletStash = bal_check
                last_observed_balance = walletStash
                last_balance_change_time = time.time()

                if auto_rotate_interval > 0 and total_bets_placed > 0 and total_bets_placed % auto_rotate_interval == 0:
                    rand_seed = generate_random_seed()
                    print(f"\n[Auto-Rotate] Reached {total_bets_placed} bets. Generating new random seed...", flush=True)
                    await set_client_seed_async(session, rand_seed)

                computedNextBet = await calculate_next_progression_step(session, previousWagerAmount)
                total_profit = walletStash - trueOriginalBalance
                log_bet_info(computedNextBet, walletStash, total_profit)

                bet_payload = {
                    "currency": currency_symbol.lower(),
                    "game": "dice",  # Fixed game configuration slug
                    "amount": f"{computedNextBet:.8f}",
                    "rule": "over",
                    "multiplier": "2",
                    "bet_value": "50.49"
                }

                previousWagerAmount = computedNextBet
                bet_response = await api_request_async(session, "bet/place", method="POST", payload=bet_payload)
                total_bets_placed += 1
                
                if bet_response and "bet" in bet_response:
                    user_bal_obj = bet_response.get("user_balance")
                    if isinstance(user_bal_obj, dict):
                        for k in ["amount", "balance", "value"]:
                            if k in user_bal_obj:
                                try:
                                    walletStash = Decimal(str(user_bal_obj[k]))
                                    break
                                except (ValueError, TypeError):
                                    pass
                    elif isinstance(user_bal_obj, (int, float, str)):
                        walletStash = Decimal(str(user_bal_obj))
                    elif "balance" in bet_response:
                        try:
                            walletStash = Decimal(str(bet_response["balance"]))
                        except (ValueError, TypeError):
                            pass
                    last_observed_balance = walletStash
                    save_state()
            else:
                await asyncio.sleep(0.1)

def main():
    global api_token, currency_symbol, active_client_seed, auto_rotate_interval

    print("=== SnowyBot WolfBet API Edition (Game Config Fixed) ===")
    api_token = pwinput.pwinput(prompt="WolfBet API Token / Bearer: ", mask="*")
    
    currency_input = input("Currency symbol [default: usdt]: ").strip().lower()
    if currency_input:
        currency_symbol = currency_input

    try:
        interval_input = input("Automatically rotate random seed every X bets (enter 0 to disable): ").strip()
        if interval_input:
            auto_rotate_interval = int(interval_input)
    except ValueError:
        auto_rotate_interval = 0

    seed_input = input("Initial Client Seed (leave blank to generate a random one): ").strip()
    if seed_input:
        active_client_seed = seed_input
    else:
        active_client_seed = generate_random_seed()
        print(f"[Provably Fair] Generated initial random client seed: {active_client_seed}", flush=True)

    try:
        asyncio.run(run_betting_loop())
    except KeyboardInterrupt:
        print("\n[System] Bot stopped by user. Saving final state...", flush=True)
        save_state()

if __name__ == "__main__":
    main()