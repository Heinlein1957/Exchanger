import requests
import json
from time import time
from re import sub
from config import own_qiwi_number
from sql import get_config_var
import log

qiwi_logger = log.logger('qiwi', 'logs.log')


def validate_number(number):
    new = sub(r'\W', '', number)
    if new[0] == '8' and len(new) == 11:
        new = '7' + new[1:]
    return new


def check_payment_history(comment, amount):
    qiwi_token = get_config_var('QiwiToken')
    if not qiwi_token:
        return False
    s = requests.Session()
    s.headers['authorization'] = 'Bearer ' + qiwi_token
    params = {
        'rows': '50',
        'operation': 'IN'
    }
    h = s.get(f'https://edge.qiwi.com/payment-history/v2/persons/{validate_number(own_qiwi_number)}/payments',
              params=params)
    data = json.loads(h.text)['data']
    for payment in data:
        if payment['comment'] is not None and comment in payment['comment'] and payment['sum']['amount'] >= amount:
            return True
    return False


def get_qiwi_balance():
    qiwi_token = get_config_var('QiwiToken')
    if not qiwi_token:
        return False
    s = requests.Session()
    s.headers['authorization'] = 'Bearer ' + qiwi_token
    accounts = s.get(f"https://edge.qiwi.com/funding-sources/v2/persons/{validate_number(own_qiwi_number)}/accounts")
    for account in json.loads(accounts.text)['accounts']:
        if account['defaultAccount'] and account['currency'] == 643:
            return account['balance']['amount']
    return 0


def detect_payment_system(number):
    url = 'https://qiwi.com/card/detect.action'
    res = requests.post(url, data={"cardNumber": number})
    return res.json()


def commission_amount(number, amount):
    number = validate_number(number)
    qiwi_token = get_config_var('QiwiToken')
    if not qiwi_token:
        return False
    s = requests.Session()
    s.headers['authorization'] = 'Bearer ' + qiwi_token
    id_details = detect_payment_system(number)
    if id_details['code']['value'] == '2':
        payment_id = '99'
    else:
        payment_id = id_details['message']
    url = f'https://edge.qiwi.com/sinap/providers/{payment_id}/onlineCommission'
    data = {
        "account": number,
        "paymentMethod": {
            "type": "Account",
            "accountId": "643"
        },
        "purchaseTotals": {
            "total": {
                "amount": amount,
                "currency": "643"
            }
        }
    }
    res = s.post(url, json=data)
    return res.json()['qwCommission']['amount']


def send_money(number, amount):
    number = validate_number(number)
    qiwi_token = get_config_var('QiwiToken')
    if not qiwi_token:
        return False
    s = requests.Session()
    s.headers['authorization'] = 'Bearer ' + qiwi_token
    id_details = detect_payment_system(number)
    if id_details['code']['value'] == '2' and 'Неверно введен номер банковской карты' in id_details['message']:
        payment_id = '99'
    else:
        payment_id = id_details["message"]

    url = f'https://edge.qiwi.com/sinap/api/v2/terms/{payment_id}/payments'
    data = {
        "id": str(int(time() * 1000)),
        "sum": {
            "amount": amount,
            "currency": "643"
        },
        "paymentMethod": {
            "type": "Account",
            "accountId": "643"
        },
        "fields": {
            "account": number
        }
    }
    res = s.post(url, json=data)
    if not res.ok:
        qiwi_logger.warning(res.text)
    return res.ok


def create_form(number, amount, comment=None):
    number = validate_number(number)
    id_details = detect_payment_system(number)
    if id_details['code']['value'] == '2':
        payment_id = '99'
    else:
        payment_id = id_details['message']

    url = f"https://qiwi.com/payment/form/{payment_id}?amountInteger={amount}&amountFraction=0&currency=643&" \
          f"extra%5B%27account%27%5D={number}&blocked%5B0%5D=sum&blocked%5B1%5D=account&blocked%5B2%5D=comment"
    if payment_id == '99':
        url += '&extra%5B%27comment%27%5D=' + comment
    return url
