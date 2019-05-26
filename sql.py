import psycopg2
from psycopg2.extras import DictCursor
import config


def get_connection(dict_return=False):  # -> psycopg2._psycopg.connection:
    if not dict_return:
        return psycopg2.connect(host=config.ip, dbname=config.db_name, user=config.db_login, password=config.db_pass,
                                port=config.db_port)
    else:
        return psycopg2.connect(host=config.ip, dbname=config.db_name, user=config.db_login, password=config.db_pass,
                                port=config.db_port, cursor_factory=DictCursor)


def add_user(user_id, username):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (User_id, Username, State) VALUES (%s, %s, %s) "
                        "ON CONFLICT (User_id) DO UPDATE SET State = %s;", (user_id, username, '', ''))
            conn.commit()


def get_btc_address(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT Address FROM users WHERE User_id = %s;", (user_id,))
            address = cur.fetchone()[0]
            conn.commit()
            return address


def set_state(user_id, states: dict):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE users SET {', '.join([f'{state} = %s' for state in states.keys()])} WHERE User_id = %s;",
                        (*states.values(), user_id))
            conn.commit()


def get_state(user_id, states=None):
    if states is None:
        states = ['State']
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {', '.join([state for state in states])} FROM users WHERE User_id = %s;", (user_id,))
            states = cur.fetchall()
            conn.commit()
            return states[0]


def insert_new_config_var(name, token):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO config_vars (Name, Value) VALUES (%s, %s) "
                        "ON CONFLICT (Name) DO UPDATE SET Value = %s;", (name, token, token))
            conn.commit()


def get_config_var(name):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT Value FROM config_vars WHERE Name = %s;", (name,))
            token = cur.fetchone()
            conn.commit()
            return token[0] if token else None


def get_users_count():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(id) FROM users;")
            count = cur.fetchone()[0]
            conn.commit()
            return count


def new_transaction(user_id, rub_in, rub_out, date):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO transactions (User_id, RubIn, RubOut, Date) VALUES "
                        "((SELECT Id FROM users WHERE User_id = %s), %s, %s, %s);", (user_id, rub_in, rub_out, date))
            conn.commit()


def get_transactions_count():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(id) FROM transactions;")
            count = cur.fetchone()[0]
            conn.commit()
            return count


def get_total_sum():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT RubOut FROM transactions;")
            tx_list = cur.fetchall()
            total = 0
            for out in tx_list:
                total += out[0]
            conn.commit()
            return total


def get_transactions():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT User_id, RubIn, RubOut, Date FROM transactions;")
            tx_list = cur.fetchall()
            return tx_list


def get_user_info(row_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT users.User_id, users.Username, (SELECT COUNT(transactions.Id) FROM transactions "
                        f"WHERE transactions.User_id = %s) FROM users WHERE Id = %s;", (row_id, row_id))
            info = cur.fetchone()
            return info


if __name__ == "__main__":
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM config_vars')
