# -*- coding: utf-8 -*-

import telebot
import bot
import flask
from config import bot_token, webhook_port, ssl_cert, ssl_pom, ip
import log


def flask_init(bot_object):
    webhook_app = flask.Flask(__name__)
    webhook_logger = webhook_app.logger
    webhook_logger.setLevel(log.levels.get('DEBUG'))
    webhook_logger.addHandler(log.__file_handler('logs.log', log.__get_formater()))

    @webhook_app.route('/', methods=['GET', 'HEAD'])
    def index():
        return '', 200

    @webhook_app.route('/' + bot_token + '/', methods=['POST'])
    def webhook():
        if flask.request.headers.get('content-type') == 'application/json':
            json_string = flask.request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot_object.process_new_updates([update])
            webhook_logger.debug('updates from webhook: ' + str(update))
            return ''
        else:
            flask.abort(403)

    return webhook_app


def start(use_webhook=False, **webhook_data):
    logger = log.logger('main', 'logs.log')
    try:

        bot_object = bot.bot_start(use_webhook=use_webhook, webhook_data=webhook_data)

        if use_webhook:
            server_app = flask_init(bot_object)
            return server_app

    except Exception as err:
        logger.exception('bot crashed')
        logger.exception(err)


app = start(use_webhook=True,
            webhook_ip=ip,
            webhook_port=webhook_port,
            token=bot_token,
            ssl_cert=ssl_cert)

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=webhook_port, ssl_context=(ssl_cert, ssl_pom))
    except AttributeError:
        print('Local start without webhooks')
