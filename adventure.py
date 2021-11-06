import sys
import time
from brownie.network.main import gas_price
import requests
import os
import json
from brownie import *

# User variables. Change these to match your Fantom wallet public address and FTMScan API key (https://ftmscan.com/myapikey)
ADDRESS_USER = "0x31d8204ba31768CB4CfA111B429BDc8F2c6f477b"
FTMSCAN_API_KEY = "8C6RD312AG41JTZK1DK1D4538B6WBJFZBN"

# Contract addresses
SUMMONER_CONTRACT_ADDRESS = "0xce761D788DF608BD21bdd59d6f4B54b2e27F25Bb"
GOLD_CONTRACT_ADDRESS = "0x2069B76Afe6b734Fb65D1d099E7ec64ee9CC76B2"
CELLAR_CONTRACT_ADDRESS = "0x2A0F1cB17680161cF255348dDFDeE94ea8Ca196A"
CRAFTING_CONTRACT_ADDRESS = "0xf41270836dF4Db1D28F7fd0935270e3A603e78cC"
SKILLS_CONTRACT_ADDRESS = "0x6292f3fB422e393342f257857e744d43b1Ae7e70"
ATTRIBUTES_CONTRACT_ADDRESS = "0xB5F5AF1087A8DA62A23b08C00C6ec9af21F397a1"

os.environ["FTMSCAN_TOKEN"] = FTMSCAN_API_KEY

FTMSCAN_API_PARAMS = {
    "module": "account",
    "action": "tokennfttx",
    "contractaddress": SUMMONER_CONTRACT_ADDRESS,
    "address": ADDRESS_USER,
    "apikey": FTMSCAN_API_KEY,
}

# Class Number to Name translation
CLASSES = {
    1: "Barbarian",
    2: "Bard",
    3: "Cleric",
    4: "Druid",
    5: "Fighter",
    6: "Monk",
    7: "Paladin",
    8: "Ranger",
    9: "Rogue",
    10: "Sorcerer",
    11: "Wizard",
}

# Stored numbers on Ethereum-compatible blockchains are integers.
# The default type is padded to 18 decimal place accuracy (floats not used).
# Some on-contract results need to be divided and rounded off to be usable.
DECIMALS = 10 ** 18

DAY = 24 * 60 * 60  # 1 day in seconds


def main():

    global summoners
    summoners = {}

    try:
        global user
        user = accounts.load("rarity")
    except:
        sys.exit(
            "Could not load account!\nVerify that your account is listed using 'brownie accounts list' and that you are using the correct password.\nIf you have not added an account, run 'brownie accounts new rarity' now."
        )

    try:
        network.connect("fantom")
    except:
        sys.exit(
            "Could not connect to the Fantom Mainnet! Verify that brownie lists the Fantom Mainnet using 'brownie networks list'"
        )

    print("\nContracts loaded:")

    global gold_contract
    gold_contract = load_contract(GOLD_CONTRACT_ADDRESS, "Rarity: Gold")

    global summoner_contract
    summoner_contract = load_contract(SUMMONER_CONTRACT_ADDRESS, "Rarity: Summoner")

    global cellar_contract
    cellar_contract = load_contract(CELLAR_CONTRACT_ADDRESS, "Rarity: Cellar")

    global crafting_contract
    crafting_contract = load_contract(CRAFTING_CONTRACT_ADDRESS, "Rarity: Crafting")

    global skills_contract
    skills_contract = load_contract(SKILLS_CONTRACT_ADDRESS, "Rarity: Skills")

    global attributes_contract
    attributes_contract = load_contract(
        ATTRIBUTES_CONTRACT_ADDRESS, "Rarity: Attributes"
    )

    if get_summoners():
        pass
    else:
        sys.exit(
            "No summoners found! Check wallet address, FTMScan API key, and ensure that you already have a summoner"
        )

    # Fill the dictionary with on-chain data
    print("\nSummoners found:")
    for id in summoners.keys():

        summoners[id].update(get_summoner_info(id))
        summoners[id].update(get_summoner_next_xp(summoners[id]["Level"]))
        summoners[id].update(get_cellar_log(id))
        summoners[id].update(get_claimable_gold(id))

        print(
            f'• #{id}: Level {summoners[id]["Level"]} {summoners[id]["Class Name"]} with ({summoners[id]["XP"]} / {summoners[id]["XP_LevelUp"]}) XP'
        )

    # Start the babysitting loop
    print("\nEntering babysitting loop. Triggered events will appear below:")
    while True:

        for id in summoners.keys():

            # Adventure, then update summoner info
            if time.time() > summoners[id]["Adventure Log"]:
                if adventure(summoner_contract, id):
                    # TODO: figure out how long fantom blockchain takes to return accurate data
                    summoners[id]["Adventure Log"] += DAY

            # Level up if XP is sufficient, refresh summoner info, and fetch the new XP_LevelUp
            if summoners[id]["XP"] >= summoners[id]["XP_LevelUp"]:
                if level_up(id):
                    summoners[id]["Level"] += 1
                    summoners[id].update(get_summoner_next_xp(summoners[id]["Level"]))

            # Claim available gold
            if summoners[id]["Claimable Gold"]:
                claim_gold(id)

            # Scout the Cellar and adventure if it will yield
            # a reward. Note some summoners may never be able to enter a
            # dungeon, thus "Cellar Log" will always equal 0.
            # Handle this by resetting it manually every 24 hours
            # to prevent excessive looping
            if time.time() > summoners[id]["Cellar Log"] > 0:
                if cellar_contract.scout.call(id) and adventure(cellar_contract, id):
                    summoners[id]["Cellar Log"] += DAY

        time.sleep(10)


