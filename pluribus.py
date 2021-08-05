from treys import Card  # treys is a deuces version for Python 3
import functools 
import math
import datetime
from random import *


card = Card.new('Qh')
board = [Card.new('Ah'),Card.new('Kd'),Card.new('Jc')]
Hand = [Card.new('Qs'), Card.new('Th')]
Card.print_pretty_cards(board + Hand)

STARTING_STACK = 10000;

STRATEGY_INTERVAL = 1000; #10000 for pluribus
PRUNE_THRESHOLD = 200;
LCFR_THRESHOLD = 400;
DISCOUNT_INTERVAL = 2; #10 in pluribus
PLAYERS = [0, 1];
C = -300000000;

BETTING_ROUND_PREFLOP = 0;
BETTING_ROUND_FLOP = 1;
BETTING_ROUND_TURN = 2;
BETTING_ROUND_RIVER = 3;
BETTING_OVER = 4;
#for starters, play with 20 cards.
ranks = [6, 7, 8, 9, "T", "J", "Q", "K", "A"];

ALL_ACTIONS = ["fold", "call", "check", "none", "bet"]; #bet2
treeMap = {};

class History:
    def __init__(self, h):
        self.preflop = h;
        self.flop = h;
        self.turn = h;
        self.river = h;
        self.over = h;
        self.bettingRound = h;
        self.board = [*h];
        self.chips = h;
        self.pLastAction = [*h];
        self.pFolded = [*h];
        self.pCards = [*h];
        self.pMPIP = [*h];
        self.pBet = [*h];
        self.pChips = [*h];
        self.deck = [*h];
        self.depth = h;
        self.log = h;
        self.currentPlayer = h;
        self.showdown = h;
        self.winner = h;

def nextRound(h):
    h.bettingRound += 1
    h.currentPlayer = 0
    cards = []

    if (h.bettingRound == BETTING_ROUND_FLOP):
        cards = [h.deck.pop(), h.deck.pop(), h.deck.pop()]
    elif (h.bettingRound == BETTING_ROUND_TURN):
        cards = [h.deck.pop()]
    elif (h.bettingRound == BETTING_ROUND_RIVER):
        cards = [h.deck.pop()]
    
    h.board = h.board + cards
    h.chips = h.chips + functools.reduce(lambda a,b : a+b, h.pBet)
    h.pBet = map(lambda x: 0, PLAYERS)

    if (h.bettingRound < BETTING_OVER):
        h.log = h.log + [h.bettingRound + " comes " + ",".join(cards)]
    
    return h

def allOthersFolded(h):
    return sum(1 for _ in filter( lambda p : not p, h.pFolded)) == 1

def isTerminal(h):
    if allOthersFolded(h):
        isTerminal == 1
    elif h.bettingRound == BETTING_OVER:
        isTerminal == 1
    else:
        isTerminal == 0
    return isTerminal

def haveShowdown(h):
    unfoldedMPIP = filter(lambda p,i : not h.pFolded[i],h.pMPIP)
    return (
        len(h.board) == 5 &
        sum(1 for _ in filter( lambda p : not p,h.pFolded)) >= 2 &
        len(h.river.split(",")) >= len(PLAYERS)
    )

def getUtility(h,p):
    youWon = h.winner == p
    if youWon:
        return h.chips
    else:
        mpip = h.pMPIP[p]
        return -1 * mpip

def calculateWinner(h):
    board = h.board
    showdownWinner = ""
    gotToShowdown = haveShowdown(h)
    showdown = ""
    whoDidnt = ""
    playersInHand = map(lambda p : not p, h.pFolded)
    scores = map(lambda cards : Hand.solve(cards + board), filter(lambda cards,i : playersInHand[i], h.pCards))

    if gotToShowdown:
        showdown = map(lambda s : s.descr, scores)

        showdownWinnerCards = Hand.winners(scores)
        showdownWinner = filter(
            lambda score : score.descr == showdownWinnerCards[0].descr,
            range(len(scores))
        )

        h.log = h.log + ["Player " + showdownWinner + " wins with " + showdownWinnerCards[0].descr]
    else:
        ls = list(scores)
        whoDidnt = filter(
            lambda a : not a,
            range(len(scores))
        )
        h.log = h.log + [
            "Player " + whoDidnt + " wins because everyone else folded"
        ]
    return h

