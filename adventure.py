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

WEI_PER_GWEI = 10 ** 9

MINIMUM_CONFIRMATION_TIME = (
    10  # How long to wait (in seconds) after a successful confirmation
)

GAS_BUFFER = 1.1  # Add 10% to value found in get_gas()


def main():

    global summoners
    summoners = {}

    try:
        global user
        user = accounts.load("rarity")
    except:
        sys.exit(
            "Could not load account! Verify that your account is listed using 'brownie accounts list' and that you are using the correct password. If you have not added an account, run 'brownie accounts new rarity' now."
        )

    try:
        network.connect("fantom")
    except:
        sys.exit(
            "Could not connect to the Fantom Mainnet! Verify that brownie lists the Fantom Mainnet using 'brownie networks list'"
        )

    print("\nContracts loaded:")

    global gold_contract
    gold_contract = contract_load(GOLD_CONTRACT_ADDRESS, "Rarity: Gold")

    global summoner_contract
    summoner_contract = contract_load(SUMMONER_CONTRACT_ADDRESS, "Rarity: Summoner")

    global cellar_contract
    cellar_contract = contract_load(CELLAR_CONTRACT_ADDRESS, "Rarity: Cellar")

    global crafting_contract
    crafting_contract = contract_load(CRAFTING_CONTRACT_ADDRESS, "Rarity: Crafting")

    global skills_contract
    skills_contract = contract_load(SKILLS_CONTRACT_ADDRESS, "Rarity: Skills")

    global attributes_contract
    attributes_contract = contract_load(
        ATTRIBUTES_CONTRACT_ADDRESS, "Rarity: Attributes"
    )

    if account_get_summoners():
        pass
    else:
        sys.exit(
            "No summoners found! Check wallet address, FTMScan API key, and ensure that you already have a summoner"
        )

    # Fill the dictionary with on-chain data
    print("\nSummoners found:")
    for id in summoners.keys():

        summoners[id].update(summoner_get_stats(id))
        summoners[id].update(summoner_get_next_xp(summoners[id]["Level"]))
        summoners[id].update(cellar_get_log(id))
        summoners[id].update(gold_get_claimable(id))

        print(
            f'• #{id}: Level {summoners[id]["Level"]} {summoners[id]["Class Name"]} ({summoners[id]["XP"]} / {summoners[id]["XP_LevelUp"]} XP)'
        )

    print("\nEntering babysitting loop. Triggered events will appear below:\n")

    # Start of babysitting loop
    while True:

        for id in summoners.keys():

            # Adventure, then update summoner info
            if time.time() > summoners[id]["Adventure Log"] and adventure_summoner(id):
                summoners[id].update(summoner_get_stats(id))

            # Level up if XP is sufficient, refresh summoner info, fetch the new XP_LevelUp, and
            # check for claimable gold
            if summoners[id]["XP"] >= summoners[id]["XP_LevelUp"] and summoner_level_up(
                id
            ):
                summoners[id].update(summoner_get_stats(id))
                summoners[id].update(summoner_get_next_xp(summoners[id]["Level"]))
                summoners[id].update(gold_get_claimable(id))

            # Claim gold if we've just leveled up (XP == 0) and the contract shows a positive
            # balance ready to claim
            if (
                summoners[id]["XP"] == 0
                and summoners[id]["Claimable Gold"]
                and gold_claim(id)
            ):
                summoners[id].update(gold_get_claimable(id))

            # Scout the Cellar and adventure if it will yield
            # a reward. Note some summoners may never be able to enter a
            # dungeon, thus "Cellar Log" will always equal 0.
            # Handle this by resetting it manually every 24 hours
            # to prevent excessive looping
            if (
                time.time() > summoners[id]["Cellar Log"]
                and cellar_contract.scout.call(id)
                and adventure_cellar(id)
            ):
                summoners[id].update(cellar_get_log(id))

        time.sleep(1)
        # End of babysitting loop


