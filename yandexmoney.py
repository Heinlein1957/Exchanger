from yandex_money.api import Wallet
from sql import get_config_var
import log

ym_logger = log.logger('yandexmoney', 'logs.log')


def get_yandex_balance():
    yandex_money_token = get_config_var('YandexMoneyToken')
    if not yandex_money_token:
        return False
    wallet = Wallet(yandex_money_token)
    account_info = wallet.account_info()
    return account_info['balance']


def check_payment_history(comment, amount):
    yandex_money_token = get_config_var('YandexMoneyToken')
    if not yandex_money_token:
        return False
    wallet = Wallet(yandex_money_token)
    options = {
        "type": "deposition",
        "details": "true"
    }
    for operation in wallet.operation_history(options)['operations']:
        try:
            if operation['message'] == comment and operation['amount'] >= amount:
                return True
        except KeyError:
            continue
    return False


def send_money(number, amount):
    yandex_money_token = get_config_var('YandexMoneyToken')
    if not yandex_money_token:
        return False
    wallet = Wallet(yandex_money_token)
    options = {
        "pattern_id": "p2p",
        "to": number,
        "amount_due": amount
    }
    request_result = wallet.request_payment(options)
    process_payment = wallet.process_payment({"request_id": request_result['request_id']})
    if process_payment['status'] == "success":
        return True
    else:
        ym_logger.warning(process_payment['error'])
        return False