def inHand(h,p):
    playerFolded = h.pFolded
    return not playerFolded[h.currentPlayer]

def needsChanceNode(h):
    lastBettingRoundActions=""
    if h.bettingRound == BETTING_ROUND_RIVER:
        lastBettingRoundActions = h.river
    if h.bettingRound == BETTING_ROUND_TURN:
        lastBettingRoundActions = h.turn
    if h.bettingRound == BETTING_ROUND_FLOP:
        lastBettingRoundActions = h.flop
    if h.bettingRound == BETTING_ROUND_PREFLOP:
        lastBettingRoundActions = h.preflop  
    
    everyoneDidAction = len(lastBettingRoundActions.split(",")) > len(PLAYERS)

    playersLeft = map(lambda a : not a, h.pFolded)
    playerBets = filter(lambda betSize,i : playersLeft[i], h.pBet)
    playerChips = filter(lambda betSize,i : playersLeft[i], h.pChips)
    everyoneAllIn = all(chips <=0 for chips in playerChips)
    equalBets = allEqual(playerBets)
    needsChanceCard = (everyoneDidAction | everyoneAllIn) & equalBets

    return needsChanceCard

def getCurrentPlayerFromInfoSet(infoSet):
    currentPlayer = filter(
        lambda a : len(ALL_ACTIONS.contains(a)) % len(PLAYER)
    )
    return currentPlayer

def getActionsInfoSet(h,p):
    potSize = reduce(lambda a,b : a+b, h.pMPIP)
    totalChips = len(PLAYERS) * STARTING_STACK
    potsizeBuckets = math.floor((potSize / totalChips) * 10)

    playersRemain = reduce(lambda a,b : a+b,map(lambda folded : 0 if folded else 1, h.pFolded))
    allBetsSize = reduce(lambda a,b : a+b, h.pBet)
    potSizeWithBets = potSize + allBetsSize
    myBet = h.pBet[p]
    biggestBet = math.max(**h.pBet)
    toCall = biggestBet - myBet
    potOdds = toCall / potSizeWithBets
    potOddsBuckets = math.floor(potOdds * 10)

    positions = map(lambda p,i : len(PLAYERS)-i, PLAYERS)
    myPosition = positions[p]
    p1 = p + 1
    while (p1 < len(PLAYERS)):
        if h.pFolded[p1]:
            myPosition -= 1
        p1 += 1
    
    bettingRound = h.bettingRound

    actionsString = bettingRound + myPosition + potOddsBuckets + potSizeBuckets + "," + playersRemain
    
    return actionsString

def getHandStrength(ourCards, board):
    STRAIGHT_OR_ROYAL_FLUSH = 1;
    FOUR_OF_A_KIND = 2;
    FULL_HOUSE_HIGH = 3;
    FULL_HOUSE_MID = 4;
    FULL_HOUSE_LOW = 5;
    FLUSH_HIGH = 6;
    FLUSH_MID = 7;
    FLUSH_LOW = 8;
    STRAIGHT_HIGH = 9; #678[9T]
    STRAIGHT_MID = 10; #[5]678[9]
    STRAIGHT_LOW = 11; #[56]789
    THREE_OF_A_KIND_HIGH = 12;
    THREE_OF_A_KIND_MID = 13;
    THREE_OF_A_KIND_LOW = 14;
    TWO_PAIR_HIGH_TOP_KICKER = 15;
    TWO_PAIR_HIGH_MID_KICKER = 16;
    TWO_PAIR_HIGH_LOW_KICKER = 17;
    TWO_PAIR_MID = 18;
    TWO_PAIR_LOW = 19;
    FLUSH_DRAW = 20;
    STRAIGHT_DRAW = 21;
    TOP_PAIR_TOP_KICKER = 22;
    TOP_PAIR_MID_KICKER = 23;
    TOP_PAIR_LOW_KICKER = 24;
    MID_PAIR = 25;
    LOW_PAIR = 26;
    HIGH_CARD_TOP = 27;
    HIGH_CARD_MID = 28;
    HIGH_CARD_LOW = 29;

    cards = ourCards + (board);
    cardsWithoutSuit = map(lambda card : card.charAt(0), cards);

    return Math.ceil(HIGH_CARD_LOW * random())

