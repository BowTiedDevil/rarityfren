import sys
import json
import time
import requests
from brownie import *

ADDRESS_RARITY_CONTRACT = "0xce761D788DF608BD21bdd59d6f4B54b2e27F25Bb"
ADDRESS_USER = "0x31d8204ba31768CB4CfA111B429BDc8F2c6f477b"

ETHERSCAN_API_KEY = "8C6RD312AG41JTZK1DK1D4538B6WBJFZBN"
ETHERSCAN_API_PARAMS = {
    "module": "account",
    "action": "tokennfttx",
    "contractaddress": ADDRESS_RARITY_CONTRACT,
    "address": ADDRESS_USER,
    "apikey": ETHERSCAN_API_KEY,
}


# Dictionary of summoners, keyed by unique summoner tokenID
summoners = {}


def main():
    if count := get_summoners():
        print(f"{count} found!")

    user = accounts.load("rarityuser", password="")
    network.connect("ftm-main")

    rarity_contract = Contract.from_explorer(ADDRESS_RARITY_CONTRACT, owner=user)

    for id in summoners.keys():
        adventure(rarity_contract, id)


def get_summoners():
    while True:
        print(
            f"Querying FTMScan API for Rarity summoner data at address {ADDRESS_USER}..."
        )
        if (
            response := requests.get(
                "https://api.ftmscan.com/api", params=ETHERSCAN_API_PARAMS
            )
        ).status_code == 200:
            for metadata in response.json()["result"]:
                summoners[metadata["tokenID"]] = metadata
            return len(summoners)
        else:
            print("retrying...")
            time.sleep(5)


def adventure(contract, id):
    print(f"Adventuring with summoner id: {id}")
    tx = contract.adventure(id)


if __name__ == "__main__":
    main()
