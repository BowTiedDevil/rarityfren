import sys
import json
import pprint
import time
import requests
import os
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

DAY = 24 * 60 * 60  # 1 day in seconds
DECIMALS = 10 ** 18


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
        summoners[id] = get_summoner_info(summoner_contract, id)
        summoners[id]["XP_LevelUp"] = get_summoner_next_level_xp(
            summoner_contract, summoners[id]["Level"]
        )
        summoners[id]["Cellar Log"] = get_adventure_log(cellar_contract, id, user)

        if summoners[id]["Cellar Log"] == 0:
            summoners[id]["Cellar Log"] = time.time()

        print(
            f'• #{id}: Level {summoners[id]["Level"]} {summoners[id]["ClassName"]} with ({summoners[id]["XP"]} / {summoners[id]["XP_LevelUp"]}) XP.'
        )

    # Start the babysitting loop
    print("\nEntering babysitting loop. Triggered events will appear below:")
    while True:

        for id in summoners.keys():

            # Adventure when ready
            if time.time() > summoners[id]["Adventure Log"]:
                print(f"[Adventure] {id}")
                adventure(summoner_contract, id, user)
                # refresh summoner info
                summoners[id] = get_summoner_info(summoner_contract, id)
                summoners[id]["XP_LevelUp"] = get_summoner_next_level_xp(
                    summoner_contract, summoners[id]["Level"]
                )

            # Level up if XP is sufficient
            if summoners[id]["XP"] >= summoners[id]["XP_LevelUp"]:
                print(f"[LevelUp] {id}")
                level_up(summoner_contract, id, user)

                # Refresh summoner info
                print(f"[Refresh] {id}")
                summoners[id] = get_summoner_info(summoner_contract, id)
                summoners[id]["XP_LevelUp"] = get_summoner_next_level_xp(
                    summoner_contract, summoners[id]["Level"]
                )

                # Claim gold after successful level_up
                print(f"[ClaimGold] {id}")
                claim_gold(gold_contract, id, user)

            # print(summoners[id]["Cellar Log"])
            # Scout the Cellar dungeon and adventure if ready
            # if time.time() > summoners[id]["Cellar Log"]:
            #     # only adventure if we expect a reward
            #     if cellar_contract.scout.call(id) != 0:
            #         print(f"[Cellar] {id}")
            #         adventure(cellar_contract, id, user)
            #         # update adventurer log for this dungeon
            #         print(f"[Refresh] Summoner #{id}")
            #         summoners[id]["Cellar Log"] = get_adventure_log(
            #             cellar_contract, id, user
            #         )
            #     # otherwise we reset the log manually and try again in 24 hours
            #     else:
            #         summoners[id]["Cellar Log"] = time.time() + DAY

        # Repeat loop
        time.sleep(1)


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
    # Sometimes the contract call to the 'summoner' method will return all zeros, so loop until it returns real results
    while True:
        tx = contract.summoner.call(id)
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
            time.sleep(5)


def get_summoner_next_level_xp(contract, level):
    # Sometimes the contract call to the 'xp_required' method will return a zero, so loop until it returns real results
    while True:
        if tx := contract.xp_required.call(level):
            return int(tx / DECIMALS)
        else:
            pass


def adventure(contract, id, user):
    while True:
        try:
            contract.adventure(id, {"from": user})
            break
        except ValueError:
            # tx might fail, so passing will continue the loop until success
            pass


def level_up(contract, id, user):
    while True:
        try:
            contract.level_up(id, {"from": user})
            break
        except ValueError:
            # tx might fail, so passing will continue the loop until success
            pass


def get_adventure_log(contract, id, user):
    while True:
        try:
            return contract.adventurers_log.call(id, {"from": user})
        except ValueError:
            # call might fail, so passing will continue the loop until success
            pass


def load_contract(address, alias, user):
    # Attempt to load the saved contract. If not found, fetch from FTM network explorer
    try:
        contract = Contract(alias)
    except ValueError:
        contract = Contract.from_explorer(address, owner=user)
        contract.set_alias(alias)
    finally:
        print(f"• {alias}")
        return contract


if __name__ == "__main__":
    main()
