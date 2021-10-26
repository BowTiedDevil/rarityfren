import sys
import json
import pprint
import time
import requests
import math
from brownie import *

# User variables. Change these to match your Fantom wallet public address and FTMScan API key (https://ftmscan.com/myapikey)
ADDRESS_USER = "0x31d8204ba31768CB4CfA111B429BDc8F2c6f477b"
ETHERSCAN_API_KEY = "8C6RD312AG41JTZK1DK1D4538B6WBJFZBN"

# Contract and API variables - do not change!
ADDRESS_RARITY_CONTRACT = "0xce761D788DF608BD21bdd59d6f4B54b2e27F25Bb"
FTMSCAN_API_PARAMS = {
    "module": "account",
    "action": "tokennfttx",
    "contractaddress": ADDRESS_RARITY_CONTRACT,
    "address": ADDRESS_USER,
    "apikey": ETHERSCAN_API_KEY,
}

# Classes Number/Name dictionary
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

DECIMALS = 10 ** 18


def main():
    # Initialize a blank summoners dictionary
    summoners = {}

    user = accounts.load("rarityuser", password="")
    network.connect("ftm-main")

    # Attempt to load the saved rarity contract. If not found, fetch from FTM network explorer
    try:
        rarity_contract = Contract("rarity")
    except ValueError:
        rarity_contract = Contract.from_explorer(ADDRESS_RARITY_CONTRACT, owner=user)
        rarity_contract.set_alias("rarity")

    if get_summoners(summoners):
        print(f"Found {len(summoners)} summoners:")
    else:
        sys.exit(
            "No summoners found! Check wallet address, FTMScan API key, and ensure that you already have a summoner"
        )

    # Fill the dictionary with on-chain data
    for id in summoners.keys():
        summoners[id] = get_summoner_info(rarity_contract, id)
        summoners[id]["XP_LevelUp"] = get_summoner_next_level_xp(
            rarity_contract, summoners[id]["Level"]
        )
        print(
            f'• Summoner #{id}: Level {summoners[id]["Level"]} {summoners[id]["ClassName"]} with ({summoners[id]["XP"]} / {summoners[id]["XP_LevelUp"]}) XP'
        )

    # Start the daycare loop
    while True:
        loop_timer = math.ceil(time.time())

        # Send our summoners on adventures
        for id in summoners.keys():
            # Only adventure when ready
            if loop_timer > summoners[id]["Log"]:
                adventure(rarity_contract, id)
                # refresh summoner info
                summoners[id] = get_summoner_info(rarity_contract, id)
                summoners[id]["XP_LevelUp"] = get_summoner_next_level_xp(
                    rarity_contract, summoners[id]["Level"]
                )

        # Level up
        for id in summoners.keys():
            # Level up when ready
            if summoners[id]["XP"] >= summoners[id]["XP_LevelUp"]:
                level_up(rarity_contract, id)
                # refresh summoner info
                summoners[id] = get_summoner_info(rarity_contract, id)
                summoners[id]["XP_LevelUp"] = get_summoner_next_level_xp(
                    rarity_contract, summoners[id]["Level"]
                )

        # Repeat loop
        time.sleep(5)


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
        tx = contract.summoner(id)
        if tx[3]:
            return {
                "XP": int(tx[0] / DECIMALS),
                "Log": tx[1],
                "ClassNumber": tx[2],
                "ClassName": CLASSES[tx[2]],
                "Level": tx[3],
            }
        else:
            time.sleep(5)


def get_summoner_next_level_xp(contract, level):
    # Sometimes the contract call to the 'xp_required' method will return a zero, so loop until it returns real results
    while True:
        if tx := contract.xp_required(level):
            return int(tx / DECIMALS)
        else:
            time.sleep(5)


def adventure(contract, id):
    print(f"Adventuring with summoner #{id}")
    tx = contract.adventure(id)


def level_up(contract, id):
    print(f"Leveling up summoner #{id}")
    if tx := contract.level_up(id):
        print(f'New Level: {tx.events["leveled"]["level"]}')
        return tx.events["leveled"]["level"]
    else:
        return 0


if __name__ == "__main__":
    main()
