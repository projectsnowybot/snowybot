#!/usr/bin/env python3
import asyncio
import json
import math
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

# Financial variables initialized safely as floats
trueOriginalBalance = float(0.0)
startingPocketChange = float(0.0)
tinyPeanutSize = float(0.0)
backupPeanut = float(0.0)
tenPeanuts = float(0.0)
walletStash = float(0.0)
bob = float(0.0)
previousWalletState = float(0.0)
currentWagerAmount = float(0.0)
previousWagerAmount = float(0.0)
checkpointJuice = float(0.0)
wobbleFactor = float(1.0)
safetyCheckpoint = float(0.0)
safetyCheckpointtwo = float(0.0)
last_observed = float(0.0)
beat = 0
forker = float(0.0)
targetBalance = float(144.0)

last_observed_balance = float(0.0)
last_balance_change_time = float(time.time())
watchdog_threshold = float(10.0)

api_token = ""
currency_symbol = "usdt"
active_client_seed = ""
auto_rotate_interval = 0
total_bets_placed = 0


def safe_float(value, default=0.0) -> float:
    default_f = float(default)
    if value is None:
        return default_f
    try:
        parsed = float(value)
        if math.isnan(parsed) or math.isinf(parsed):
            return default_f
        return float(parsed)
    except (ValueError, TypeError):
        return default_f


def floor_to_step(value: float, step: float) -> float:
    val_f = safe_float(value, 0.0)
    step_f = safe_float(step, 0.0)
    if step_f <= float(0.0):
        return float(val_f)
    return float(round(float(math.floor(val_f / step_f)) * step_f, 8))


def load_state():
    global walletStash, currentWagerAmount, bob, previousWagerAmount, last_observed, forker
    global checkpointJuice, wobbleFactor, safetyCheckpoint, safetyCheckpointtwo
    global tinyPeanutSize, backupPeanut, tenPeanuts, startingPocketChange, previousWalletState

    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                walletStash = safe_float(data.get("walletStash", walletStash), walletStash)
                forker = safe_float(data.get("forker", forker), forker)
                bob = safe_float(data.get("bob", bob), bob)
                startingPocketChange = safe_float(data.get("startingPocketChange", startingPocketChange), startingPocketChange)
                tinyPeanutSize = safe_float(data.get("tinyPeanutSize", tinyPeanutSize), tinyPeanutSize)
                backupPeanut = safe_float(data.get("backupPeanut", backupPeanut), backupPeanut)
                tenPeanuts = safe_float(data.get("tenPeanuts", tenPeanuts), tenPeanuts)
                previousWalletState = safe_float(data.get("previousWalletState", previousWalletState), previousWalletState)
                currentWagerAmount = safe_float(data.get("currentWagerAmount", currentWagerAmount), currentWagerAmount)
                previousWagerAmount = safe_float(data.get("previousWagerAmount", previousWagerAmount), previousWagerAmount)
                checkpointJuice = safe_float(data.get("checkpointJuice", checkpointJuice), checkpointJuice)
                wobbleFactor = safe_float(data.get("wobbleFactor", wobbleFactor), wobbleFactor)
                safetyCheckpoint = safe_float(data.get("safetyCheckpoint", safetyCheckpoint), safetyCheckpoint)
                safetyCheckpointtwo = safe_float(data.get("safetyCheckpointtwo", safetyCheckpointtwo), safetyCheckpointtwo)
                last_observed = safe_float(data.get("last_observed", last_observed), last_observed)
        except Exception:
            pass


