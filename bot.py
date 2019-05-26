import telebot
import multiprocessing
import log
import logging
import time
from telebot import apihelper
from datetime import datetime
from constants import *
from coinbase_api import *
from blockchain_api import get_rates
from utils import create_random_comment, sub_commission, add_commission
from config import bot_token, admin_id, ip, own_qiwi_number
import sql as db
import qiwi
import yandexmoney

bot = telebot.TeleBot(bot_token)


@bot.message_handler(regexp="🔙 Обратно в меню")
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    db.add_user(user_id, message.from_user.username)
    bot.send_message(user_id, menu_message.format(*get_rates()), reply_markup=menu_markup)


@bot.message_handler(commands=['help'])
def help_handler(message):
    user_id = message.from_user.id
    bot.send_message(user_id, help_message + f"\nАдмин - {get_config_var('AdminUsername')}")


@bot.message_handler(regexp="(?:^📥Купить|^📤Продать) BTC")
def trade_handler(message):
    user_id = message.from_user.id
    action = message.text.split(' ')[0]
    if action == "📥Купить":
        action = "buy"
        payment_text = set_payment_mes + "покупки 🔶 BTC 🔶"
    else:
        action = "send"
        payment_text = set_payment_mes + "продажи 🔶 BTC 🔶"
    bot.send_message(user_id, payment_text, reply_markup=payment_markup)
    db.set_state(user_id, {'State': 'set_payment', 'Action': action})


@bot.message_handler(func=lambda message: 'set_payment' in db.get_state(message.from_user.id))
def set_payment(message):
    user_id = message.from_user.id
    try:
        payment = payments[message.text]
        db.set_state(user_id, {'State': 'set_address', 'Payment': payment})
        plus_text = 'ваш BTC адрес' if 'buy' in db.get_state(user_id, ['Action']) else address_mes_texts[payment]
        bot.send_message(user_id, set_address_mes + plus_text, reply_markup=back_markup)
    except KeyError:
        bot.send_message(user_id, set_payment_error_mes, reply_markup=payment_markup)


@bot.message_handler(func=lambda message: 'set_address' in db.get_state(message.from_user.id))
def set_address(message):
    user_id = message.from_user.id
    address = message.text
    action, payment = db.get_state(user_id, ['Action', 'Payment'])
    if action == 'buy':
        is_valid = payments_validations['btc'](address)
        substr = 'адреса'
    else:
        is_valid = payments_validations[payment](address)
        substr = 'номера карты' if 'card' in payment else 'счета'

    if is_valid:
        db.set_state(user_id, {'State': 'set_amount', 'Address': address})
        bot.send_message(user_id, set_amount_mes, reply_markup=back_markup)
    else:
        bot.send_message(user_id, address_error_mes.format(substr), reply_markup=back_markup)


@bot.message_handler(func=lambda message: 'set_amount' in db.get_state(message.from_user.id))
def set_amount(message):
    user_id = message.from_user.id
    try:
        amount = float(message.text)
    except ValueError:
        bot.send_message(user_id, "Необходимо ввести число или дробь, разделенную точкой", reply_markup=back_markup)
        return
    try:
        min_rub_amount = int(get_config_var('MinRubAmount'))
    except TypeError:
        min_rub_amount = 100
    min_btc_amount = round(convert_to_btc(min_rub_amount), 7)
    action, payment, address = db.get_state(user_id, ['Action', 'Payment', 'Address'])
    if action == 'buy':
        max_btc_amount, max_rub_amount = get_account_balance()
    else:
        max_rub_amount = payments_balances[payment]()
        max_btc_amount = round(convert_to_btc(max_rub_amount), 7)

    if min_btc_amount <= amount <= max_btc_amount:
        converted = convert_to_rub(amount)
        rub_amount = round(add_commission(converted, payment) if action == 'buy'
                           else sub_commission(converted, payment, address))
        btc_amount = amount
    elif min_rub_amount <= amount <= max_rub_amount:
        rub_amount = int(amount)
        btc_amount = round(sub_commission(convert_to_btc(amount), payment) if action == 'buy'
                           else convert_to_btc(add_commission(rub_amount, payment, address)), 7)
    else:
        bot.send_message(user_id,
                         set_amount_error_mes.format(min_btc_amount, max_btc_amount, min_rub_amount, max_rub_amount),
                         reply_markup=back_markup)
        return

    if action == 'buy':
        to_receive, to_pay = str(btc_amount) + ' BTC', str(rub_amount) + ' руб'
    else:
        to_receive, to_pay = str(rub_amount) + ' руб', str(btc_amount) + ' BTC'
    db.set_state(user_id, {'State': 'confirm', 'AmountRUB': rub_amount, 'AmountBTC': btc_amount})
    commission = get_config_var('Commission')
    if not commission:
        commission = 10
    bot.send_message(user_id, confirm_mes.format(to_receive, commission, to_pay,
                                                 reversed_payments[payment], address, round(convert_to_rub(1), 2)),
                     reply_markup=confirm_markup, parse_mode='Markdown')


