// ============================================================================
// BET EXECUTION
// ============================================================================

const initialBalance = Number(getPlatformBalance());
const beatsbase = Number((initialBalance / 14400).toFixed(8));
const beatsbasetwo = Number(beatsbase * 1.25);
const tenTimesBase = Number(beatsbase * 10);
const fourTimesBase = Number(beatsbase * 4);
const sevenTimesBase = Number(beatsbase * 7);
const eightTimesBase = Number(beatsbase * 8);
const thirtyTwoTimesBase = Number(beatsbase * 32);

var currentBalance = initialBalance;
var balanceChunks = Math.floor(initialBalance / tenTimesBase);
var isTargetReached = false;
var betAttemptCount = 0;
var balanceMultiplier = Math.floor(currentBalance / tenTimesBase);
var lowerBracketLimit = balanceMultiplier * tenTimesBase;
var lastBalance = Number(parseFloat(currentBalance));
var checkpointBalance = parseFloat((Math.floor(initialBalance / (beatsbase * 10))) * (beatsbase * 10));
var initialCheckpoint = parseFloat(checkpointBalance);
var previousBetId = 0;
var currentBetId = 0;
const mult6_9 = Number(beatsbase * 6.9);
const mult7_9 = Number(beatsbase * 7.9);
var upperLowerThreshold = lowerBracketLimit + mult6_9;
var upperUpperThreshold = lowerBracketLimit + mult7_9;
let wins = Number(getDOMWins());
let losses = Number(getDOMLosses());
let initialWins = Number(parseFloat(wins));
let initialLosses = Number(parseFloat(losses));
let activeBet = beatsbasetwo;    
let lastBet = Number(parseFloat(activeBet));
var peakBalance = parseFloat(initialBalance); 
var initialBalanceReference = parseFloat(initialBalance); 
var activeTenTimes = (activeBet * 10);
var activeMult6_9 = (activeBet * 6.9);
var activeMult7_9 = (activeBet * 7.9);
var activeChunks = Math.floor(currentBalance / activeTenTimes);
var activeBaseBracket = activeChunks * activeTenTimes;
var activeLowThreshold = activeBaseBracket + activeMult6_9;
var activeHighThreshold = activeBaseBracket + activeMult7_9; 
var activeTrackedBracket = parseFloat((Math.floor(currentBalance / (activeBet * 10))) * (activeBet * 10));
var safetyHandbrakeLimit = parseFloat(((Math.floor(initialBalance / (beatsbase * 10))) * (beatsbase * 10))-(beatsbase * 20));
var coolzy = Number((beatsbasetwo).toFixed(8));
var lastWinsFlag = 0;
var booze = parseFloat(initialBalance);
let worry;
var betAttemptkool = 0;
var nottoofast = true;
var checkpointBalancetwo = parseFloat((Math.floor(currentBalance / (beatsbase * 10))) * (beatsbase * 10));

function getRollResult() {
    const rollElement = document.getElementById("me");
    if (rollElement && rollElement.firstChild && rollElement.firstChild.lastChild) {
        const targetChild = rollElement.firstChild.lastChild.firstChild.children[7];
        if (targetChild) {
            const parsedValue = targetChild.innerText.replace(/,/g, '');
            if (!isNaN(parsedValue)) {return parsedValue;}
        }
    }
}

function getDOMWins() {
    return Number(document.getElementById("wins").innerText.replace(/,/g, ''));
}

function getDOMLosses() {
    return Number(document.getElementById("losses").innerText.replace(/,/g, ''));
}

function getLatestBetId() {    
    const lastWinsElement = document.getElementById("me");
    if (lastWinsElement && lastWinsElement.firstChild && lastWinsElement.firstChild.lastChild) {
        const betIdChild = lastWinsElement.firstChild.lastChild.firstChild.children[5];
        if (betIdChild) {
            const parsedId = parseInt(betIdChild.innerText.replace(/,/g, ''), 10);
            if (!isNaN(parsedId) && parsedId > 0) {return parsedId;}
        }
    }
}

function getPlatformBalance() {
    const balanceElement = document.getElementById("pct_balance");
    if (!balanceElement) return Number(0);
    const parsedBalance = Number(parseFloat(parseFloat(balanceElement.value || balanceElement.innerText).toFixed(8)));
    return isNaN(parsedBalance) ? Number(0) : parsedBalance;
}

async function clickMinButton() {
    const minButton = document.getElementById("b_min");
    if (minButton) minButton.click();
}

