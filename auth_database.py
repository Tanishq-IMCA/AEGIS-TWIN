import os
from contextlib import contextmanager

import psycopg2
from werkzeug.security import check_password_hash, generate_password_hash


def _username_key(username):
    if not isinstance(username, str):
        return ""
    return username.strip().casefold()


@contextmanager
def _connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for login accounts.")

    connection = psycopg2.connect(database_url, connect_timeout=10)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize():
    """Fail early if the login-only table has not been provisioned."""
    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username, username_key, password_hash "
                "FROM nexus_login_accounts LIMIT 0"
            )


def create_account(username, password):
    username = username.strip()
    key = _username_key(username)
    if not key or not password:
        return False

    password_hash = generate_password_hash(password)
    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO nexus_login_accounts (username, username_key, password_hash)
                VALUES (%s, %s, %s)
                ON CONFLICT (username_key) DO NOTHING
                RETURNING username_key
                """,
                (username, key, password_hash),
            )
            return cursor.fetchone() is not None


def has_account(username):
    key = _username_key(username)
    if not key:
        return False
    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM nexus_login_accounts WHERE username_key = %s",
                (key,),
            )
            return cursor.fetchone() is not None


def list_usernames():
    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username FROM nexus_login_accounts ORDER BY username_key"
            )
            return [row[0] for row in cursor.fetchall()]


def verify_password(username, password):
    key = _username_key(username)
    if not key or not isinstance(password, str):
        return False

    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM nexus_login_accounts WHERE username_key = %s",
                (key,),
            )
            row = cursor.fetchone()

    return bool(row and check_password_hash(row[0], password))


def set_password(username, password):
    key = _username_key(username)
    if not key or not password:
        return False

    password_hash = generate_password_hash(password)
    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE nexus_login_accounts
                SET password_hash = %s
                WHERE username_key = %s
                """,
                (password_hash, key),
            )
            return cursor.rowcount == 1


def delete_account(username):
    key = _username_key(username)
    if not key:
        return False
    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM nexus_login_accounts WHERE username_key = %s",
                (key,),
            )
            return cursor.rowcount == 1
