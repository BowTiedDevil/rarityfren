# rarityfren

## DISCLAIMER
This Python script will spend FTM from your wallet in an automatic way. The script may have bugs and spend all of your FTM! I **highly** recommend setting up a dedicated wallet for this and keeping a low FTM balance in there (sufficient for adventuring but not your life savings)

## Package prerequisites
* Python 3
* Python Packages (installed with `pip install [packagename]`)
    - requests
    - eth-brownie

## Brownie Setup
- Create a dedicated account on the console using `brownie accounts new`, enter the private key from your Metamask wallet (or similar). Edit the `ADDRESS_USER` value in `adventure.py` to match the public address.
- Create a dedicated network for interacting with the Fantom blockchain by entering the following:
`brownie networks add "Fantom" fantom chainid=250 host=https://rpc.ftm.tools explorer=https://ftmscan.com/api`
**Note** Brownie comes with a built-in Fantom network labeled "ftm-main", which is outdated and often returns bad data when queried.

## Basic Use
Run `python3 adventure.py`, unlock brownie account data using password, watch your summoners go on their adventures

## TO-DO
- Load address and API keys from env instead of hard-coding
- Add try/except error handling for all contract calls
- Refactor functions, adventure.py is getting too big
- Add expansion contracts
- Automate crafting
- Automate dungeons
- Automate skills