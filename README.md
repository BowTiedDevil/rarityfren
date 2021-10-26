# rarityfren

## Package prerequisites
* Python 3
* Python Packages (installed with `pip install [packagename]`)
    - requests
    - eth-brownie

## Brownie Setup
Create a dedicated account on the console using `brownie accounts new`, enter the private key from your Metamask wallet (or similar). Edit the `ADDRESS_USER` value in `adventure.py` to match the public address.

## Basic Use
Run `python3 adventure.py`, unlock brownie account data using password, watch your summoners go on their adventures

## TO-DO
- Improve README
- Refactor, too many functions in adventure.py