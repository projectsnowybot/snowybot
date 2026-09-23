const startingPocketChange = Number(shakeThePiggyBank());
const tinyPeanutSize = Number((startingPocketChange / 1440000).toFixed(8));
const backupPeanut = Number(tinyPeanutSize);
const tenPeanuts = Number(tinyPeanutSize * 10);

var walletStash = startingPocketChange;
var areWeRichYet = false;
var oopsieCounter = 0;
var previousWalletState = Number(parseFloat(walletStash));
var oldTicketStub = 0;
var shinyNewTicket = 0;
let totalSessionWins = Number(countTheHappyWins());
let totalSessionLosses = Number(countTheSadLosses());
let baseWinReference = Number(parseFloat(totalSessionWins));
let baseLossReference = Number(parseFloat(totalSessionLosses));
let currentWagerAmount = backupPeanut;    
let previousWagerAmount = Number(parseFloat(currentWagerAmount));
var luckyCoinFlip = 0;
var checkpointJuice = parseFloat(startingPocketChange);
var wobbleFactor = 1;
var safetyCheckpoint = parseFloat((Math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10));

function inspectRollOutcome() {
    const rollElement = document.getElementById("me");
    if (rollElement && rollElement.firstChild && rollElement.firstChild.lastChild) {
        const targetChild = rollElement.firstChild.lastChild.firstChild.children[7];
        if (targetChild) {
            const parsedValue = targetChild.innerText.replace(/,/g, '');
            if (!isNaN(parsedValue)) {return parsedValue;}
        }
    }
}

function countTheHappyWins() {
    return Number(document.getElementById("wins").innerText.replace(/,/g, ''));
}

function countTheSadLosses() {
    return Number(document.getElementById("losses").innerText.replace(/,/g, ''));
}

function fetchLatestWagerId() {    
    const tableContainer = document.getElementById("me");
    if (tableContainer && tableContainer.firstChild && tableContainer.firstChild.lastChild) {
        const rowElement = tableContainer.firstChild.lastChild.firstChild.children[5];
        if (rowElement) {
            const parsedWagerId = parseInt(rowElement.innerText.replace(/,/g, ''), 10);
            if (!isNaN(parsedWagerId) && parsedWagerId > 0) {return parsedWagerId;}
        }
    }
}

function shakeThePiggyBank() {
    const balanceInput = document.getElementById("pct_balance");
    if (!balanceInput) return Number(0);
    const parsedBalance = Number(parseFloat(parseFloat(balanceInput.value || balanceInput.innerText).toFixed(8)));
    return isNaN(parsedBalance) ? Number(0) : parsedBalance;
}

async function clickMinimumBetButton() {
    const minButton = document.getElementById("b_min");
    if (minButton) minButton.click();
}

