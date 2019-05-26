from coinbase.wallet.client import Client
from sql import get_config_var
import log

coinbase_logger = log.logger('coinbase', 'logs.log')


def get_client():
    coinbase_api_key = get_config_var('CoinbaseApiKey')
    coinbase_api_secret = get_config_var('CoinbaseSecretKey')
    if not coinbase_api_key or not coinbase_api_secret:
        return False
    return Client(coinbase_api_key, coinbase_api_secret)


def get_account_balance():
    client = get_client()
    if not client:
        return False, False
    account = client.get_primary_account()
    in_btc = float(account['balance']["amount"])
    in_rub = float(account['native_balance']["amount"])

    return in_btc, in_rub


def make_address():
    client = get_client()
    if not client:
        return False
    new_address = client.get_primary_account().create_address()
    return new_address['address'], new_address['id']


def check_payment(address_id, amount):
    client = get_client()
    if not client:
        return False
    transactions = client.get_primary_account().get_address_transactions(address_id)['data']
    for tx in transactions:
        if float(tx['amount']['amount']) >= amount and (
                tx['network']['status'] == 'confirmed' or tx['status'] == 'completed'):
            return True
    return False


def convert_to_rub(amount):
    client = get_client()
    if not client:
        return False
    return amount * float(client.get_exchange_rates(currency='BTC')['rates']['RUB'])


def convert_to_btc(amount):
    client = get_client()
    if not client:
        return False
    return amount / float(client.get_exchange_rates(currency='BTC')['rates']['RUB'])


def send_btc(address, amount):
    try:
        client = get_client()
        if not client:
            return False
        client.get_primary_account().send_money(to=address, amount=amount, currency='BTC')
    except Exception as e:
        coinbase_logger.warning(e)
        return False
    return True