@bot.message_handler(func=lambda message: 'confirm' in db.get_state(message.from_user.id))
def confirm(message):
    user_id = message.from_user.id
    text = message.text
    if text == "✅ Перейти к оплате":
        action, payment, rub, btc = db.get_state(user_id, ['Action', 'Payment', 'AmountRUB', 'AmountBTC'])

        if action == 'buy':
            comment = create_random_comment()
            pay_url = qiwi.create_form(own_qiwi_number, rub, comment)  # if payment == 'qiwi' else own_card_number
            markup = types.InlineKeyboardMarkup()
            if payment == 'yad':
                markup = wait_for_pay_markup
            else:
                markup.row(types.InlineKeyboardButton('Оплатить в браузере', pay_url))
            if payment != 'card':
                text = f'Переведите `{rub}` руб\nна этот номер: `{payments_numbers[payment]}` ' \
                       f'({reversed_payments[payment]})\nс комментарием `{comment}`\n❗️Важно: не забудьте указать ' \
                       f'комментарий к платежу, иначе ваши средства не будут засчитаны\n\n' \
                       f'После оплаты, вам будет переведено {btc} BTC'
            else:
                text = f'Для оплаты с помощью карты откройте [форму]({pay_url}) *в браузере* и выберите ' \
                       f'соответствующий способ.\n\nПосле оплаты, вам будет переведено {btc} BTC'
            bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')

            if payment != 'yad':
                bot.send_message(user_id, 'Подтвердите или отмените оплату', reply_markup=wait_for_pay_markup)
        else:
            address, comment = make_address()
            bot.send_message(user_id, f'Переведите `{btc}` BTC\nна этот адрес: `{address}` (BTC)\n\n'
                                      f'После оплаты, вам будет переведено {rub} руб',
                             reply_markup=wait_for_pay_markup, parse_mode='Markdown')

        db.set_state(user_id, {'State': 'paying|' + comment, 'Date': datetime.now()})
    elif text == 'TestAdminPrivileges':
        db.set_state(user_id, {'State': 'Admin_menu'})
    elif text == "Изменить сумму":
        db.set_state(user_id, {'State': 'set_amount'})
        bot.send_message(user_id, "Укажите новую сумму в BTC или рублях", reply_markup=back_markup)