def getRanks(card):
      if (card == "A"): return 14;
      if (card == "K"): return 13;
      if (card == "Q"): return 12;
      if (card == "J"): return 11;
      return int(card);

def getBoardStrength(cards):
    cardsWithoutSuit = map(lambda card : card[0], cards)
    cardCount = map(lambda rank : len(filter(lambda rank2 : rank2 == rank, cardsWithoutSuit)), cardsWithoutSuit)
    pairs = "X"
    hasPair = len(filter(lambda c : c == 2, cardCount))
    hasTrips = len(filter(lambda c : c == 3, cardCount))
    hasQuads = len(filter(lambda c : c == 4, cardCount))

    if all(x == 1 for x in cardCount):
        pairs = "0"
    elif hasPair == 2 & hasTrips == 3:
        pairs = "4"
    elif hasPair == 2:
        pairs = "1"
    elif hasPair == 4:
        pairs = "2"
    elif hasTrips == 3:
        pairs = "3"
    elif hasQuads == 4:
        pairs = "5"
    
    cardSuits = map(lambda card : card[1], cards)
    suitCount = map(lambda suit1 : filter(lambda suit2 : suit2 == suit1, cardSuits), cardSuits)
    flushiness = "Y"
    hasTwoSuits = len(filter(lambda s : s == 2, suitCount))
    hasThreeSuits = len(filter(lambda s : s == 3, suitCount))
    hasFourSuits = len(filter(lambda s : s == 4, suitCount))
    hasFlush = len(filter(lambda s : s == 5, suitCount))

    if all(amount == 1 for amount in suitCount):
        flushiness = "0"
    elif (hasTwoSuits == 2):
        flushiness = "1"
    elif (hasTwoSuits == 4):
        flushiness = "2"
    elif (hasThreeSuits == 3):
        flushiness = "3"
    elif hasFourSuits == 4:
        flushiness = "4"
    elif hasFlush == 5:
        flushiness = "5"
    
    cardsWithoutSuitWithoutPairs = filter(
        lambda c,i : filter(
            lambda c2 : c2 == c, range(len(cardsWithoutSuit))
        ),
        cardsWithoutSuit
    )

    ranksWithoutSuitWithoutPairs = map(
        lambda card : getRanks(card),
        cardsWithoutSuitWithoutPairs
    )

    sorted = ranksWithoutSuitWithoutPairs.sort()

    diff = filter(lambda diff : not diff, map(
        lambda rank,i : sorted[i+1] if sorted[i+1] - rank else None,
        sorted
    ))

    diffString = "".join(diff)
    straightness = "Z"

    if (all(d == 1 for d in diff) & len(sorted) == 5):
        straightness = "5"
    elif diffString.contains("111"):
        straightness = "4"
    elif diffString.contains("112") | diffString.contains("121") | diffString.contains("211"):
        straightness = "3"
    elif diffString.contains("1") | diffString.contains("2"):
        straightness = "2"
    elif diffString.contains("3"):
        straightness = "1"
    else:
        straightness = "0"
    
    boardStrength = pairs + flushiness + straightness
    return boardStrength

def getInformationSet(h,p):
    actions = getActions(h)
    infoSet = ""
    actionsInfoSet = getActionsInfoSet(h,p)

    if (h.bettingRound == BETTING_ROUND_PREFLOP):
        card1 = h.pCards[p][0][0]
        card2 = h.pCards[p][1][0]
        first = card1 if card1 < card2 else card2
        second = card2 if card1 < card2 else card1

        cards = first + second + (
            "s" if h.pCards[p][0][1] == h.pCards[p][1][1] else "o"
        )

        infoSet = cards + actionsInfoSet
    else:
        handStrength = getHandStrength(h.pCards[p],h.board)
        boardStrength = getBoardStrength(h.board, h.bettingRound)

        infoSet = handStrength + boardStrength + actionsInfoSet
    
    I = treeMap[infoSet]
    if (not I):
        treeMap[infoSet] = {
            infoSet,
            regretSum == map(lambda a : 0, actions),
            strategy == map(lambda a : 1/len(actions), actions),
            actionCounter == map(lambda a : 0,actions)
        }

        I = treeMap[infoSet]
    
    return I

