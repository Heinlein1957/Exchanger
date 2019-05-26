from blockchain.blockexplorer import get_address
from blockchain import exceptions, exchangerates


def check_btc_address(address):
    try:
        get_address(address)
        return True
    except (exceptions.APIException, UnicodeEncodeError):
        return False


def convert_to_btc(amount):
    return exchangerates.to_btc('RUB', amount)


def convert_to_rub(amount):
    return amount * float(exchangerates.get_ticker()['RUB'].p15min)


def get_rates():
    ticker = exchangerates.get_ticker()
    return float(ticker['RUB'].p15min), float(ticker['USD'].p15min)