@bot.message_handler(func=lambda message: 'paying' in db.get_state(message.from_user.id)[0])
def paying(message):
    user_id = message.from_user.id
    text = message.text
    if text == '✅ Проверить оплату':
        date, state, payment, action, rub, btc, address = db.get_state(user_id, ['Date', 'State', 'Payment', 'Action',
                                                                                 'AmountRUB', 'AmountBTC', 'Address'])
        if (datetime.now() - date).seconds // 3600 > 24:
            db.set_state(user_id, {'State': ''})
            bot.send_message(user_id,
                             'Ваша операция просрочена. Вы можете начать новую\n\n' + menu_message.format(*get_rates()),
                             reply_markup=menu_markup)
        else:
            comment = state.split('|')[1]
            admin_username = db.get_config_var('AdminUsername')
            if action == 'buy':
                confirmed = payments_checking[payment](comment, rub)
            else:
                confirmed = payments_checking['btc'](comment, btc)

            if confirmed:
                converted = round(convert_to_rub(btc))
                if action == 'buy':
                    tx_hash = send_btc(address, btc)
                    if tx_hash:
                        bot.send_message(user_id, f'Ваш платеж принят. Ожидайте поступления BTC на свой адрес.')
                        db.new_transaction(user_id, rub, converted, datetime.now())
                        bot.send_message(admin_id, f'❇️ Новая операция ❇️\nПользователь @{message.from_user.username} '
                                                   f'id:`{user_id}`\nОплачено: {rub}\nПолучено: {converted}')
                    else:
                        bot.send_message(user_id, f'Возникла ошибка во время перевода... Возможно вы неверно указали '
                                                  f'свой номер\nОбратитесь за помощью к админу {admin_username}')
                else:
                    if payment == 'yad':
                        sent = yandexmoney.send_money(address, rub)
                    else:
                        sent = qiwi.send_money(address, rub)

                    if sent:
                        bot.send_message(user_id, 'Ваш платеж принят. Ожидайте поступления средств.')
                        db.new_transaction(user_id, convert_to_rub(btc), rub, datetime.now())
                        bot.send_message(admin_id, f'❇️ Новая операция ❇️\nПользователь @{message.from_user.username} '
                                                   f'id:`{user_id}`\nОплачено: {converted}\nПолучено: {rub}')
                    else:
                        bot.send_message(user_id, f'Возникла ошибка во время перевода... Возможно вы неверно указали '
                                                  f'свой номер\nОбратитесь за помощью к админу {admin_username}')
                start_handler(message)
            else:
                bot.send_message(user_id, f'Что то пошло не так...\nПопробуйте еще раз через 5-10 минут.\nВ случае '
                                          f'нескольких неудач, обратитесь за помощью к админу {admin_username}')
    elif text == '❌ Отменить операцию':
        db.set_state(user_id, {'State': ''})
        bot.send_message(user_id, menu_message.format(*get_rates()), reply_markup=menu_markup)


# ======================= Admin panel ================================


@bot.message_handler(func=lambda message: message.from_user.id == admin_id and
                     message.text in ['Вернуться в главное меню админки', '/adm'])
def admin_command(message):
    user_id = message.from_user.id
    users_count = db.get_users_count()
    transactions_count = db.get_transactions_count()
    total_sum = db.get_total_sum()
    db.set_state(user_id, {'State': 'Admin_menu'})
    bot.send_message(user_id, admin_menu_text.format(users_count, transactions_count, total_sum),
                     reply_markup=admin_markup)


@bot.message_handler(func=lambda message: 'Admin_menu' in db.get_state(message.from_user.id) and
                                          message.text == 'История обменов')
def transactions_list(message):
    user_id = message.from_user.id
    tx_list = db.get_transactions()
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton('➡️', callback_data='tx_list 10'))
    bot.send_message(user_id, 'Показано: 0 - 10\n\n' + '\n'.join([f'*[{tx[3]}]* /getUser{tx[0]} Отдано: `{tx[1]}` '
                                                                  f'Получено: `{tx[2]}`' for tx in tx_list[0:10]]),
                     reply_markup=markup, parse_mode='Markdown')


@bot.callback_query_handler(func=lambda callback: 'tx_list' in callback.data)
def scroll_tx_list(callback):
    user_id = callback.from_user.id
    offset = int(callback.data.split(' ')[1])
    tx_list = db.get_transactions()
    markup = types.InlineKeyboardMarkup()
    if len(tx_list) - offset > 10:
        markup.add(types.InlineKeyboardButton('➡️', callback_data=f'tx_list {offset + 10}'))
    if offset != 0:
        markup.add(types.InlineKeyboardButton('⬅️', callback_data=f'tx_list {offset - 10}'))
    bot.edit_message_text(f'Показано: {offset} - {offset + 10}\n\n' + '\n'.join([f'*[{tx[3]}]* /getUser{tx[0]} Отдано: '
                          f'`{tx[1]}` Получено: `{tx[2]}`' for tx in tx_list[offset:offset + 10]]), user_id,
                          callback.message.message_id, reply_markup=markup, parse_mode='Markdown')