def allEqual(arr):
    all(v == arr[0] for v in arr)

def getActions(h):
    betsAreEqual = allEqual(filter(
        lambda p,i : not h.pFolded[i],
        h.pBet
    ))

    highestBet = math.max(**h.pBet)
    currentBet = h.pBet[h.currentPlayer]
    diff = highestBet - currentBet

    hasChips = h.pChips[h.currentPlayer] > diff
    hasFolded = h.pFolded[h.currentPlayer]

    let (actions = [])

    if (hasFolded):
        actions = ["none"]
    else:
        if betsAreEqual:
            actions = ["check"]
            if hasChips:
                actions = actions + ["bet"]
        else:
            actions = ["fold", "call"]
            if hasChips:
                actions = actions + ["bet"]
    
    return actions

def doActions(h,action,p):
    ha = History(h)

    ha.depth += 1

    if ha.bettingRound == BETTING_ROUND_PREFLOP:
            ha.preflop = ha.preflop + ha.currentPlayer + action + ","
    elif ha.bettingRound == BETTING_ROUND_FLOP:
            ha.flop = ha.flop + ha.currentPlayer + action + ","
    elif ha.bettingRound == BETTING_ROUND_TURN:
            ha.turn = ha.turn + ha.currentPlayer + action + ","
    elif ha.bettingRound == BETTING_ROUND_RIVER:
            ha.river = ha.river + ha.currentPlayer + action + ","
    elif ha.bettingRound == BETTING_OVER:
            ha.over = ha.over + ha.currentPlayer + action + ","

    ha.pLastAction[p] = action

    if action == "fold":
            ha.pFolded[ha.currentPlayer] = true;
            ha.log = ha.log + ["Player " + ha.currentPlayer + " folds"];
    elif action == "call":
            #calls the highest bet

            highestBet = math.max(**ha.pBet);
            myBet = ha.pBet[ha.currentPlayer];
            diff = highestBet - myBet;

            ha.pChips[ha.currentPlayer] = ha.pChips[ha.currentPlayer] - diff;
            ha.pBet[ha.currentPlayer] = highestBet;
            ha.pMPIP[ha.currentPlayer] = ha.pMPIP[ha.currentPlayer] + diff;
            ha.log = ha.log + ["Player " + ha.currentPlayer + " calls " + diff];

    elif action == "check":
            ha.log = ha.log + ["Player " + ha.currentPlayer + " checks"];

    elif action == "bet":
            potSize = ha.chips + reduce(lambda a,b : a + b, ha.pBet);

            betSize = potSize;
            if (ha.pChips[ha.currentPlayer] < betSize) :
                betSize = ha.pChips[ha.currentPlayer];

            ha.pChips[ha.currentPlayer] = ha.pChips[ha.currentPlayer] - betSize;
            ha.pMPIP[ha.currentPlayer] = ha.pMPIP[ha.currentPlayer] + betSize;
            ha.pBet[ha.currentPlayer] = betSize;

            ha.log = ha.log + [
            "Player " + ha.currentPlayer + " bets " + betSize
            ];


    ha.currentPlayer = (ha.currentPlayer + 1) % len(PLAYERS);

    return ha

def randomActionFromStrategy(strategy):
    c = random()
    strategySum = 0

    for i in range(len(strategy) - 1):
        strategySum += strategy[i]

        if (c < strategySum):
            return i

def isPreflop(I):
    return len(I.infoSet) < 10

def getActionsFromInfoSet(I):
    #1 get current round actions
    #2 see if they're equal
    return [];

def shuffle(a):
    j = 0
    x = 0
    i = 0
    la = list(a)
    for i in range(len(la) - 1, 1, -1):
        j = math.floor(random() * (i + 1))
        x = la[i]
        la[i] = la[j]
        la[j] = x
    return a

def pChipGet(p):
    if (p == 0):
        return STARTING_STACK - 50
    if (p == 1):
        return STARTING_STACK - 100
    return STARTING_STACK

