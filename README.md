# rarityfren

## DISCLAIMER!
This Python script will spend FTM from your wallet in an automatic way. The script may have bugs and spend all of your FTM! I **highly** recommend setting up a dedicated wallet for this and keeping a low FTM balance in there (sufficient for adventuring but not your life savings)

---

## Features
RarityFren automates many tedious tasks associated with playing [Rarity](https://andrecronje.medium.com/loot-rarity-d341faa4485c) by Andre Cronje. Including:
- Adventuring once a day
- Leveling Up
- Claiming Gold
- Scouting and completing the entry-level [Cellar Dungeon](https://andrecronje.medium.com/rarity-the-cellar-83a1606a0be3)

RarityFren interacts with the smart contracts published on Fantom directly, and does not interact with any outside "helper" contracts. You maintain control of your keys the whole time, thus it is non-custodial.

## Prerequisites
- Python 3
- Package Installer for Python (`pip`)

## Installation
- (optional) Inside the `rarityfren` directory, create a virtual environment using `python3 -m venv .venv`, then activate it with `source .venv/bin/activate`
- Install the necessary Python packages by executing pip3 -r requirements.txt`

## Brownie Setup
- Create a dedicated account on the console using `brownie accounts new`, enter the private key from your Metamask wallet (or similar). Edit the `ADDRESS_USER` value in `adventure.py` to match the public address.
- Create a [FTMScan API Key](https://ftmscan.com/myapikey) and save it to the `FTMSCAN_API_KEY` variable. 
- Create a dedicated network for interacting with the Fantom blockchain by entering the following:
`brownie networks add "Fantom" fantom chainid=250 host=https://rpc.ftm.tools explorer=https://api.ftmscan.com/api`
**Note** Brownie comes with a built-in Fantom network labeled "ftm-main", which is outdated and often returns bad data when queried.

## Basic Use
- (optional) activate your virtual environment
- Run `python3 adventure.py`, unlock brownie account data using password, and watch your summoners go on their adventures

## TO-DO
- Add maximum gas flag
- Load user's address and API key from env instead of hard-coding
- Refactor functions, adventure.py is getting too big
- Add expansion contracts
- Explore automation of crafting, skills, and attribute increases
- Add [Rarity Open Mic](https://rarity-openmic.com/)
- Add [RarityForest](https://github.com/TheAustrian1998/theRarityForest)