@bot.message_handler(regexp=r'/getUser\d', func=lambda message: message.from_user.id == admin_id)
def get_user_handler(message):
    user_id = message.from_user.id
    search_id = int(message.text.replace('/getUser', ''))
    user_info = db.get_user_info(search_id)
    try:
        bot.send_message(user_id, f'*Информация о пользователе*\nId: `{user_info[0]}`\nUsername: @{user_info[1]}\n'
                                  f'Кол-во проведенных операций: {user_info[2]}', parse_mode='Markdown')
    except TypeError:
        pass


@bot.message_handler(func=lambda message: 'Admin_menu' in db.get_state(message.from_user.id) and
                                          message.text == 'Баланс кошельков')
def check_balances_handler(message):
    user_id = message.from_user.id
    qiwi_balance = payments_balances['qiwi']()
    text = 'Балансы ваших счетов:\nCoinbase: `{}` BTC | `{}` руб\nQiwi кошелек: `{}` руб\nYandexMoney: `{}` руб\n' \
           'Card: `{}` руб'.format(*get_account_balance(), qiwi_balance, payments_balances['yad'](), qiwi_balance)
    bot.send_message(user_id, text, parse_mode='Markdown')


@bot.message_handler(func=lambda message: 'Admin_menu' in db.get_state(message.from_user.id) and
                                          'Перевести' in message.text)
def admin_send_btc(message):
    user_id = message.from_user.id
    if 'BTC' in message.text:
        payment = 'btc'
    elif 'ЯД' in message.text:
        payment = 'yad'
    else:
        payment = 'qiwi'
    db.set_state(user_id, {'State': 'Admin_send_address', 'Payment': payment})
    bot.send_message(user_id, 'Отправьте реквизиты для перевода', reply_markup=admin_back_markup)


@bot.message_handler(func=lambda message: 'Admin_send_address' in db.get_state(message.from_user.id))
def admin_send_address(message):
    user_id = message.from_user.id
    if payments_validations[db.get_state(message.from_user.id, ['Payment'])[0]](message.text):
        db.set_state(user_id, {'State': 'Admin_send', 'Address': message.text})
        bot.send_message(user_id, 'Введите сумму для перевода (не менее 10 руб)', reply_markup=admin_back_markup)
    else:
        bot.send_message(user_id, 'Такого адреса не существует, или вы допустили ошибку!')


@bot.message_handler(func=lambda message: 'Admin_send' in db.get_state(message.from_user.id))
def admin_send(message):
    user_id = message.from_user.id
    sub_str = 'BTC'
    try:
        amount = float(message.text)
    except ValueError:
        bot.send_message(user_id, "Введите число или дробь, разделенную точкой", reply_markup=admin_back_markup)
        return
    address, payment = db.get_state(user_id, ['Address', 'Payment'])
    if payment == 'btc':
        max_btc, max_rub = get_account_balance()
        if 10 < amount < max_rub:
            amount = convert_to_btc(amount)
        if amount > max_btc:
            bot.send_message(user_id, 'Недостаточно средств на балансе', reply_markup=admin_back_markup)
            return
    else:
        max_rub = payments_balances[payment]()
        if 0 < amount < 10:
            amount = convert_to_rub(amount)
        amount = int(amount)
        if amount > max_rub:
            bot.send_message(user_id, 'Недостаточно средств на балансе', reply_markup=admin_back_markup)
            return
        sub_str = 'руб'
    amount_state = 'AmountRUB' if payment != 'btc' else 'AmountBTC'
    db.set_state(user_id, {'State': 'Admin_send_confirm', amount_state: amount})
    bot.send_message(user_id, f'Перевести *{amount}* {sub_str} на *{address}* ?', reply_markup=admin_confirm_markup,
                     parse_mode='Markdown')