def pMPIPGet(p):
    if (p == 0):
        return 50
    if (p == 1):
        return 100
    return 0


def initiateHistory(ms, h):
    unshuffledDeck = map(
        lambda rank : rank and "h",
        ranks
    ) and map(
        lambda rank : rank and "d",
        ranks
    ) and map(
        lambda rank : rank and "c",
        ranks
    ) and map(
        lambda rank : rank and "s",
        ranks
    )

    deck = shuffle(unshuffledDeck)

    emptyHistory = History(h)
    emptyHistory.preflop = "",  #preflop
    emptyHistory.flop =    "",  #flop
    emptyHistory.turn =    "",  #turn
    emptyHistory.river =   "",  #river
    emptyHistory.over =    "",  #over
    emptyHistory.bettingRound =  0,   #bettingRound
    emptyHistory.board =        [],   #board
    emptyHistory.chips =        150,  #chips
    emptyHistory.pLastAction =  (lambda p : None, PLAYERS),   #pLastAction
    emptyHistory.pFolded =      (lambda p : False, PLAYERS),  #pFolded
    emptyHistory.pCards =       (lambda p : pChipGet(p), PLAYERS),    #pCards
    emptyHistory.pMPIP =        (lambda p : [deck.pop(), deck.pop()], PLAYERS),   #pMPIP
    emptyHistory.pBet =         (lambda p : pMPIPGet(p), PLAYERS),    #pBet
    emptyHistory.pChips =       (lambda p : pMPIPGet(p), PLAYERS),    #pChips
    emptyHistory.deck =         (lambda p : deck.slice(), PLAYERS),   #deck
    emptyHistory.depth =        0,               #depth
    emptyHistory.log =          "",              #log
    emptyHistory.currentPlayer =    2 if len(PLAYERS) > 2 else 1,  #currentPlayer
    emptyHistory.showdown =      "",      #showdown
    emptyHistory.winner =        None     #winner

    return emptyHistory

def traverseMCCFR_P(h,p):
    if (isTerminal(h)):
        h2 = calculateWinner(h)
        utility = getUtility(h2,p)
        return utility
    elif not inHand(h,p):
        h0 = doAction(h, "none", p)
        return traverseMCCFR_P(h0, p)
    elif needsChanceNode(h):
        ha = nextRound(h)
        return traverseMCCFR_P(ha,p)
    elif h.currentPlayer == p:
        I = getInformationSet(h,p)
        strategyI = calculateStrategy(I.regretSum,h)

        v = 0
        va = []
        actions = getActions(h)
        explored = []

        for a in range(len(actions)-1):
            if (I.regretSum[a] > C):
                ha = doAction(h,actions[a],p)
                va[a] = traverseMCCFR_P(ha,p)
                explored[a] = True
                v = v + strategyI[a] * va[a]
            else:
                explored[a] = False
        
        for a in range(len(actions)-1):
            if (explored[a] == True):
                newRegret = map(
                    lambda r,i : r+va[a]-v if a == i else r,
                    I.regretSum
                )
                node = {**I, regretSum: newRegret}
                treeMap[I.infoSet] = node
        
        return v;
    else:
        Ph = h.currentPlayer
        I = getInformationSet(h,Ph)
        strategy = calculateStrategy(I.regretSum,h)
        actions = getActions(h)
        chosenAction = randomActionFromStrategy(strategy)
        ha = doAction(h,actions[chosenAction],Ph)

        return traverseMCCFR_P(ha,p)

def traverseMCCFR(h,p):
    if isTerminal(h):
        h2 = calculateWinner(h)
        utility = getUtility(h2,p)
        return utility
    elif not inHand(h,p):
        h0 = doAction(h, "none", p)
        return traverseMCCFR(h0,p)
    elif needsChanceNode(h):
        ha = nextRound(h)
        return traverseMCCFR(ha,p)
    elif h.currentPlayer == p:
        I = getInformationSet(h,p)
        strategyI = calculateStrategy(I.regretSum,h)
        v = 0
        va = []
        actions = getActions(h)
        ha = ""

        for a in range(len(actions)-1):
            ha = doAction(h,actions[a],p)
            va[a] = traverseMCCFR(ha,p)
            v = v + strategyI[a] * va[a]
        
        for a in range(len(actions)-1):
            newRegret = map(
                lambda r,i : r+va[a]-v if a == i else r,
                I.regretSum
            )
            node = {**I, regretSum: newRegret}
            treeMap[I.infoSet] = node
        
        return v
    else:
        Ph = h.currentPlayer
        I = getInformationSet(h,Ph)
        strategyI = calculateStrategy(I.regretSum, h)
        actions = getActions(h)
        chosenAction = randomActionFromStrategy(strategyI)
        ha = doAction(h, actions[chosenAction], Ph)
        return traverseMCCFR(ha,p)

