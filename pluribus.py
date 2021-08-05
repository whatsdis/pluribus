from treys import Card as Card  # treys is a deuces version for Python 3, install it with "pip install treys"
from treys import Evaluator
from functools import reduce
import math
from time import perf_counter
import random
from colorama import init, Fore, Style


STARTING_STACK = 10000

STRATEGY_INTERVAL = 1000 #10000 for pluribus
PRUNE_THRESHOLD = 200
LCFR_THRESHOLD = 400
DISCOUNT_INTERVAL = 2 #10 in pluribus
PLAYERS = [0, 1]
C = -300000000

BETTING_ROUND_PREFLOP = 0
BETTING_ROUND_FLOP = 1
BETTING_ROUND_TURN = 2
BETTING_ROUND_RIVER = 3
BETTING_OVER = 4
#for starters, play with 20 cards.
ranks = ["6", "7", "8", "9", "T", "J", "Q", "K", "A"]

ALL_ACTIONS = ["fold", "call", "check", "none", "bet"] #bet2
treeMap = {}

init()  # initialization for colorama to color console output (especially under Windows with console that support ANSI codes like native win command prompt)


def nextRound(h):
    h.bettingRound += 1
    h.currentPlayer = 0
    cards = []
    rounds = ["Preflop", "Flop", "Turn", "River"]

    if (h.bettingRound == BETTING_ROUND_FLOP):
        #draw flop
        cards = [h.deck.pop(), h.deck.pop(), h.deck.pop()]
    elif (h.bettingRound == BETTING_ROUND_TURN):
        #draw turn or river
        cards = [h.deck.pop()]
    elif (h.bettingRound == BETTING_ROUND_RIVER):
        cards = [h.deck.pop()]
    
    h.board = h.board + cards
    h.chips = h.chips + reduce(lambda a,b : a+b, h.pBet)
    h.pBet = list(map(lambda p: 0, PLAYERS))

    if (h.bettingRound < BETTING_OVER):
        h.log = h.log + [rounds[h.bettingRound] + " comes " + ",".join(cards)]
    
    return h

def allOthersFolded(h):
    return len([x for x in filter( lambda p : not p, h.pFolded)]) == 1

def isTerminal(h):
    if allOthersFolded(h):
        return True
    elif h.bettingRound == BETTING_OVER:
        return True
    else:
        return False