@bot.message_handler(func=lambda message: 'Admin_send_confirm' in db.get_state(message.from_user.id))
def admin_send_confirm(message):
    user_id = message.from_user.id
    if message.text == 'Да, перевести':
        address, payment, rub, btc = db.get_state(user_id, ['Address', 'Payment', 'AmountRUB', 'AmountBTC'])
        amount = rub if payment != 'btc' else btc
        if payment == 'btc':
            sent = send_btc(address, amount)
        elif payment == 'yad':
            sent = yandexmoney.send_money(address, amount)
        else:
            sent = qiwi.send_money(address, amount)
        text = 'Деньги переведены. Ожидайте поступления средств.'
        text += f'\nИнформация о транзакции https://www.blockchain.com/btc/tx/{sent}' if payment == 'btc' else ''
        if sent:
            bot.send_message(user_id, text, True)
        else:
            bot.send_message(user_id, '❗️Возникла какая-то ошибка при переводе❗️')
        admin_command(message)
    elif message.text == 'Нет, отменить':
        admin_command(message)


@bot.message_handler(func=lambda message: 'Admin_menu' in db.get_state(message.from_user.id) and
                                          message.text == '⚙️Настройки')
def admin_settings_handler(message):
    user_id = message.from_user.id
    db.set_state(user_id, {'State': 'Admin_settings'})
    bot.send_message(user_id, admin_setting_mes, reply_markup=admin_setting_markup)


@bot.message_handler(func=lambda message: 'Admin_settings' in db.get_state(message.from_user.id))
def admin_settings(message):
    user_id = message.from_user.id
    if message.text == 'Yandex токен':
        bot.send_message(user_id, f'Для обновления токена YM:\n\n1. На сервере, на время отключите бота\n2. Запустите '
                                  f'файл deploy.py с аргументом -newYMToken. Команда: <code>python3.6 deploy.py '
                                  f'-newYMToken</code>\n3. Перейдите по этой ссылке: https://{ip}/auth_url и '
                                  f'подтвердите выпуск нового токена\n\nДанные будут автоматически помещены в бд',
                         parse_mode='HTML')
        admin_settings_handler(message)
    else:
        try:
            name = setting_tokens[message.text]
            db.set_state(user_id, {'State': 'Admin_new_' + name})
            bot.send_message(user_id, 'Введите новое значение')
        except KeyError:
            pass


@bot.message_handler(func=lambda message: 'Admin_new_' in db.get_state(message.from_user.id)[0])
def update_config(message):
    user_id = message.from_user.id
    name = db.get_state(user_id)[0].split('_')[2]
    db.insert_new_config_var(name, message.text)
    db.set_state(user_id, {'State': 'Admin_settings'})
    bot.send_message(user_id, 'Значение параметра успешно обновлено!')


def args_check(args_names, checking_kwargs):
    for arg in args_names:
        if checking_kwargs.get(arg) is None:
            return False
    return True


def bot_start(use_webhook=False, webhook_data=None):
    if webhook_data is None:
        webhook_data = {}

    def set_webhook(url, cert):
        try:
            apihelper.set_webhook(bot_token, url=url, certificate=cert)
        except Exception as err:
            print(err.with_traceback(None))

    def webhook_isolated_run(url, cert):
        multiprocessing.Process(target=set_webhook, args=(url, cert), daemon=True).start()

    global bot

    telebot.logger.setLevel(logging.DEBUG)
    telebot.logger.addHandler(log.__file_handler('logs.log', log.__get_formater()))

    if not use_webhook:
        bot.remove_webhook()
        bot.polling(none_stop=True)

    elif args_check(['webhook_ip', 'webhook_port', 'token', 'ssl_cert'], webhook_data):
        bot.remove_webhook()
        time.sleep(1)

        webhook_isolated_run(url='https://%s:%s/%s/' % (webhook_data.get('webhook_ip'),
                                                        webhook_data.get('webhook_port'),
                                                        webhook_data.get('token')),
                             cert=open(webhook_data.get('ssl_cert'), 'r'))

        return bot
    else:
        raise Exception('Params for start with webhook is not specified')

    return bot
