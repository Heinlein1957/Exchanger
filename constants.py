from telebot import types
from utils import qiwi_validation_check, yad_validation_check, card_validation_check
from blockchain_api import check_btc_address
from coinbase_api import check_payment
from config import own_qiwi_number, own_yad_number
import qiwi
import yandexmoney

# Можно редактировать следующие сообщения !!! кроме предложений с `{}` !!!
menu_message = "Здравствуйте 👋. Выберите тип операции!\n\n📈 Текущий курс:\n1 BTC = {} ₽\n1 BTC = {} $\n\n" \
               "Помощь, сотрудничество, ваши предложения и жалобы - /help"

set_payment_error_mes = "Выберите один из предложенных способов"

set_amount_mes = "Введите необходимую сумму покупки в BTC или рублях"

help_message = ''

# Если нужно изменить эти сообщения или кнопки - лучше написать мне:

menu_markup = types.ReplyKeyboardMarkup(True, False)
menu_markup.row("📥Купить BTC", "📤Продать BTC")

set_address_mes = "Для совершениея обмена, введите "

set_payment_mes = "Укажите удобный для вас способ "

payment_markup = types.ReplyKeyboardMarkup(True, False, row_width=2)
payment_markup.add("🥝 Qiwi", "💵 ЯндексДеньги", "💳 Visa(Mastercard)")
payment_markup.row("🔙 Обратно в меню")

back_markup = types.ReplyKeyboardMarkup(True, False)
back_markup.row("🔙 Обратно в меню")

payments = {
    "🥝 Qiwi": "qiwi",
    "💵 ЯндексДеньги": "yad",
    "💳 Visa(Mastercard)": "card"
}

reversed_payments = {
    "qiwi": "🥝 Qiwi",
    "yad": "💵 ЯндексДеньги",
    "card": "💳 Visa(Mastercard)"
}

payments_validations = {
    'qiwi': qiwi_validation_check,
    'yad': yad_validation_check,
    'card': card_validation_check,
    'btc': check_btc_address
}

payments_numbers = {
    'qiwi': own_qiwi_number,
    'yad': own_yad_number
}

address_mes_texts = {
    'qiwi': 'ваш Qiwi кошелек',
    'yad': 'номер вашего кошелька YandexMoney',
    'card': 'номер вашей карты'
}

payments_balances = {
    'qiwi': qiwi.get_qiwi_balance,
    'yad': yandexmoney.get_yandex_balance,
    'card': qiwi.get_qiwi_balance
}

payments_checking = {
    'qiwi': qiwi.check_payment_history,
    'yad': yandexmoney.check_payment_history,
    'card': qiwi.check_payment_history,
    'btc': check_payment
}

address_markup = types.ReplyKeyboardMarkup(True, False, row_width=1)
address_markup.add("💾 Сохранить адрес", "🚫 Не сохранять")

address_error_mes = "Такого {} не существует, или вы допустили ошибку!"

set_amount_error_mes = "Введите сумму от {:0.7f} до {:0.7f} BTC\nИли в рублях: от {} до {} руб"

confirm_markup = types.ReplyKeyboardMarkup(True, False, row_width=1)
confirm_markup.add("✅ Перейти к оплате", "Изменить сумму", "🔙 Обратно в меню")

confirm_mes = "Будет зачислено *{}*\nКомиссия *{}*%\nНужно будет оплатить *{}*\n\nПлатежный сервис: *{}*\n" \
              "Адрес для получения: *{}*\nКурс на момент покупки: 1 BTC = {} руб"

wait_for_pay_markup = types.ReplyKeyboardMarkup(True, False)
wait_for_pay_markup.row('✅ Проверить оплату', '❌ Отменить операцию')

admin_markup = types.ReplyKeyboardMarkup(True, False)
admin_markup.row('Перевести BTC', 'Перевести рубли с киви')
admin_markup.row('Перевести рубли с ЯД')
admin_markup.row('Перевести рубли с карты')
admin_markup.row('История обменов', 'Баланс кошельков')
admin_markup.row('⚙️Настройки')

admin_menu_text = 'Здравствуйте!\nКоличество пользователей в боте - {}\nКоличество обменов - {}\n' \
                  'Общая сумма обмена в рублях - {}\nНажмите /start, для выхода из админки'

admin_back_markup = types.ReplyKeyboardMarkup(True, False)
admin_back_markup.row('Вернуться в главное меню админки')

admin_confirm_markup = types.ReplyKeyboardMarkup(True, False)
admin_confirm_markup.row('Да, перевести', 'Нет, отменить')

setting_tokens = {
    'Комиссию': 'Commission',
    'Минимальную сумму обмена': 'MinRubAmount',
    'Username админа': 'AdminUsername',
    'Qiwi токен': 'QiwiToken',
    'Yandex токен': 'YandexMoneyToken',
    'Api ключ Coinbase': 'CoinbaseApiKey',
    'Secret ключ Coinbase': 'CoinbaseSecretKey'
}

admin_setting_markup = types.ReplyKeyboardMarkup(True, False, row_width=2)
admin_setting_markup.add('Комиссию', 'Минимальную сумму обмена', 'Username админа', 'Qiwi токен', 'Yandex токен',
                         'Api ключ Coinbase', 'Secret ключ Coinbase')
admin_setting_markup.row('Вернуться в главное меню админки')

admin_setting_mes = 'Выберите, что хотите изменить в конфигурации бота'
