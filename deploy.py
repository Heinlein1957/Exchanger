import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import argparse
import sys
import flask
import requests
from sql import insert_new_config_var
import log

from yandex_money.api import Wallet

from config import client_id, ip, db_name, db_port, db_login, db_pass


def create_db():
    with psycopg2.connect(host=ip, dbname="postgres", user=db_login, password=db_pass, port=db_port) as conn:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            try:
                cur.execute(f'CREATE DATABASE {db_name};')
                print("[SUCCESS] Data base created")
            except psycopg2.ProgrammingError as e:
                if e.pgcode == '42P04':
                    print("[ERROR] Data base already exists")
                else:
                    print(e)
            conn.commit()


def create_users_table():
    with psycopg2.connect(host=ip, dbname=db_name, user=db_login, password=db_pass, port=db_port) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute('CREATE TABLE users '
                            '(Id SERIAL PRIMARY KEY, '
                            'User_id INT UNIQUE NOT NULL, '
                            'Username CHARACTER VARYING(50), '
                            'State CHARACTER VARYING(50), '
                            'Address CHARACTER VARYING(50), '
                            'Action CHARACTER VARYING(5), '
                            'Payment CHARACTER VARYING(5), '
                            'AmountRUB INT, '
                            'AmountBTC REAL, '
                            'Date TIMESTAMP);')
                print("[SUCCESS] Users table created")
            except psycopg2.ProgrammingError as e:
                if e.pgcode == '42P07':
                    print("[ERROR] Users table already exists")
                else:
                    print(e)
            conn.commit()


def create_config_table():
    with psycopg2.connect(host=ip, dbname=db_name, user=db_login, password=db_pass, port=db_port) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute('CREATE TABLE config_vars '
                            '(Id SERIAL PRIMARY KEY, '
                            'Name CHARACTER VARYING(20) UNIQUE, '
                            'Value TEXT);')
                print("[SUCCESS] Config table created")
            except psycopg2.ProgrammingError as e:
                if e.pgcode == '42P07':
                    print("[ERROR] Config table already exists")
                else:
                    print(e)
            conn.commit()


def create_transactions_table():
    with psycopg2.connect(host=ip, dbname=db_name, user=db_login, password=db_pass, port=db_port) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute('CREATE TABLE transactions '
                            '(Id SERIAL PRIMARY KEY, '
                            'User_id INT REFERENCES users (Id), '
                            'RubIn INT, '
                            'RubOut INT, '
                            'Date TIMESTAMP);')
                print("[SUCCESS] Transactions table created")
            except psycopg2.ProgrammingError as e:
                if e.pgcode == '42P07':
                    print("[ERROR] Transactions table already exists")
                else:
                    print(e)


def create_tables():
    create_users_table()
    create_config_table()
    create_transactions_table()


def get_yandex_auth_url():
    scope = ['account-info', 'operation-history', 'operation-details', 'payment-p2p.limit(1,100000)',
             'money-source("wallet","card")']
    return Wallet.build_obtain_token_url(client_id, 'http://' + ip + '/ym', scope) + '&response_type=code'


def flask_init():
    app_ym = flask.Flask(__name__)
    app_logger = app_ym.logger
    app_logger.setLevel(log.levels.get('DEBUG'))
    app_logger.addHandler(log.__file_handler('logs.log', log.__get_formater()))

    @app_ym.route('/')
    def index():
        return 'ʕ´•ᴥ•`ʔ', 200

    @app_ym.route('/auth_url')
    def auth_url():
        return flask.redirect(get_yandex_auth_url())

    @app_ym.route('/ym', methods=['POST', 'GET'])
    def get_token():
        token = requests.post("https://money.yandex.ru/oauth/token",
                              headers={'Content-type': 'application/x-www-form-urlencoded'},
                              data={
                                  "code": flask.request.args['code'],
                                  "client_id": client_id,
                                  "grant_type": "authorization_code",
                                  "redirect_uri": 'http://' + ip + '/ym'
                              }).json()['access_token']
        insert_new_config_var('YandexMoneyToken', token)
        return f'New YM token [{token}] has been inserted into the database', 200

    return app_ym


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-full', dest='full_deploy', action='store_true', default=False,
                        help='runs all functions for full deployment')
    parser.add_argument('-cdb', dest='create_db', action='store_true', default=False, help='creates database')
    parser.add_argument('-cts', dest='create_tables', action='store_true', default=False,
                        help='creates necessary tables')
    parser.add_argument('-newYMToken', dest='new_ym_token', action='store_true', default=False,
                        help='start the flask server and allows you to create a new YM token')

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    if args.full_deploy:
        create_db()
        create_tables()

        print(f'Follow this link: https://{ip}/auth_url and fill the form to create YM token')
        app = flask_init()
        app.run(host='0.0.0.0', port=80)
    else:
        if args.create_db:
            create_db()
        if args.create_tables:
            create_tables()
        if args.new_ym_token:
            print(f'Follow this link: https://{ip}/auth_url and fill the form to create YM token')
            app = flask_init()
            app.run(host='0.0.0.0', port=80)
