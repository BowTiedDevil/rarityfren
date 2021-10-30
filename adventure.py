import sys
import time
import requests
import os
import json
from brownie import *

# User variables. Change these to match your Fantom wallet public address and FTMScan API key (https://ftmscan.com/myapikey)
ADDRESS_USER = "0x31d8204ba31768CB4CfA111B429BDc8F2c6f477b"
FTMSCAN_API_KEY = "8C6RD312AG41JTZK1DK1D4538B6WBJFZBN"

# Contract addresses - do not change!
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
    # Initialize a blank summoners dictionary
    summoners = {}

    try:
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

    gold_contract = load_contract(GOLD_CONTRACT_ADDRESS, "Rarity: Gold", user)
    summoner_contract = load_contract(
        SUMMONER_CONTRACT_ADDRESS, "Rarity: Summoner", user
    )
    cellar_contract = load_contract(CELLAR_CONTRACT_ADDRESS, "Rarity: Cellar", user)
    crafting_contract = load_contract(
        CRAFTING_CONTRACT_ADDRESS, "Rarity: Crafting", user
    )
    skills_contract = load_contract(SKILLS_CONTRACT_ADDRESS, "Rarity: Skills", user)
    attributes_contract = load_contract(
        ATTRIBUTES_CONTRACT_ADDRESS, "Rarity: Attributes", user
    )

    if get_summoners(summoners):
        pass
    else:
        sys.exit(
            "No summoners found! Check wallet address, FTMScan API key, and ensure that you already have a summoner"
        )

    # Fill the dictionary with on-chain data
    print("\nSummoners found:")
    for id in summoners.keys():
        summoners[id].update(get_summoner_info(summoner_contract, id))
        summoners[id].update(
            get_summoner_next_level_xp(summoner_contract, summoners[id]["Level"])
        )
        summoners[id].update(get_cellar_log(cellar_contract, id, user))
        print(
            f'• #{id}: Level {summoners[id]["Level"]} {summoners[id]["ClassName"]} with ({summoners[id]["XP"]} / {summoners[id]["XP_LevelUp"]}) XP'
        )

    # Start the babysitting loop
    print("\nEntering babysitting loop. Triggered events will appear below:")
    while True:

        for id in summoners.keys():

            # Adventure when ready
            if time.time() > summoners[id]["Adventure Log"]:
                print(f'[Adventure] #{id} ({summoners[id]["ClassName"]})')
                adventure(summoner_contract, id, user)
                # Refresh summoner info
                summoners[id].update(get_summoner_info(summoner_contract, id))
                summoners[id].update(
                    get_summoner_next_level_xp(
                        summoner_contract, summoners[id]["Level"]
                    )
                )

            # Level up if XP is sufficient
            if summoners[id]["XP"] >= summoners[id]["XP_LevelUp"]:
                print(f'[LevelUp] #{id} ({summoners[id]["ClassName"]})')
                level_up(summoner_contract, id, user)

                # Refresh summoner info
                summoners[id].update(get_summoner_info(summoner_contract, id))
                summoners[id].update(
                    get_summoner_next_level_xp(
                        summoner_contract, summoners[id]["Level"]
                    )
                )

                # Claim gold after successful level_up
                print(f'[ClaimGold] #{id} ({summoners[id]["ClassName"]})')
                claim_gold(gold_contract, id, user)

            # Scout the Cellar dungeon
            if time.time() > summoners[id]["Cellar Log"]:
                # Adventure if the dungeon will yield a reward
                if cellar_contract.scout.call(id):
                    print(f'[Cellar] #{id} ({summoners[id]["ClassName"]})')
                    adventure(cellar_contract, id, user)
                    summoners[id].update(get_cellar_log(cellar_contract, id, user))
                # Otherwise we reset the log manually and try again in 24 hours (prevents excessive calls on every loop)
                else:
                    summoners[id]["Cellar Log"] = time.time() + DAY

        # Sleep before repeating loop
        time.sleep(10)


def claim_gold(contract, id, user):
    while True:
        try:
            contract.claim(id, {"from": user})
            break
        except ValueError:
            # tx call might fail, so passing will continue the loop until success
            pass


def get_summoners(summoners):
    while True:
        if (
            response := requests.get(
                "https://api.ftmscan.com/api", params=FTMSCAN_API_PARAMS
            )
        ).status_code == 200:
            # Loop through the JSON object, prepare the summoners dictionary with keys set from unique "tokenID"
            for metadata in response.json()["result"]:
                # Store dictionary key as integer
                summoners[int(metadata["tokenID"])] = {}
            return len(summoners)
        else:
            time.sleep(5)


def get_summoner_info(contract, id):
    while True:
        tx = contract.summoner.call(id)  # returns tuple (XP, Log, ClassNumber, Level)
        if tx[3]:
            return {
                "XP": int(tx[0] / DECIMALS),
                "Adventure Log": tx[1],
                "ClassName": CLASSES[
                    tx[2]
                ],  # translates to ClassName using CLASSES dictionary
                "Level": tx[3],
            }
        else:
            pass


def get_summoner_next_level_xp(contract, level):
    while True:
        if tx := contract.xp_required.call(level):
            return {"XP_LevelUp": int(tx / DECIMALS)}
        else:
            pass  # tx might fail, so passing will continue the loop until success


def adventure(contract, id, user):
    while True:
        try:
            contract.adventure(id, {"from": user})
            break
        except ValueError:
            pass  # tx might fail, so passing will continue the loop until success


def level_up(contract, id, user):
    while True:
        try:
            contract.level_up(id, {"from": user})
            break
        except ValueError:
            pass  # tx might fail, so passing will continue the loop until success


def get_adventure_log(contract, id, user):
    while True:
        try:
            tx = contract.adventurers_log.call(id, {"from": user})
            return {"Adventure Log": tx}
        except ValueError:
            pass  # call might fail, so passing will continue the loop until success


def get_cellar_log(contract, id, user):
    while True:
        try:
            tx = contract.adventurers_log.call(id, {"from": user})
            return {"Cellar Log": tx}
        except ValueError:
            pass  # call might fail, so passing will continue the loop until success


def load_contract(address, alias, user):
    # Attempts to load the saved contract. If not found, fetch from FTM network explorer
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
