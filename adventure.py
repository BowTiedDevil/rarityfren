import sys
import json
import pprint
import time
import requests
import math
from brownie import *

# User variables. Change these to match your Fantom wallet public address and FTMScan API key (https://ftmscan.com/myapikey)
ADDRESS_USER = "0x31d8204ba31768CB4CfA111B429BDc8F2c6f477b"
FTMSCAN_API_KEY = "8C6RD312AG41JTZK1DK1D4538B6WBJFZBN"

# Contract addresses - do not change!
SUMMONER_CONTRACT_ADDRESS = "0xce761D788DF608BD21bdd59d6f4B54b2e27F25Bb"
GOLD_CONTRACT_ADDRESS = "0x2069B76Afe6b734Fb65D1d099E7ec64ee9CC76B2"

FTMSCAN_API_PARAMS = {
    "module": "account",
    "action": "tokennfttx",
    "contractaddress": SUMMONER_CONTRACT_ADDRESS,
    "address": ADDRESS_USER,
    "apikey": FTMSCAN_API_KEY,
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

    try:
        user = accounts.load("rarity")
    except:
        sys.exit(
            "Could not load account!\nVerify that your account is listed using 'brownie accounts list' and that you are using the correct password.\nIf you have not added an account, run 'brownie accounts new rarity' now."
        )

    try:
        network.connect("ftm-main")
    except:
        sys.exit(
            "Could not connect to the Fantom Mainnet! Verify that brownie lists the Fantom Mainnet using 'brownie networks list'"
        )

    print("Contracts loaded:")

    # Attempt to load the saved rarity contract. If not found, fetch from FTM network explorer
    try:
        summoner_contract = Contract("rarity-summoner")
    except ValueError:
        summoner_contract = Contract.from_explorer(
            SUMMONER_CONTRACT_ADDRESS, owner=user
        )
        summoner_contract.set_alias("rarity-summoner")
    finally:
        print("• Rarity Summoner")

    # Attempt to load the saved rarity gold contract. If not found, fetch from FTM network explorer
    try:
        gold_contract = Contract("rarity-gold")
    except ValueError:
        gold_contract = Contract.from_explorer(GOLD_CONTRACT_ADDRESS, owner=user)
        gold_contract.set_alias("rarity-gold")
    finally:
        print("• Rarity Gold")

    if get_summoners(summoners):
        pass
    else:
        sys.exit(
            "No summoners found! Check wallet address, FTMScan API key, and ensure that you already have a summoner"
        )

    # Fill the dictionary with on-chain data
    print("Summoners found:")
    for id in summoners.keys():
        summoners[id] = get_summoner_info(summoner_contract, id)
        summoners[id]["XP_LevelUp"] = get_summoner_next_level_xp(
            summoner_contract, summoners[id]["Level"]
        )
        print(
            f'• #{id}: Level {summoners[id]["Level"]} {summoners[id]["ClassName"]} with ({summoners[id]["XP"]} / {summoners[id]["XP_LevelUp"]}) XP'
        )

    # Start the babysitting loop
    print(
        "\nEntering babysitting loop. Adventure, LevelUp, and ClaimGold messages will appear below when triggered."
    )
    while True:
        loop_timer = math.ceil(time.time())

        for id in summoners.keys():
            # Only adventure when ready
            if loop_timer > summoners[id]["Log"]:
                print(f"[Adventure] Sending Summoner {id} on adventure")
                adventure(summoner_contract, id, user)
                # refresh summoner info
                summoners[id] = get_summoner_info(summoner_contract, id)
                summoners[id]["XP_LevelUp"] = get_summoner_next_level_xp(
                    summoner_contract, summoners[id]["Level"]
                )

            # Level up if XP is sufficient
            if summoners[id]["XP"] >= summoners[id]["XP_LevelUp"]:
                print(f"[LevelUp] Summoner {id}")
                level_up(summoner_contract, id, user)

                # refresh summoner info
                summoners[id] = get_summoner_info(summoner_contract, id)
                summoners[id]["XP_LevelUp"] = get_summoner_next_level_xp(
                    summoner_contract, summoners[id]["Level"]
                )

                # claim gold
                print(f"[ClaimGold] Claiming gold for Summoner {id}")
                claim_gold(gold_contract, id, user)

        # Repeat loop every second
        time.sleep(1)


def claim_gold(contract, id, user):
    while True:
        try:
            contract.claim(id, {"from": user})
            break
        except ValueError:
            # tx will fail as gas price fluctuates, so passing will loop until success
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
                "Log": tx[1],
                "ClassNumber": tx[2],
                "ClassName": CLASSES[
                    tx[2]
                ],  # translates ClassNumber to ClassName using CLASSES dictionary
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
            # tx will fail as gas price fluctuates, so passing will loop until success
            pass


def level_up(contract, id, user):
    while True:
        try:
            contract.level_up(id, {"from": user})
            break
        except ValueError:
            # tx will fail as gas price fluctuates, so passing will loop until success
            pass


if __name__ == "__main__":
    main()