def save_state():
    bot_state = {
        "walletStash": float(round(safe_float(walletStash), 8)),
        "startingPocketChange": float(round(safe_float(startingPocketChange), 8)),
        "last_observed": float(round(safe_float(last_observed), 8)),
        "forker": float(round(safe_float(forker), 8)),
        "bob": float(round(safe_float(bob), 8)),
        "tinyPeanutSize": float(round(safe_float(tinyPeanutSize), 8)),
        "backupPeanut": float(round(safe_float(backupPeanut), 8)),
        "tenPeanuts": float(round(safe_float(tenPeanuts), 8)),
        "previousWalletState": float(round(safe_float(previousWalletState), 8)),
        "currentWagerAmount": float(round(safe_float(currentWagerAmount), 8)),
        "previousWagerAmount": float(round(safe_float(previousWagerAmount), 8)),
        "checkpointJuice": float(round(safe_float(checkpointJuice), 8)),
        "wobbleFactor": safe_float(wobbleFactor, 1.0),
        "safetyCheckpoint": float(round(safe_float(safetyCheckpoint), 8)),
        "safetyCheckpointtwo": float(round(safe_float(safetyCheckpointtwo), 8)),
        "last_seen_timestamp": float(time.time()),
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
    master_state = {"trueOriginalBalance": float(round(safe_float(balance), 8))}
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
    backoff_factor = float(0.5)

    for attempt in range(max_retries):
        try:
            if method == "GET":
                async with session.get(url, headers=headers, timeout=10) as response:
                    text = await response.text()
                    if response.status == 200:
                        return json.loads(text) if text else {}
                    else:
                        await asyncio.sleep(float(backoff_factor * (2.0 ** float(attempt))))
            elif method == "POST":
                async with session.post(url, headers=headers, json=payload, timeout=10) as response:
                    text = await response.text()
                    if response.status == 200:
                        return json.loads(text) if text else {}
                    else:
                        print(f"\n[API Error {response.status}] Server response: {text}", flush=True)
                        await asyncio.sleep(float(backoff_factor * (2.0 ** float(attempt))))
        except Exception as e:
            print(f"\n[API Exception] {e}", flush=True)
            await asyncio.sleep(float(backoff_factor * (2.0 ** float(attempt))))

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
        print("\n[Warning] Failed to update client seed.", flush=True)
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
        except Exception:
            await asyncio.sleep(float(1.0))


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
            for _, v in data.items():
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
                    return float(item.get("amount", float(0.0)))
                except (ValueError, TypeError):
                    pass

    return None


def extract_balance_from_bet_response(bet_response):
    if not isinstance(bet_response, dict) or "bet" not in bet_response:
        return None

    user_bal_obj = bet_response.get("user_balance")
    if isinstance(user_bal_obj, dict):
        for k in ["amount", "balance", "value"]:
            if k in user_bal_obj:
                try:
                    return float(user_bal_obj[k])
                except (ValueError, TypeError):
                    pass
    elif isinstance(user_bal_obj, (int, float, str)):
        try:
            return float(user_bal_obj)
        except (ValueError, TypeError):
            pass
    elif "balance" in bet_response:
        try:
            return float(bet_response["balance"])
        except (ValueError, TypeError):
            pass

    return None


async def calculate_next_progression_step(session, incoming_wager):
    global walletStash, currentWagerAmount, bob, wobbleFactor, forker
    global checkpointJuice, safetyCheckpoint, tinyPeanutSize, backupPeanut
    global safetyCheckpointtwo, last_observed, beat

    currentWagerAmount = float(incoming_wager)
    checkpointJuice = float(checkpointJuice)
    forker = float(forker)
    safetyCheckpoint = float(safetyCheckpoint)
    safetyCheckpointtwo = float(safetyCheckpointtwo)
    backupPeanut = float(tinyPeanutSize)
    wobbleFactor = float(wobbleFactor)
    bob = float(bob)
    walletStash = float(walletStash)
    last_observed = float(last_observed)

    if beat > 0:
        soulp = float(walletStash - last_observed)
        souly = float(last_observed - walletStash)
        matches_wager = (
            math.isclose(float(soulp - currentWagerAmount), float(0.0), abs_tol=float(1e-8))
            or math.isclose(float(soulp + currentWagerAmount), float(0.0), abs_tol=float(1e-8))
        )
        if soulp > float(0.0):
            if matches_wager:
                last_observed = float(walletStash)
            else:
                print(f"[Security] External balance change detected! Delta: {soulp:+.8f} | Expected Wager: {currentWagerAmount:.8f}. Using original balance.", flush=True)
                bob = float(bob + souly)
                last_observed = float(walletStash)
        elif souly > float(0.0):
            if matches_wager:
                last_observed = float(walletStash)
            else:
                print(f"[Security] External balance change detected! Delta: {soulp:+.8f} | Expected Wager: {currentWagerAmount:.8f}. Halting.", flush=True)
                save_state()
                sys.exit(1)

    if beat <= 0:
        last_observed = float(walletStash)

    ten_peanuts_val = float(tinyPeanutSize * float(10.0))
    forty_peanuts = float(tinyPeanutSize * float(40.0))
    frack = float(walletStash + bob)

    if (frack<(checkpointJuice-(tinyPeanutSize*23.9))):
        currentWagerAmount = float(tinyPeanutSize)
        checkpointJuice = float(floor_to_step(frack, ten_peanuts_val))

    if ((frack>(checkpointJuice+(tinyPeanutSize*31.9))) and (frack >= (forker + forty_peanuts))):
        currentWagerAmount = float(tinyPeanutSize)
        forker = float(frack)
        checkpointJuice = float(floor_to_step(frack, ten_peanuts_val))

    if (
        ((currentWagerAmount <= tinyPeanutSize) and (frack > float(checkpointJuice + (currentWagerAmount * float(6.9)))))
        or ((currentWagerAmount <= tinyPeanutSize) and (frack < float(checkpointJuice - (currentWagerAmount * float(2.9)))))
        or ((currentWagerAmount > tinyPeanutSize) and (frack > float(checkpointJuice + (currentWagerAmount * float(4.9)))))
        or ((currentWagerAmount > tinyPeanutSize) and (frack < float(checkpointJuice - (currentWagerAmount * float(4.9)))))
    ):
        currentWagerAmount = float(currentWagerAmount * float(2.0))
        checkpointJuice = float(frack)

    beat += 1
    currentWagerAmount = float(math.floor(float(currentWagerAmount * float(1e8))) / float(1e8))
    return float(currentWagerAmount)


def log_bet_info(bet_amount, current_balance, total_profit):
    print(f"Bet: {float(bet_amount):.8f} | Balance: {float(current_balance):.8f} | Total Profit: {float(total_profit):+.8f}", flush=True)


async def initialize_bot_state_async(session):
    global trueOriginalBalance, startingPocketChange, tinyPeanutSize, backupPeanut, tenPeanuts
    global walletStash, previousWalletState, currentWagerAmount, previousWagerAmount
    global checkpointJuice, wobbleFactor, safetyCheckpoint, safetyCheckpointtwo
    global forker, last_observed, bob, last_observed_balance, last_balance_change_time

    current_bal = await get_user_balance_async(session)
    if current_bal is None:
        print(f"[System] Failed to fetch initial balance for '{currency_symbol.upper()}' from WolfBet API.", flush=True)
        sys.exit(1)

    current_bal_f = float(current_bal)

    if active_client_seed:
        await set_client_seed_async(session, active_client_seed)

    master_state = load_master_state()
    if master_state and "trueOriginalBalance" in master_state:
        trueOriginalBalance = float(master_state["trueOriginalBalance"])
    else:
        trueOriginalBalance = float(current_bal_f)
        save_master_state(trueOriginalBalance)

    savedState = load_state()

    startingPocketChange = float(current_bal_f)
    walletStash = float(current_bal_f)

    calculated_tiny = float(startingPocketChange / float(1000.0))
    tinyPeanutSize = float(savedState.get("tinyPeanutSize", calculated_tiny)) if savedState else float(calculated_tiny)
    backupPeanut = float(savedState.get("backupPeanut", tinyPeanutSize)) if savedState else float(tinyPeanutSize)
    tenPeanuts = float(savedState.get("tenPeanuts", float(tinyPeanutSize * float(10.0)))) if savedState else float(tinyPeanutSize * float(10.0))

    previousWalletState = float(savedState.get("previousWalletState", walletStash)) if savedState else float(walletStash)
    currentWagerAmount = float(savedState.get("currentWagerAmount", backupPeanut)) if savedState else float(backupPeanut)
    previousWagerAmount = float(savedState.get("previousWagerAmount", currentWagerAmount)) if savedState else float(currentWagerAmount)

    default_chk = float(walletStash)
    chk_calc = float(floor_to_step(default_chk, float(tinyPeanutSize * float(10.0))))
    checkpointJuice = float(savedState.get("checkpointJuice", chk_calc)) if savedState else float(chk_calc)
    wobbleFactor = float(savedState.get("wobbleFactor", float(1.0))) if savedState else float(1.0)
    safetyCheckpoint = float(savedState.get("safetyCheckpoint", chk_calc)) if savedState else float(chk_calc)
    safetyCheckpointtwo = float(savedState.get("safetyCheckpointtwo", float(1e36))) if savedState else float(1e36)

    last_observed_balance = float(current_bal_f)
    forker = float(savedState.get("forker", current_bal_f)) if savedState else float(current_bal_f)
    last_observed = float(savedState.get("last_observed", current_bal_f)) if savedState else float(current_bal_f)
    bob = float(savedState.get("bob", float(0.0))) if savedState else float(0.0)
    last_balance_change_time = float(time.time())

    total_profit_init = float(walletStash - trueOriginalBalance)
    print(f"[System] Connected to WolfBet! Balance: {walletStash:.8f} {currency_symbol.upper()} | Master Original: {trueOriginalBalance:.8f} | Total Profit: {total_profit_init:+.8f}", flush=True)


async def watchdog_loop(session):
    global last_balance_change_time, walletStash, last_observed_balance
    while True:
        await asyncio.sleep(float(2.0))
        if float(time.time() - last_balance_change_time) > float(watchdog_threshold):
            load_state()
            bal_check = await get_user_balance_async(session)
            if bal_check is not None:
                bal_float = float(bal_check)
                if not math.isclose(bal_float, float(walletStash), abs_tol=float(1e-9)):
                    walletStash = float(bal_float)
                    last_observed_balance = float(walletStash)
                    last_balance_change_time = float(time.time())
                    print(f"[Watchdog] Balance updated: {walletStash:.8f}", flush=True)
                else:
                    last_balance_change_time = float(time.time())


async def run_betting_loop():
    global walletStash, last_observed_balance, previousWagerAmount, trueOriginalBalance, last_balance_change_time, total_bets_placed

    connector = aiohttp.TCPConnector(limit=1, limit_per_host=1)
    async with aiohttp.ClientSession(connector=connector) as session:
        await initialize_bot_state_async(session)

        asyncio.create_task(watchdog_loop(session))
        asyncio.create_task(console_seed_input_listener(session))

        print("[System] Entering safe 100ms polling balance check loop...", flush=True)

        computedNextBet = float(await calculate_next_progression_step(session, float(previousWagerAmount)))
        total_profit = float(walletStash - trueOriginalBalance)
        log_bet_info(float(computedNextBet), float(walletStash), float(total_profit))

        bet_payload = {
            "currency": currency_symbol.lower(),
            "game": "dice",
            "amount": f"{float(computedNextBet):.8f}",
            "rule": "under",
            "multiplier": "2",
            "bet_value": "49.5"
        }
        previousWagerAmount = float(computedNextBet)
        bet_response = await api_request_async(session, "bet/place", method="POST", payload=bet_payload)
        total_bets_placed += 1

        parsed_bal = extract_balance_from_bet_response(bet_response)
        if parsed_bal is not None:
            walletStash = float(parsed_bal)
            last_observed_balance = float(walletStash)
            last_balance_change_time = float(time.time())
            save_state()

        while True:
            if float(walletStash) >= float(targetBalance):
                total_profit = float(walletStash - trueOriginalBalance)
                print(f"\n[System] TARGET REACHED ({float(walletStash):.8f}). Total Cumulative Profit: {total_profit:+.8f}. Halting.", flush=True)
                for f_path in [STATE_FILE, MASTER_STATE_FILE]:
                    if os.path.exists(f_path):
                        try:
                            os.remove(f_path)
                        except Exception:
                            pass
                sys.exit(0)

            current_balance = float(last_observed_balance)
            bal_check = await get_user_balance_async(session)

            if bal_check is not None:
                bal_check_f = float(bal_check)
                if not math.isclose(bal_check_f, current_balance, abs_tol=float(1e-9)):
                    walletStash = float(bal_check_f)
                    last_observed_balance = float(walletStash)
                    last_balance_change_time = float(time.time())

                    if auto_rotate_interval > 0 and total_bets_placed > 0 and total_bets_placed % auto_rotate_interval == 0:
                        rand_seed = generate_random_seed()
                        print(f"\n[Auto-Rotate] Reached {total_bets_placed} bets. Generating new random seed...", flush=True)
                        await set_client_seed_async(session, rand_seed)

                    computedNextBet = float(await calculate_next_progression_step(session, float(previousWagerAmount)))
                    total_profit = float(walletStash - trueOriginalBalance)
                    log_bet_info(float(computedNextBet), float(walletStash), float(total_profit))

                    bet_payload = {
                        "currency": currency_symbol.lower(),
                        "game": "dice",
                        "amount": f"{float(computedNextBet):.8f}",
                        "rule": "under",
                        "multiplier": "2",
                        "bet_value": "49.5"
                    }

                    previousWagerAmount = float(computedNextBet)
                    bet_response = await api_request_async(session, "bet/place", method="POST", payload=bet_payload)
                    total_bets_placed += 1

                    parsed_bal = extract_balance_from_bet_response(bet_response)
                    if parsed_bal is not None:
                        walletStash = float(parsed_bal)
                        last_observed_balance = float(walletStash)
                        save_state()
            else:
                await asyncio.sleep(float(0.1))


def main():
    global api_token, currency_symbol, active_client_seed, auto_rotate_interval, targetBalance

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