import random
from re import findall, sub
from qiwi import commission_amount, detect_payment_system
from sql import get_config_var


def qiwi_validation_check(number):
    return len(findall(r'(?:\+\d{1,2}|\d{1,2})(?:\W?\d{3}){2}(?:\W?\d{2}){2}', number)) == 1


def yad_validation_check(number):
    return (number[:4] == '4100' and 11 <= len(number) <= 20) or \
           len(findall(r'(?:\+\d{1,2}|\d{1,2})(?:\W?\d{3}){2}(?:\W?\d{2}){2}', number)) == 1


def card_validation_check(number: str):
    # return len(number) == 16 and number.isdigit()
    new = sub(r'\W', '', number)
    return detect_payment_system(new)['code']['value'] == '0'


def create_random_comment(n=4):
    chars = list('1234567890ABCDEFGHIGKLMNOPQRSTUVYXWZabcdefghigklmnopqrstuvyxwz')
    random.shuffle(chars)
    block1 = ''.join([random.choice(chars) for _ in range(n)])
    block2 = ''.join([random.choice(chars) for _ in range(n)])
    block3 = ''.join([random.choice(chars) for _ in range(n)])
    block4 = ''.join([random.choice(chars) for _ in range(n)])
    return block1 + '-' + block2 + '-' + block3 + '-' + block4


def sub_commission(amount, payment, number=None):
    commission = get_config_var('Commission')
    commission = 10 if not commission else int(commission)
    res = amount * (1 - commission / 100)
    if payment != 'yad' and number:
        res -= commission_amount(number, res)
    return res


def add_commission(amount, payment, number=None):
    commission = get_config_var('Commission')
    commission = 10 if not commission else int(commission)
    res = amount * (1 + commission / 100)
    if payment != 'yad' and number:
        res += commission_amount(number, res)
    return res