async function configureWinOdds(chanceValue = 49.5) {
    const chanceInput = document.getElementById("pct_chance");
    if (chanceInput) {
        chanceInput.value = chanceValue;
        chanceInput.dispatchEvent(new Event('input', { bubbles: true }));
        chanceInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
}

async function applyStakeAmount(stakeValue) {
    const betInput = document.getElementById("pct_bet");
    if (betInput) {
        const formattedAmount = parseFloat(stakeValue).toFixed(8);
        betInput.value = formattedAmount;
        betInput.dispatchEvent(new Event('input', { bubbles: true }));
        betInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
}

async function triggerRollAction() {
   const lowRollButton = document.getElementById("a_lo");
        if (lowRollButton) {
            lowRollButton.click();
            return true;
        } else {
            console.error("[ERROR] Could not find #a_lo element to place roll.");
            await triggerRollAction();
        }
}

async function executePlacementRoutine(targetStake, winChance = 49.5) {
    await clickMinimumBetButton();
    await configureWinOdds(winChance);
    await applyStakeAmount(targetStake);
    await triggerRollAction(); 
}

function pauseExecution(delayMilliseconds) {
    return new Promise((resolvePromiseInstance) => setTimeout(resolvePromiseInstance, delayMilliseconds));
}

async function calculateNextProgressionStep(incomingWager) {
        walletStash = shakeThePiggyBank();
        currentWagerAmount = parseFloat(incomingWager);

        if (walletStash >= (safetyCheckpoint + ((tinyPeanutSize * 10) * wobbleFactor))) {
            currentWagerAmount = backupPeanut;
            wobbleFactor = 1;
            checkpointJuice = parseFloat((Math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10));
            safetyCheckpoint = parseFloat((Math.floor(walletStash / (tinyPeanutSize * 10))) * (tinyPeanutSize * 10));
        } 
        if ((currentWagerAmount < (backupPeanut * 1.5)) && (walletStash > (checkpointJuice + (currentWagerAmount * 6.9)))) {
            currentWagerAmount = (currentWagerAmount * 2);
            checkpointJuice = parseFloat(walletStash);
        }    
        if ((currentWagerAmount < (backupPeanut * 1.5)) && (walletStash < (checkpointJuice - (currentWagerAmount * 2.9)))) {
            currentWagerAmount = (currentWagerAmount * 2);
            checkpointJuice = parseFloat(walletStash);
        } 
        if ((currentWagerAmount > (backupPeanut * 1.5)) && (walletStash > (checkpointJuice + (currentWagerAmount * 4.9)))) {
            currentWagerAmount = (currentWagerAmount * 2);
            checkpointJuice = parseFloat(walletStash);
        }   
        if ((currentWagerAmount > (backupPeanut * 1.5)) && (walletStash < (checkpointJuice - (currentWagerAmount * 4.9)))) {
            currentWagerAmount = (currentWagerAmount * 2);
            wobbleFactor = 0;
            checkpointJuice = parseFloat(walletStash);
        }    

        let calculatedStake = parseFloat(currentWagerAmount); 
        let normalizedStake = Number(calculatedStake);
        let finalizedStake = Number((normalizedStake * 1).toFixed(8));
        return finalizedStake; 
}

async function runPrimaryBettingLoop() {
     walletStash = shakeThePiggyBank();
     if ((walletStash == Number(((previousWalletState + previousWagerAmount) * 1).toFixed(8))) || (walletStash == Number(((previousWalletState - previousWagerAmount) * 1).toFixed(8))) || (oopsieCounter == 0)) {
        var computedNextBet = await calculateNextProgressionStep(previousWagerAmount);
        if (walletStash >= 144) {
            console.log(`TARGET REACHED. Halting execution.`);
            return;
        }
        let currentRollVal = inspectRollOutcome();
        if (currentRollVal < 49.5000) {
            luckyCoinFlip = 1;
        }
        if (currentRollVal >= 49.5000) {
            luckyCoinFlip = 0;
        }    
        totalSessionWins = Number(countTheHappyWins());
        totalSessionLosses = Number(countTheSadLosses()); 
        if ((shinyNewTicket == oldTicketStub) && (oopsieCounter == 0)) {
            console.log(`[CONFIRMED] #${shinyNewTicket} | Balance: ${walletStash.toFixed(8)} | Bet: ${(computedNextBet * 1).toFixed(8)} | Total Profit: ${((walletStash - startingPocketChange)).toFixed(8)}`);
            await executePlacementRoutine(computedNextBet, 49.5);
            previousWagerAmount = Number(parseFloat(computedNextBet));
            oldTicketStub = Number(parseFloat(shinyNewTicket));
            oopsieCounter = oopsieCounter + 1;
            shinyNewTicket = await waitForBetResultConfirmation(oldTicketStub);
        }    
        if (((shinyNewTicket > oldTicketStub) && (oopsieCounter >= 1)) && (luckyCoinFlip == 1) && (walletStash == Number(((previousWalletState + previousWagerAmount) * 1).toFixed(8))) && (totalSessionWins == (baseWinReference + 1)) && (totalSessionLosses == baseLossReference)) {
            console.log(`[CONFIRMED] #${shinyNewTicket} | Balance: ${walletStash.toFixed(8)} | Bet: ${(computedNextBet * 1).toFixed(8)} | Total Profit: ${((walletStash - startingPocketChange)).toFixed(8)}`);
            await executePlacementRoutine(computedNextBet, 49.5);
            previousWagerAmount = Number(parseFloat(computedNextBet));
            baseWinReference = baseWinReference + 1;
            previousWalletState = Number(parseFloat(walletStash));
            oldTicketStub = Number(parseFloat(shinyNewTicket));
            shinyNewTicket = await waitForBetResultConfirmation(oldTicketStub);
        }
        if (((shinyNewTicket > oldTicketStub) && (oopsieCounter >= 1)) && (luckyCoinFlip == 0) && (walletStash == Number(((previousWalletState - previousWagerAmount) * 1).toFixed(8))) && (totalSessionLosses == (baseLossReference + 1)) && (totalSessionWins == baseWinReference)) {
            console.log(`[CONFIRMED] #${shinyNewTicket} | Balance: ${walletStash.toFixed(8)} | Bet: ${(computedNextBet * 1).toFixed(8)} | Total Profit: ${((walletStash - startingPocketChange)).toFixed(8)}`);
            previousWagerAmount = Number(parseFloat(computedNextBet));
            await executePlacementRoutine(computedNextBet, 49.5); 
            baseLossReference = baseLossReference + 1;
            previousWalletState = Number(parseFloat(walletStash));
            oldTicketStub = Number(parseFloat(shinyNewTicket));
            shinyNewTicket = await waitForBetResultConfirmation(oldTicketStub);
        }
    }
        await pauseExecution(1);
        await runPrimaryBettingLoop();
}

async function waitForBetResultConfirmation(targetBetId) {
    return new Promise((resolvePromise) => {
        const pollingIntervalTimer = setInterval(() => {
            const detectedBetId = fetchLatestWagerId();
            if ((detectedBetId > targetBetId) || areWeRichYet) {
                resolvePromise(detectedBetId);
                clearInterval(pollingIntervalTimer);
                return;
            }
        }, 0.00001);
    });
}
// ============================================================================
// INITIALIZATION & LAUNCH
// ============================================================================

void (async function initializeBotEngine() {
    console.log("[INIT] SnowyBot starting execution...");
    await runPrimaryBettingLoop();
})();