def adventure(contract, id):
    if contract.adventure(id, {"from": user, "gas_price": get_gas()}):
        return True
    else:
        return False


def claim_gold(id):
    if gold_contract.claim(id, {"from": user, "gas_price": get_gas()}):
        return True
    else:
        return False


def get_adventure_log(id):
    return {"Adventure Log": summoner_contract.adventurers_log.call(id)}


def get_cellar_log(id):
    return {"Cellar Log": cellar_contract.adventurers_log.call(id)}


def get_claimable_gold(id):
    return {"Claimable Gold": gold_contract.claimable.call(id) // DECIMALS}


def get_gas():
    response = requests.get(
        "https://gftm.blockscan.com/gasapi.ashx?apikey=key&method=gasoracle"
    )
    if response.status_code == 200 and response.json()["message"] == "OK":
        # Python's int() cannot convert a floating point number
        # stored as a string, so we convert to float first since
        # the API sometimes returns a value with a decimal
        network.gas_price(
            f'{int(float(response.json()["result"]["ProposeGasPrice"]))} gwei'
        )


def get_summoners():
    try:
        response = requests.get(
            "https://api.ftmscan.com/api", params=FTMSCAN_API_PARAMS
        )
        if response.status_code == 200 and response.json()["message"] == "OK":
            # Loop through the JSON object, prepare the summoners dictionary
            # keys to match the unique "tokenID" for our summoners
            for metadata in response.json()["result"]:
                # Prepare empty sub-dictionaries
                summoners[int(metadata["tokenID"])] = {}
        return True
    except:
        return False


def get_summoner_info(id):
    # The summoner contract call will return a tuple of summoner info of
    # form (XP, Log, ClassNumber, Level). "Log" is a unix timestamp for
    # the next available adventure
    tx = summoner_contract.summoner.call(id)
    return {
        "XP": tx[0] // DECIMALS,
        "Adventure Log": tx[1],
        "Class Name": CLASSES[tx[2]],
        "Level": tx[3],
    }


def get_summoner_next_xp(level):
    return {"XP_LevelUp": summoner_contract.xp_required.call(level) // DECIMALS}


def level_up(id):
    if summoner_contract.level_up(id, {"from": user, "gas_price": get_gas()}):
        return True
    else:
        return False


def load_contract(address, alias):
    # Attempts to load the saved contract.
    # If not found, fetch from FTM network explorer and save.
    try:
        contract = Contract(alias)
    except ValueError:
        contract = Contract.from_explorer(address, owner=user)
        contract.set_alias(alias)
    finally:
        print(f"• {alias}")
        return contract


# Only executes main loop if this file is called directly
if __name__ == "__main__":
    main()
