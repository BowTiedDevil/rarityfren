import sys
import time
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

        if result := get_summoner_info(summoner_contract, id):
            summoners[id].update(result)

        if result := get_summoner_next_xp(summoner_contract, summoners[id]["Level"]):
            summoners[id].update(result)

        if result := get_cellar_log(cellar_contract, id):
            summoners[id].update(result)

        print(
            f'• #{id}: Level {summoners[id]["Level"]} {summoners[id]["ClassName"]} with ({summoners[id]["XP"]} / {summoners[id]["XP_LevelUp"]}) XP'
        )

    loop_counter = 0

    # Start the babysitting loop
    print("\nEntering babysitting loop. Triggered events will appear below:")
    while True:

        for id in summoners.keys():

            # Adventure when ready
            if time.time() > summoners[id]["Adventure Log"]:
                print(f'[Adventure] #{id} ({summoners[id]["ClassName"]})')
                if adventure(summoner_contract, id, user):
                    # Refresh summoner info
                    if result := get_summoner_info(summoner_contract, id):
                        summoners[id].update(result)
                    if result := get_summoner_next_xp(
                        summoner_contract, summoners[id]["Level"]
                    ):
                        summoners[id].update(result)

            # Level up if XP is sufficient, then refresh summoner
            # info, fetch the new XP_LevelUp, and claim available gold
            if summoners[id]["XP"] >= summoners[id]["XP_LevelUp"]:
                print(f'[LevelUp] #{id} ({summoners[id]["ClassName"]})')
                if level_up(summoner_contract, id, user):
                    # Refresh summoner info
                    if result := get_summoner_info(summoner_contract, id):
                        summoners[id].update(result)
                    if result := get_summoner_next_xp(
                        summoner_contract, summoners[id]["Level"]
                    ):
                        summoners[id].update(result)
                    # Claim gold after successful level_up
                    if claim_gold(gold_contract, id, user):
                        print(f'[ClaimGold] #{id} ({summoners[id]["ClassName"]})')

            if time.time() > summoners[id]["Cellar Log"]:
                # Scout the Cellar dungeon and adventure if it will yield
                # a reward. Note some summoners may never be able to enter a
                # dungeon, thus "Cellar Log" will always equal 0.
                # Handle this by resetting it manually every 24 hours
                # to prevent excessive looping
                if cellar_contract.scout.call(id):
                    print(f'[Cellar] #{id} ({summoners[id]["ClassName"]})')
                    if adventure(cellar_contract, id, user):
                        summoners[id].update(get_cellar_log(cellar_contract, id))
                else:
                    summoners[id]["Cellar Log"] = time.time() + DAY

        # Display "..." progress text to indicate the script is working
        while True:
            if loop_counter == 0:
                print("   \r", end="", flush=True)
                loop_counter += 1
                break
            if loop_counter == 1:
                print(".  \r", end="", flush=True)
                loop_counter += 1
                break
            if loop_counter == 2:
                print(".. \r", end="", flush=True)
                loop_counter += 1
                break
            if loop_counter == 3:
                print("...\r", end="", flush=True)
                loop_counter = 0
                break

        # Sleep before repeating loop
        time.sleep(1)


def adventure(contract, id, user):
    try:
        contract.adventure(id, {"from": user, "gas_price": f"{get_gas()} gwei"})
        return True
    except ValueError:
        #        return False
        raise


def claim_gold(contract, id, user):
    try:
        contract.claim(id, {"from": user, "gas_price": f"{get_gas()} gwei"})
        return True
    except ValueError:
        return False


def get_adventure_log(contract, id, user):
    try:
        tx = contract.adventurers_log.call(
            id, {"from": user, "gas_price": f"{get_gas()} gwei"}
        )
        return {"Adventure Log": tx}
    except ValueError:
        return False


def get_gas():
    try:
        response = requests.get(
            "https://gftm.blockscan.com/gasapi.ashx?apikey=key&method=gasoracle"
        )
        if response.status_code == 200 and response.json()["message"] == "OK":
            # Python's int() cannot convert a floating point number stored as a string, so we convert to float first
            # since API sometimes returns a gas value with a decimal
            return int(float(response.json()["result"]["ProposeGasPrice"]))
    except:
        return False


def get_summoners(summoners):
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


def get_summoner_info(contract, id):
    # The summoner contract call will return a tuple of summoner info of
    # form (XP, Log, ClassNumber, Level). "Log" is a unix timestamp for
    # the next available adventure
    tx = contract.summoner.call(id)
    if tx[3]:
        return {
            "XP": tx[0] // DECIMALS,
            "Adventure Log": tx[1],
            "ClassName": CLASSES[
                tx[2]
            ],  # translates to ClassName using CLASSES dictionary
            "Level": tx[3],
        }
    else:
        return False


def get_summoner_next_xp(contract, level):
    try:
        tx = contract.xp_required.call(level)
        return {"XP_LevelUp": tx // DECIMALS}
    except ValueError:
        return False


def get_cellar_log(contract, id):
    try:
        tx = contract.adventurers_log.call(
            id,
        )
        return {"Cellar Log": tx}
    except ValueError:
        return False


def level_up(contract, id, user):
    try:
        contract.level_up(id, {"from": user, "gas_price": f"{get_gas()} gwei"})
        return True
    except ValueError:
        return False


def load_contract(address, alias, user):
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