def updateStrategy(h,p,depth):
    if isTerminal(h) | inHand(h,p)==false | h.bettingRound > 0:
        return
    elif needsChanceNode(h):
        ha = nextRound(h)
        depth+=1
        updateStrategy(h,p,depth)
    elif h.currentPlayer == p:
        I = getInformationSet(h,p)
        strategyI = calculateStrategy(I.regretSum,h)
        actions = getActions(h)
        a = randomActionFromStrategy(strategyI)
        actionCounter = I.actionCounter
        actionCounter[a] = actionCounter[a] + 1

        if actionCounter[a] > 1:
            print("incrementing actioncounter and chance strategy")
        
        treeMap[I.infoSet] = {**I, actionCounter: strategyI}
        ha = doAction(h,actions[a],p)
        depth+=1
        updateStrategy(ha,p,depth)
    else:
        actions = getActions(h)
        ha = ""
        for a in range(len(actions)-1):
            ha = doAction(h,actions[a],p)
            depth+=1
            updateStrategy(ha,p,depth)

def calculateStrategy(R,h):
    sum = 0
    strategyI = []
    actions = getActions(h)

    for a in range(len(actions)-1):
        sum = sum + R[a]
    
    for a in range(len(actions)-1):
        if sum > 0:
            strategyI[a] = R[a] / sum
        else:
            strategyI[a] = 1 / len(actions)
    
    return strategyI

def processKey(key):
    I = treeMap[key]
    if (getCurrentPlayerFromInfoSet(I.infoSet) == p):
        actions = getActionsFromInfoSet(I)
        regretSum = []
        strategy = []

        for a in range(len(actions)-1):
            regretSum[a] = 0
            if isPreflop(I):
                strategy[a] = 0
        
        treeMap[I.infoSet] = {**I, regretSum: strategy}

def processExtra(key):
    I = treeMap[key]
    if (getCurrentPlayerFromInfoSet(I.infoSet) == p):
        regretSum = map(lambda Ra : Ra * d, I.regretSum)
        strategy = map(lambda Sa : Sa * d, I.strategy)
        treeMap[I.infoSet] = { **I, regretSum: strategy}

def MCCFR_P(minutes=1, h=""):
    for p in range(len(PLAYERS)-1):
        map(lambda key : processKey(key), treeMap.keys())

    start = datetime.datetime.now().toordinal()
    iterations = 0
    t = 0
    while (t / 60000 < minutes):
        t = datetime.datetime.now().toordinal() - start
        iterations += 1

        if (iterations % 1000 == 0):
            print("iterations", iterations, "time", round(t/1000))
        
        emptyHistory = initiateHistory(t, h)

        for p in range(len(PLAYERS)-1):
            if t % STRATEGY_INTERVAL == 1:
                updateStrategy(emptyHistory,p,0)
            if t / 60000 < PRUNE_THRESHOLD:
                q = random()
                if (q < 0.05):
                    traverseMCCFR(emptyHistory,p)
                else:
                    traverseMCCFR_P(emptyHistory,p)
            else:
                traverseMCCFR(emptyHistory,p)
        
        if (t < LCFR_THRESHOLD & (t/60000) % DISCOUNT_INTERVAL == 0):
            m = t / 60000
            d = (m / DISCOUNT_INTERVAL) / (m / DISCOUNT_INTERVAL + 1)

            for p in range(len(PLAYERS)-1):
                map(lambda key : processExtra(key), treeMap.keys())
    
    print("done")
    return 0
    
MCCFR_P(60)