def account_get_balance():
    """Return account balance in gwei"""
    return user.balance() / WEI_PER_GWEI


def account_get_summoners():
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


def adventure_cellar(id):
    try:
        gas_price = get_gas_price()
        estimate = cellar_contract.adventure.estimate_gas(
            id, {"from": user, "gas_price": gas_price}
        )
    except Exception as e:
        print("Could not estimate gas!")
        print(f"Exception: {e}")
        return False

    if (user.balance() / WEI_PER_GWEI) >= estimate:
        try:
            cellar_contract.adventure(id, {"from": user, "gas_price": gas_price})
            time.sleep(MINIMUM_CONFIRMATION_TIME)
            return True
        except ValueError:
            print("Transaction failed!")
            return False
    else:
        print("Insufficent account balance to send transaction")
        return False


def adventure_get_log(id):
    return {"Adventure Log": summoner_contract.adventurers_log.call(id)}


def adventure_summoner(id):
    try:
        gas_price = get_gas_price()
        estimate = summoner_contract.adventure.estimate_gas(
            id, {"from": user, "gas_price": gas_price}
        )
    except Exception as e:
        print("Could not estimate gas!")
        print(f"Exception: {e}")
        return False

    if (user.balance() / WEI_PER_GWEI) >= estimate:
        try:
            summoner_contract.adventure(id, {"from": user, "gas_price": gas_price})   
            time.sleep(MINIMUM_CONFIRMATION_TIME)
            return True
        except Exception as e:
            print(f"Exception: {e}")
            return False
    else:
        print("Insufficent account balance to send transaction")
        return False


def cellar_get_log(id):
    return {"Cellar Log": cellar_contract.adventurers_log.call(id)}


def contract_load(address, alias):
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


def gold_claim(id):
    try:
        gas_price = get_gas_price()
        estimate = gold_contract.claim.estimate_gas(
            id, {"from": user, "gas_price": gas_price}
        )
    except Exception as e:
        print("Could not estimate gas!")
        print(f"Exception: {e}")
        return False

    if (user.balance() / WEI_PER_GWEI) >= estimate:
        try:
            gold_contract.claim(id, {"from": user, "gas_price": gas_price})
            time.sleep(MINIMUM_CONFIRMATION_TIME)
            return True
        except Exception as e:
            print(f"Exception: {e}")
            return False
    else:
        print("Insufficent account balance to send transaction")
        return False


def gold_get_claimable(id):
    return {"Claimable Gold": gold_contract.claimable.call(id) // DECIMALS}


def get_gas_price():
    response = requests.get(
        "https://gftm.blockscan.com/gasapi.ashx?apikey=key&method=gasoracle"
    )
    if response.status_code == 200 and response.json()["message"] == "OK":
        # Python's int() cannot convert a floating point number
        # stored as a string, so we convert to float first since
        # the API sometimes returns a value with a decimal
        network.gas_price(
            f'{int(GAS_BUFFER * float(response.json()["result"]["ProposeGasPrice"]))} gwei'
        )


def summoner_get_stats(id):
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


def summoner_get_next_xp(level):
    return {"XP_LevelUp": summoner_contract.xp_required.call(level) // DECIMALS}


def summoner_level_up(id):
    try:
        gas_price = get_gas_price()
        estimate = summoner_contract.level_up.estimate_gas(
            id, {"from": user, "gas_price": gas_price}
        )
    except Exception as e:
        print("Could not estimate gas!")
        print(f"Exception: {e}")
        return False

    if (user.balance() / WEI_PER_GWEI) >= estimate:
        try:
            summoner_contract.level_up(id, {"from": user, "gas_price": gas_price})
            time.sleep(MINIMUM_CONFIRMATION_TIME)
            return True
        except Exception as e:
            print(f"Exception: {e}")
            return False
    else:
        print("Insufficent account balance to send transaction")
        return False


# Only executes main loop if this file is called directly
if __name__ == "__main__":
    main()
