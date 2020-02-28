# Pluribus

Implementation of Pluribus, a Superhuman AI for 6-MAX No-Limit Holdem Poker Bot based on Supplementary Material https://science.sciencemag.org/highwire/filestream/728919/field_highwire_adjunct_files/0/aay2400-Brown-SM.pdf from the paper, "Superhuman AI for multiplayer poker" by Noam Brown and Tuomas Sandholm 

# Goal 

I am interested in Bodog.eu for the time being because of its HTML5 Client accessible with only a browser. This is infinitely easier than forcing people to run a Virtualized instance of a Poker software client which is actively hostile to any sort of automation. Our aim is to create a simple Chrome Extension which will monitor a Bodog.eu 6-MAX NL Holdem Poker game during real-time depth limited search that will be performed on an AWS EC2 r5a.16xlarge instance with 64 cores and 512GB of memory.

  1. Solver: Translating the pseudo code and deploying it successfully on AWS. Returns solution showing the action to take.

  2. Parser: Computer vision to parse screenshots of Bodog.eu game for the purpose of extracting current game state.
  
  3. Client: Chrome Extension which upon click will upload the game screenshot to be parsed and solved.
  
  
 ## 1. Solver (wIP)
 
 The code is a port of @EAT-CODE-KITE-REPEAT's javascript implementation. For Python, I decided to use the Deuces library, however, it has not been tested. 
 
 ## 2. Parser (WIP):
 
 Seems like Bodog.eu uses an HTML5 renderer so will not require any computer vision. 
 
 ## 3. Client (WIP)
  
 