async function setWinChance(chance = 49.5) {
    const chanceInput = document.getElementById("pct_chance");
    if (chanceInput) {
        chanceInput.value = chance;
        chanceInput.dispatchEvent(new Event('input', { bubbles: true }));
        chanceInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
}

async function setBetSize(amount) {
    const betInput = document.getElementById("pct_bet");
    if (betInput) {
        const formattedAmount = parseFloat(amount).toFixed(8);
        betInput.value = formattedAmount;
        betInput.dispatchEvent(new Event('input', { bubbles: true }));
        betInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
}

async function clickLowBetButton() {
   const lowButton = document.getElementById("a_lo");
        if (lowButton) {
            lowButton.click();
            return true;
        } else {
            console.error("[ERROR] Could not find #a_lo element to place roll.");
            await clickLowBetButton();
        }
}

async function executeRoll(amount, chance = 49.5) {
    await clickMinButton();
    await setWinChance(chance);
    await setBetSize(amount);
    await clickLowBetButton(); 
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function getenlightened(boob) {
        currentBalance = getPlatformBalance();
        let newCheck = parseFloat((Math.floor(currentBalance / (beatsbase * 10))) * (beatsbase * 10));
        if ((currentBalance > (boob + (beatsbase * 6.9))) && (currentBalance < (boob + (beatsbase * 16.9)))) {
            return { coolzy: (beatsbasetwo * 2), sadly: (boob + (beatsbase * 7.5)) };
        }  
        if ((currentBalance > (boob + (beatsbase * 16.9))) && (currentBalance < (boob + (beatsbase * 36.9)))) {
            return { coolzy: (beatsbasetwo * 4), sadly: (boob + (beatsbase * 17.5))};
        } 
        if ((currentBalance > (boob + (beatsbase * 36.9))) && (currentBalance < (boob + (beatsbase * 50)))) {
            return { coolzy: (beatsbasetwo * 8), sadly: (boob + (beatsbase * 37.5))};
        }      
        if (currentBalance > (boob + (beatsbase * 50))) {
            return { coolzy: (beatsbasetwo), sadly: newCheck };
        }  
        if (currentBalance < (boob + (beatsbase * 6.9))) {
            return { coolzy: (beatsbasetwo), sadly: newCheck };
        }
}



async function startMainLoop() {
       currentBalance = getPlatformBalance();
       if (currentBalance > (checkpointBalancetwo + (beatsbase * 50))) {
            activeBet = beatsbasetwo;
            booze = parseFloat((Math.floor(currentBalance / (beatsbase * 10))) * (beatsbase * 10));
            checkpointBalance = parseFloat((Math.floor(currentBalance / (beatsbase * 10))) * (beatsbase * 10));
            checkpointBalancetwo = parseFloat((Math.floor(currentBalance / (beatsbase * 10))) * (beatsbase * 10));
            safetyHandbrakeLimit = parseFloat(((Math.floor(currentBalance / (beatsbase * 10))) * (beatsbase * 10))-(beatsbase * 20));
        }

        if ((activeBet<(beatsbasetwo*1.5))&&(currentBalance > (checkpointBalance + (activeBet * 5.9))) && (currentBalance < (checkpointBalance + (activeBet * 6.9))) ) {
            activeBet = (activeBet * 2);
            booze = parseFloat(currentBalance);
            checkpointBalance = parseFloat(currentBalance);
        }    
        if ((activeBet<(beatsbasetwo*1.5))&&(currentBalance < (checkpointBalance - (activeBet * 1.9))) && (currentBalance > (checkpointBalance - (activeBet * 2.9))) ) {
            activeBet = (activeBet * 2);
            booze = parseFloat(currentBalance);
            checkpointBalance = parseFloat(currentBalance);
        } 

        if ((activeBet>(beatsbasetwo*1.5))&&(activeBet<(beatsbasetwo*15))&&(currentBalance > (checkpointBalance + (activeBet * 3.9))) && (currentBalance < (checkpointBalance + (activeBet * 4.9))) ) {
            activeBet = (activeBet * 2);
            booze = parseFloat(currentBalance);
            checkpointBalance = parseFloat(currentBalance);
        }    
        if ((activeBet>(beatsbasetwo*1.5))&&(activeBet<(beatsbasetwo*15))&&(currentBalance < (checkpointBalance - (activeBet * 3.9))) && (currentBalance > (checkpointBalance - (activeBet * 4.9))) ) {
            activeBet = (activeBet * 2);
            booze = parseFloat(currentBalance);
            checkpointBalance = parseFloat(currentBalance);
        } 


        if ((activeBet>(beatsbasetwo*15))&&(currentBalance > (checkpointBalance + (activeBet * 4.9))) && (currentBalance < (checkpointBalance + (activeBet * 5.9))) ) {
            activeBet = (activeBet * 2);
            booze = parseFloat(currentBalance);
            checkpointBalance = parseFloat(currentBalance);
        }    
        if ((activeBet>(beatsbasetwo*15))&&(currentBalance < (checkpointBalance - (activeBet * 4.9))) && (currentBalance > (checkpointBalance - (activeBet * 5.9))) ) {
            activeBet = (activeBet * 2);
            booze = parseFloat(currentBalance);
            checkpointBalance = parseFloat(currentBalance);
        } 
        if (((currentBalance - (safetyHandbrakeLimit + (activeBet * 2))) <= 0)&&(activeBet!==booze)) {
            worry = await getenlightened(checkpointBalancetwo);
            if (worry.coolzy > beatsbasetwo){
                activeBet = parseFloat(worry.coolzy);
                checkpointBalance = parseFloat(worry.sadly);
                booze = parseFloat(((Math.floor(currentBalance / (beatsbase * 10))) * (beatsbase * 10)));
            }
            if (worry.coolzy == beatsbasetwo){
                activeBet = beatsbasetwo;
                checkpointBalance = parseFloat(((Math.floor(currentBalance / (beatsbase * 10))) * (beatsbase * 10)));
                booze = parseFloat(((Math.floor(currentBalance / (beatsbase * 10))) * (beatsbase * 10)));
                safetyHandbrakeLimit = parseFloat(((Math.floor(currentBalance / (beatsbase * 10))) * (beatsbase * 10))-(beatsbase * 20));
                checkpointBalancetwo = parseFloat((Math.floor(currentBalance / (beatsbase * 10))) * (beatsbase * 10));
            }
        }    

        if (currentBalance >= (initialBalance * 24000)) {
            console.log(`TARGET REACHED. Halting execution.`);
            return;
        }
        activeBet = parseFloat(activeBet); 
        let formactiveBet = parseFloat(activeBet); 
        let migraine = Number(formactiveBet);
        let Mybet =  Number((migraine*1).toFixed(8));
        let rollResultVal = getRollResult();
        if (rollResultVal < 49.5000) {
            lastWinsFlag = 1;
        }
        if (rollResultVal >= 49.5000) {
            lastWinsFlag = 0;
        }    
        wins = Number(getDOMWins());
        losses = Number(getDOMLosses()); 
        if ((currentBetId == previousBetId) && (betAttemptCount == 0)) {
            console.log(`[CONFIRMED] #${currentBetId} | Balance: ${currentBalance.toFixed(8)} | Bet: ${(activeBet * 1).toFixed(8)} | Total Profit: ${((currentBalance - initialBalance)).toFixed(8)}`);
            lastBet = Number(parseFloat(Mybet));
            await executeRoll(Mybet, 49.5);
            previousBetId = Number(parseFloat(currentBetId));
            betAttemptCount = betAttemptCount+1 
            currentBetId = await waitForBetCompletion(previousBetId);
        }    
        if (((currentBetId > previousBetId) && (betAttemptCount >= 1)) && (lastWinsFlag == 1) && (currentBalance == Number(((lastBalance + lastBet) * 1).toFixed(8))) && (wins == (initialWins + 1)) && (losses == initialLosses)) {
            console.log(`[CONFIRMED] #${currentBetId} | Balance: ${currentBalance.toFixed(8)} | Bet: ${(activeBet * 1).toFixed(8)} | Total Profit: ${((currentBalance - initialBalance)).toFixed(8)}`);
            lastBet = Number(parseFloat(Mybet));
            await executeRoll(Mybet, 49.5);
            initialWins = initialWins + 1;
            lastBalance = Number(parseFloat(currentBalance));
            previousBetId = Number(parseFloat(currentBetId));
            currentBetId = await waitForBetCompletion(previousBetId);
        }
        if (((currentBetId > previousBetId) && (betAttemptCount >= 1)) && (lastWinsFlag == 0) && (currentBalance == Number(((lastBalance - lastBet) * 1).toFixed(8))) && (losses == (initialLosses + 1)) && (wins == initialWins)) {
            console.log(`[CONFIRMED] #${currentBetId} | Balance: ${currentBalance.toFixed(8)} | Bet: ${(activeBet * 1).toFixed(8)} | Total Profit: ${((currentBalance - initialBalance)).toFixed(8)}`);
            lastBet = Number(parseFloat(Mybet));
            await executeRoll(Mybet, 49.5); 
            initialLosses = initialLosses + 1;
            lastBalance = Number(parseFloat(currentBalance));
            previousBetId = Number(parseFloat(currentBetId));
            currentBetId = await waitForBetCompletion(previousBetId);
        }
        await sleep(1);
        await startMainLoop()
}

async function waitForBetCompletion(targetBetId) {
    return new Promise((resolve) => {
        const pollInterval = setInterval(() => {
            const latestId = getLatestBetId();
            if ((latestId > targetBetId) || isTargetReached) {
                resolve(latestId);
                clearInterval(pollInterval);
                return;
            }
        }, 0.00001);
    });
}
// ============================================================================
// INITIALIZATION & LAUNCH
// ============================================================================

void (async function init() {
    console.log("[INIT] SnowyBot starting execution...");
    await startMainLoop();
})();