def haveShowdown(h):
    unfoldedMPIP = filter(lambda p,i : not h.pFolded[i],h.pMPIP)
    return (
        (len(h.board) == 5) & 
        (len([x for x in filter( lambda p : not p, h.pFolded)]) >= 2) & 
        (len(h.river.split(",")) >= len(PLAYERS))
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

    if gotToShowdown:
        evaluator = Evaluator()
        trBoard = list(map(lambda b : Card.new(b), board)) 
        trCards = []
        for i in range (len(h.pCards)): 
            trCards.append(list(map(lambda c : Card.new(c), h.pCards[i])))
        playersInHand = list(map(lambda p : not p, h.pFolded))
        scores = list(map(lambda cards : evaluator.evaluate(trBoard, cards), filter(lambda cards : playersInHand, trCards)))

        showdown = list(map(lambda s : evaluator.class_to_string(evaluator.get_rank_class(s)), scores))
                
        showdownWinner = scores.index(min(scores)) #for now, ties are not explored
        showdownWinnerCards = showdown[showdownWinner]

        h.log += ([
            "Player " + str(showdownWinner) + " wins with " + showdownWinnerCards + ": " + h.pCards[showdownWinner].__str__()
            ],)
    else:
        whoDidnt = h.pFolded.index(False)
        h.log += ([
            "Player " + str(whoDidnt) + " wins because everyone else folded"
        ],)

    if showdownWinner != '':
        h.winner = showdownWinner
    else:
        h.winner = whoDidnt

    h.showdown = list(map(lambda s, c : s + ": " + c.__str__(), showdown, h.pCards))
    return h

def inHand(h,p):
    playerFolded = h.pFolded
    return not playerFolded[h.currentPlayer]

def needsChanceNode(h):
    # since last chancenode , more than or equal to {PLAYERS.length} actions were taken
    # and all players left ( not action none, not action fold) have equal betsizes
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

    playersLeft = list(map(lambda a : not a, h.pFolded))
    playerBets = list(filter(lambda betSize : True in playersLeft, h.pBet))
    playerChips = list(filter(lambda stackSize : True in playersLeft, h.pChips))
    everyoneAllIn = all(chips <=0 for chips in playerChips)
    equalBets = allEqual(playerBets)
    needsChanceCard = (everyoneDidAction | everyoneAllIn) & equalBets

     # print(
  #   "needschancenoce",
  #   needsChanceCard,
  #   "lastBettingRoundActions",
  #   lastBettingRoundActions,
  #   "everyoneDidAction",
  #   everyoneDidAction,
  #   "playersLeft",
  #   playersLeft,
  #   "playerBets",
  #   playerBets,
  #   "equalBets",
  #   equalBets
  # )
    return needsChanceCard

def getCurrentPlayerFromInfoSet(infoSet):
    currentPlayer = filter(
        lambda a : len(ALL_ACTIONS.contains(a)) % len(PLAYER)
    )
    return currentPlayer

def getActionsInfoSet(h,p):
    potSize = reduce(lambda a,b : a+b, h.pMPIP)
    totalChips = len(PLAYERS) * STARTING_STACK
    potSizeBuckets = math.floor((potSize / totalChips) * 10) #expect to be 0-9, linear to potSize/totalChips ratio

    playersRemain = reduce(lambda a,b : a+b, list(map(lambda folded : '0' if folded else '1', h.pFolded))) # expect to be 010101 in order of position so 2^players combinations
    allBetsSize = reduce(lambda a,b : a+b, h.pBet)
    potSizeWithBets = potSize + allBetsSize
    myBet = h.pBet[p]
    biggestBet = max(h.pBet)
    toCall = biggestBet - myBet
    potOdds = toCall / potSizeWithBets
    potOddsBuckets = math.floor(potOdds * 10) #expect it to be 0-9

    positions = list(map(lambda i : len(PLAYERS)-i, PLAYERS)) #for six players, expect to be [5,4,3,2,1,0]
    myPosition = positions[p] #0 is sb, players.length is dealer. so the higher the better. however, sometimes, you're in position depending on other players folded. this has to be taken into account. Therefore, 0 should be in position. then substract players that have folded
    p1 = p + 1
    while (p1 < len(PLAYERS)):
        if h.pFolded[p1]:
            myPosition -= 1
        p1 += 1
    #expect myposition to be 0 if in position, 1 if almost in position, etc. so 0-8 for 9 players

    bettingRound = h.bettingRound

    actionsString = str(bettingRound) + str(myPosition) + str(potOddsBuckets) + str(potSizeBuckets) + "," + playersRemain
    # expect it to be something like 1023,000111
    
    return actionsString

def getHandStrength(ourCards, board):
    #should return number indicating how strong your hand is. should return about 30 combinations
    STRAIGHT_OR_ROYAL_FLUSH = 1
    FOUR_OF_A_KIND = 2
    FULL_HOUSE_HIGH = 3
    FULL_HOUSE_MID = 4
    FULL_HOUSE_LOW = 5
    FLUSH_HIGH = 6
    FLUSH_MID = 7
    FLUSH_LOW = 8
    STRAIGHT_HIGH = 9 #678[9T]
    STRAIGHT_MID = 10 #[5]678[9]
    STRAIGHT_LOW = 11 #[56]789
    THREE_OF_A_KIND_HIGH = 12
    THREE_OF_A_KIND_MID = 13
    THREE_OF_A_KIND_LOW = 14
    TWO_PAIR_HIGH_TOP_KICKER = 15
    TWO_PAIR_HIGH_MID_KICKER = 16
    TWO_PAIR_HIGH_LOW_KICKER = 17
    TWO_PAIR_MID = 18
    TWO_PAIR_LOW = 19
    FLUSH_DRAW = 20
    STRAIGHT_DRAW = 21
    TOP_PAIR_TOP_KICKER = 22
    TOP_PAIR_MID_KICKER = 23
    TOP_PAIR_LOW_KICKER = 24
    MID_PAIR = 25
    LOW_PAIR = 26
    HIGH_CARD_TOP = 27
    HIGH_CARD_MID = 28
    HIGH_CARD_LOW = 29

    cards = ourCards + (board)
    cardsWithoutSuit = list(map(lambda card : card[0], cards))

    return math.ceil(HIGH_CARD_LOW * random.random()) #1-29

def getRanks(card):
      if (card == "A"): return 14
      if (card == "K"): return 13
      if (card == "Q"): return 12
      if (card == "J"): return 11      
      if (card == "T"): return 10
      return int(card);

def getBoardStrength(cards):
    cardsWithoutSuit = list(map(lambda card : card[0], cards))
    cardCount = list(map(lambda rank : len([x for x in filter(lambda rank2 : rank2 == rank, cardsWithoutSuit)]), cardsWithoutSuit))
    pairs = "X"
    hasPair = len([x for x in filter(lambda c : c == 2, cardCount)])
    hasTrips = len([x for x in filter(lambda c : c == 3, cardCount)])
    hasQuads = len([x for x in filter(lambda c : c == 4, cardCount)])

    if all(x == 1 for x in cardCount):
        pairs = "0"
    elif hasPair == 2:
        pairs = "1"
    elif hasPair == 4:
        pairs = "2"
    elif hasTrips == 3:
        pairs = "3"
    elif hasPair == 2 & hasTrips == 3:
        pairs = "4"
    elif hasQuads == 4:
        pairs = "5"
    #pairs 0,1,2,3,4,5 for no pair, one pair, two pair, trips, fullhouse, quads respectively.
    
    cardSuits = list(map(lambda card : card[1], cards))
    suitCount = list(map(lambda suit1 : len([x for x in filter(lambda suit2 : suit2 == suit1, cardSuits)]), cardSuits))
    flushiness = "Y"
    hasTwoSuits = len([x for x in filter(lambda s : s == 2, suitCount)])
    hasThreeSuits = len([x for x in filter(lambda s : s == 3, suitCount)])
    hasFourSuits = len([x for x in filter(lambda s : s == 4, suitCount)])
    hasFlush = len([x for x in filter(lambda s : s == 5, suitCount)])

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
    #flushiness 0,1,2,3,4,5
    
    cardsWithoutSuitWithoutPairs = list(dict.fromkeys(cardsWithoutSuit))

    ranksWithoutSuitWithoutPairs = list(map(
        lambda card : getRanks(card),
        cardsWithoutSuitWithoutPairs
    ))

    _sorted = sorted(ranksWithoutSuitWithoutPairs) #something like 8 10 12 or 8 10

    def diff_result(rank, i):
        try:
            result = _sorted[i+1] - rank if _sorted[i+1] else None
            return result
        except IndexError:
            pass

    diff = list(filter(lambda diff : diff, map(
        lambda rank,i : diff_result(rank, i),
            _sorted, [index for index, value in enumerate(_sorted)]
    ))) #something like 1,1,1,1 for a straight
     
    diffString = "".join(str(diff).strip('[]').replace(', ', ''))
    straightness = "Z"

    if (all(d == 1 for d in diff) & len(_sorted) == 5):
        #straight on board
        straightness = "5"
    elif diffString.find("111") > -1:
        #open ended on board
        straightness = "4"
    elif (diffString.find("112") > -1) | (diffString.find("121") > -1) | (diffString.find("211") > -1):
        #gutter on board
        straightness = "3"
    elif (diffString.find("1") > -1) | (diffString.find("2") > -1):
        # open ended or double gutter possible
        straightness = "2"
    elif diffString.find("3") > -1:
        straightness = "1"
    else:
        straightness = "0"
    #straightiness 0,1,2,3,4 for nothing possible, openended or gutter unlikely, open ended or (double)gutter possible, gutter on board, open ended on board, straight on board.
    
    boardStrength = pairs + flushiness + straightness
    print("cards", Fore.GREEN, cards, Style.RESET_ALL, "becomes ", boardStrength)
    return boardStrength
    #should return string indicating [pairs][flushyness][straightyness] like 000 for A5To for a total of 216 combinations

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
        boardStrength = getBoardStrength(h.board)

        infoSet = str(handStrength) + boardStrength + actionsInfoSet
    
    # print("infoset", infoSet)
    try :
        I = treeMap[infoSet]
        # print("we found an I that already has been declared!", I)
    except Exception as e :
        #if undefined, create new and return that one
        treeMap[infoSet] = {
           'infoSet': infoSet,
           'regretSum': tuple(list(map(lambda a : 0, actions))),
           'strategy': tuple(list(map(lambda a : 1/len(actions), actions))),
           'actionCounter': tuple(list(map(lambda a : 0, actions)))
        }

        I = treeMap[infoSet]
    
    # print("infoSet", infoSet, "Found")
    return I

"""
 returns true if all values in the array are the same
 @param {*} arr array
"""
def allEqual(arr):
    return all(v == arr[0] for v in arr)

"""
 get all actions that are currently possible
 @param {*} h history
"""
def getActions(h):
    playersLeft = list(map(lambda a : not a, h.pFolded))
    betsAreEqual = allEqual(list(filter(
        lambda p : True in playersLeft,
        h.pBet
    )))

    highestBet = max(h.pBet)
    currentBet = h.pBet[h.currentPlayer]
    diff = highestBet - currentBet

    hasChips = h.pChips[h.currentPlayer] > diff
    hasFolded = h.pFolded[h.currentPlayer]

    actions = []

    if (hasFolded):
        actions = ["none"]
    else:
        if betsAreEqual:
            actions = ["check"]
            if hasChips:
                actions = actions + ["bet"] #bet2
        else:
            actions = ["fold", "call"]
            if hasChips:
                actions = actions + ["bet"] #bet2
    
    return actions

def doAction(h,action,p):
    ha = History(h)

    ha.depth += 1

    if ha.bettingRound == BETTING_ROUND_PREFLOP:
            ha.preflop = ha.preflop + str(ha.currentPlayer) + action + ","
    elif ha.bettingRound == BETTING_ROUND_FLOP:
            ha.flop = ha.flop + str(ha.currentPlayer) + action + ","
    elif ha.bettingRound == BETTING_ROUND_TURN:
            ha.turn = ha.turn + str(ha.currentPlayer) + action + ","
    elif ha.bettingRound == BETTING_ROUND_RIVER:
            ha.river = ha.river + str(ha.currentPlayer) + action + ","
    elif ha.bettingRound == BETTING_OVER:
            ha.over = ha.over + str(ha.currentPlayer) + action + ","

    ha.pLastAction[p] = action
    
    #do stuff here

    if action == "fold":
            ha.pFolded[ha.currentPlayer] = True;
            ha.log = ha.log + ["Player " + str(ha.currentPlayer) + " folds"];
    elif action == "call":
            #calls the highest bet

            highestBet = max(ha.pBet);
            myBet = ha.pBet[ha.currentPlayer];
            diff = highestBet - myBet;

            ha.pChips[ha.currentPlayer] = ha.pChips[ha.currentPlayer] - diff;
            ha.pBet[ha.currentPlayer] = highestBet;
            ha.pMPIP[ha.currentPlayer] = ha.pMPIP[ha.currentPlayer] + diff;
            ha.log = ha.log + ["Player " + str(ha.currentPlayer) + " calls " + str(diff)];

    elif action == "check":
            ha.log = ha.log + ["Player " + str(ha.currentPlayer) + " checks"];

    elif action == "bet":
            potSize = ha.chips + reduce(lambda a,b : a + b, ha.pBet);

            betSize = potSize;
            if (ha.pChips[ha.currentPlayer] < betSize) :
                betSize = ha.pChips[ha.currentPlayer];

            ha.pChips[ha.currentPlayer] = ha.pChips[ha.currentPlayer] - betSize;
            ha.pMPIP[ha.currentPlayer] = ha.pMPIP[ha.currentPlayer] + betSize;
            ha.pBet[ha.currentPlayer] = betSize;

            ha.log = ha.log + [
            "Player " + str(ha.currentPlayer) + " bets " + str(betSize)
            ];


    ha.currentPlayer = (ha.currentPlayer + 1) % len(PLAYERS);

    return ha

#
# returns number of action based on strategy distribution
#
def randomActionFromStrategy(strategy):
    c= random.random()
    strategySum = 0

    for i in range(len(strategy)):
        strategySum += strategy[i]

        if (c < strategySum):
            return i

def isPreflop(I):
    return len(I['infoSet']) < 10 #to be determined. preflop infoset keys are shorter, but the bettinground is also included in the infoset.

def getActionsFromInfoSet(I):
    #1 get current round actions
    #2 see if they're equal
    return [];

def shuffle(a):
    j = 0
    x = 0
    i = 0
    for i in range(len(a) - 1), i > 0, --i:
        j = math.floor(random.random() * (i + 1))
        x = a[i]
        a[i] = a[j]
        a[j] = x
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


class HistoryMetaClass(type):
    def __getitem__(cls, x):
        return getattr(cls, x)

    def __new__(cls, name, parents, dct):
        dct["__getitem__"] = cls.__getitem__
        return super().__new__(cls, name, parents, dct)


class History(metaclass=HistoryMetaClass):
    def __init__(self, h):
        self.preflop = h['preflop']
        self.flop = h['flop']
        self.turn = h['turn']
        self.river = h['river']
        self.over = h['over']
        self.bettingRound = h['bettingRound']
        self.board = [*h['board']]
        self.chips = h['chips']
        self.pLastAction = [*h['pLastAction']]
        self.pFolded = [*h['pFolded']]
        self.pCards = [*h['pCards']]
        self.pMPIP = [*h['pMPIP']]
        self.pBet = [*h['pBet']]
        self.pChips = [*h['pChips']]
        self.deck = [*h['deck']]
        self.depth = h['depth']
        self.log = h['log']
        self.currentPlayer = h['currentPlayer']
        self.showdown = h['showdown']
        self.winner = h['winner']



def initiateHistory(ms):
    deck = list(map(
        lambda rank : rank + "h",
        ranks
    ))+ list(map(
        lambda rank : rank + "d",
        ranks
    ))+ list(map(
        lambda rank : rank + "c",
        ranks
    ))+ list(map(
        lambda rank : rank + "s",
        ranks
    ))
    #deck = shuffle(unshuffledDeck)
    random.shuffle(deck)
    

    emptyHistory = History({
        'preflop': "",
        'flop': "",
        'turn': "",
        'river': "",
        'over': "",
        'log': [],
        'bettingRound': 0,
        'board': [],
        'chips': 150,
        'pLastAction': list(map(lambda p : None, PLAYERS)),
        'pFolded': list(map(lambda p : False, PLAYERS)),
        'pChips': list(map(lambda p : pChipGet(p), PLAYERS)),
        'pCards': list(map(lambda p : [deck.pop(), deck.pop()], PLAYERS)),
        'pMPIP': list(map(lambda p : pMPIPGet(p), PLAYERS)),
        'pBet': list(map(lambda p : pMPIPGet(p), PLAYERS)),
        'deck': deck[:],
        'depth': 0,
        'currentPlayer': 2 if len(PLAYERS) > 2 else 1,
        'showdown': [],
        'winner': None         
    })

    return emptyHistory

#MCCFR with pruning for very negative regrets
def traverseMCCFR_P(h,p):
    if (isTerminal(h)):
        h2 = calculateWinner(h)
        utility = getUtility(h2,p)
        return utility
    elif not inHand(h,p):
        h0 = doAction(h, "none", p)
        return traverseMCCFR_P(h0, p) #the remaining actions are irrelevant to Player i
    elif needsChanceNode(h):
        ha = nextRound(h)
        return traverseMCCFR_P(ha,p)
    elif h.currentPlayer == p:
        #if history ends with current player to act
        I = getInformationSet(h,p) # the Player i infoset of this node . GET node?
        strategyI = calculateStrategy(I['regretSum'],h) #determine the strategy at this infoset

        v = 0
        va = []
        actions = getActions(h)
        explored = []

        for a in range(len(actions)):
            if (I['regretSum'][a] > C):
                ha = doAction(h,actions[a],p)
                va.append(traverseMCCFR_P(ha,p))
                explored.append(True)
                try:
                    v = v + strategyI[a] * va[a]
                except IndexError:
                    pass
            else:
                explored.append(False)
        
        for a in range(len(actions)):
            if (explored[a] == True):
                newRegret = list(map(
                    lambda r,i : r+va[a]-v if a == i else r,
                    I['regretSum'], [index for index, value in enumerate(I['regretSum'])]
                ))
                node = {**I, 'regretSum': newRegret}
                treeMap[I['infoSet']] = node
        
        return v;
    else:
        Ph = h.currentPlayer
        I = getInformationSet(h,Ph)
        strategy = calculateStrategy(I['regretSum'],h)
        actions = getActions(h)
        chosenAction = randomActionFromStrategy(strategy) #sample an action from the probability distribution
        ha = doAction(h,actions[chosenAction],Ph)

        return traverseMCCFR_P(ha,p)

#
# update the regrets for Player i
#
def traverseMCCFR(h,p):
    if isTerminal(h) == True:
        h2 = calculateWinner(h)
        utility = getUtility(h2,p)
    # if (utility > 0):
    #   print("Terminal with utility", utility, "H", h)
        return utility
    elif not inHand(h,p):
        # print("!inHand")
        h0 = doAction(h, "none", p)
        return traverseMCCFR(h0,p) #the remaining actions are irrelevant to Player i
    elif needsChanceNode(h):
        # print("Needs chance node");
        ha = nextRound(h)
        return traverseMCCFR(ha,p)
    elif h.currentPlayer == p:
        #print("You", p)
        #if history ends with current player to act
        I = getInformationSet(h,p) # the Player i infoset of this node . GET node?
        strategyI = calculateStrategy(I['regretSum'],h) #determine the strategy at this infoset
        v = 0
        va = []
        actions = getActions(h)
        ha = ""

        for a in range(len(actions)):
            ha = doAction(h,actions[a],p)
            va.append(traverseMCCFR(ha,p))
            try:
                v = v + strategyI[a] * va[a]
            except IndexError:
                pass
        
        for a in range(len(actions)):
            newRegret = list(map(
                lambda r,i : r+va[a]-v if a == i else r,
                I['regretSum'], [index for index, value in enumerate(I['regretSum'])]
            ))
            node = {**I, 'regretSum': newRegret}
            treeMap[I['infoSet']] = node
        
        # print("we get here")

        return v
    else:
        Ph = h.currentPlayer
        # print("Player", Ph, "'s turn")
        I = getInformationSet(h,Ph)
        strategyI = calculateStrategy(I['regretSum'], h)
        actions = getActions(h)
        chosenAction = randomActionFromStrategy(strategyI) #sample an action from the probability distribution
        ha = doAction(h, actions[chosenAction], Ph)
        return traverseMCCFR(ha,p)

#
# update the average strategy for Player i
# @param {*} h history
# @param {*} p Player i
#
def updateStrategy(h,p,depth):
    if isTerminal(h) | inHand(h,p)==false | h.bettingRound > 0:
        # print("isTerminal(h) | !inHand(h, p) | h.bettingRound > 0")
        #average strategy only tracked on the first betting round
        return
    elif needsChanceNode(h):
        # print("Needs chance node")
        #sample an action from the chance probabilities
        ha = nextRound(h)
        depth+=1
        updateStrategy(h,p,depth)
    elif h.currentPlayer == p:
        # print("getCurrentPlayer(h)==p")
        #if history ends with current player to act
        I = getInformationSet(h,p) # the Player i infoset of this node . GET node?
        strategyI = calculateStrategy(I['regretSum'],h) #determine the strategy at this infoset
        actions = getActions(h)
        a = randomActionFromStrategy(strategyI) #sample an action from the probability distribution
        actionCounter = I['actionCounter']
        actionCounter[a] = actionCounter[a] + 1

        if actionCounter[a] > 1:
            print("incrementing actioncounter and chancing strategy" +
                  I['infoSet'] +
                  str(actionCounter) +
                  str(strategyI))
        
        treeMap[I['infoSet']] = {**I, 'actionCounter': actionCounter, 'strategy': strategyI} #increment action and add strategy
        ha = doAction(h,actions[a],p)
        depth+=1
        updateStrategy(ha,p,depth)
    else:
        actions = getActions(h)
        # print("ELSE")
        ha = ""
        for a in range(len(actions)):
            ha = doAction(h,actions[a],p)
            depth+=1
            updateStrategy(ha,p,depth) #traverse each action

#
#
# @param {*} R(Ii)
# @param {*} Ii
#
def calculateStrategy(R,h):
    sum = 0
    strategyI = []
    actions = getActions(h)

    for a in range(len(actions)):
        try:
            sum = sum + R[a]
        except IndexError:
            pass
    
    for a in range(len(actions)):
        if sum > 0:
            try:
                strategyI.append(R[a] / sum)
            except IndexError:
                pass
        else:
            strategyI.append(1 / len(actions))
    
    return strategyI

def processKey(key):
    I = treeMap[key]
    if (getCurrentPlayerFromInfoSet(I['infoSet']) == p):
        actions = getActionsFromInfoSet(I)
        regretSum = []
        strategy = []

        for a in range(len(actions)):
            regretSum.append(0)
            if isPreflop(I):
                strategy.append(0) # 𝜙(Ii,a) = 0; not sure if this is correct
        
        treeMap[I['infoSet']] = {**I, 'regretSum': regretSum, 'strategy': strategy}

def processExtra(key):
    I = treeMap[key]
    if (getCurrentPlayerFromInfoSet(I['infoSet']) == p):
        regretSum = list(map(lambda Ra : Ra * d, I['regretSum']))
        strategy = list(map(lambda Sa : Sa * d, I['strategy']))
        treeMap[I['infoSet']] = { **I, 'regretSum': regretSum, 'strategy': strategy}

def MCCFR_P(minutes=1, h=""):
    for p in range(len(PLAYERS)):
        map(lambda key : processKey(key), treeMap.keys())

    start = perf_counter()
    iterations = 0
    t = 0
    while (t / 60  < minutes):
        iterations += 1

        if (iterations % 1000 == 0):
            print("iterations", iterations, "time", round(t))
        
        emptyHistory = initiateHistory(t)

        for p in range(len(PLAYERS)):
            # print("Player", p)
            if t % STRATEGY_INTERVAL == 1:
                updateStrategy(emptyHistory,p,0)
            if t / 60 > PRUNE_THRESHOLD:
                q = random.random()
                if (q < 0.05):
                    traverseMCCFR(emptyHistory,p)
                else:
                    traverseMCCFR_P(emptyHistory,p)
            else:
                traverseMCCFR(emptyHistory,p)
        
        # every 10 minutes, discount regrets and [strategies?] with factor d
        if (t < LCFR_THRESHOLD & round(t/60) % DISCOUNT_INTERVAL == 0):
            m = t / 60
            d = (m / DISCOUNT_INTERVAL) / (m / DISCOUNT_INTERVAL + 1)

            for p in range(len(PLAYERS)):
                map(lambda key : processExtra(key), treeMap.keys())

        t = perf_counter() - start
    
    print("done")
    return 0 # return 𝜙. must be strategy
    
MCCFR_P(60)

# map(lambda I : print(treeMap[I]), treeMap.keys())

print("we have ", len(treeMap.keys()), "entries in the Object")
