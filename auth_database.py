import os
import sqlite3
from contextlib import contextmanager

import psycopg2
from werkzeug.security import check_password_hash, generate_password_hash


class _CursorAdapter:
    def __init__(self, cursor, sqlite_mode):
        self.cursor = cursor
        self.sqlite_mode = sqlite_mode

    def execute(self, query, params=None):
        if self.sqlite_mode:
            query = query.replace("%s", "?")
        return self.cursor.execute(query, params or ())

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cursor.close()


class _ConnectionAdapter:
    def __init__(self, connection, sqlite_mode):
        self.connection = connection
        self.sqlite_mode = sqlite_mode

    def cursor(self):
        return _CursorAdapter(self.connection.cursor(), self.sqlite_mode)


def _username_key(username):
    if not isinstance(username, str):
        return ""
    return username.strip().casefold()


@contextmanager
def _connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        if os.environ.get("REPL_ID") or os.environ.get("REPLIT_ENVIRONMENT"):
            raise RuntimeError("DATABASE_URL is required for login accounts.")
        database_path = os.environ.get(
            "LOCAL_AUTH_DATABASE",
            os.path.join(os.path.dirname(__file__), "data", "local_auth.sqlite3"),
        )
        os.makedirs(os.path.dirname(os.path.abspath(database_path)), exist_ok=True)
        raw_connection = sqlite3.connect(database_path, timeout=10)
        sqlite_mode = True
    else:
        raw_connection = psycopg2.connect(database_url, connect_timeout=10)
        sqlite_mode = False

    connection = _ConnectionAdapter(raw_connection, sqlite_mode)
    try:
        yield connection
        raw_connection.commit()
    except Exception:
        raw_connection.rollback()
        raise
    finally:
        raw_connection.close()


def initialize():
    """Fail early if the login-only table has not been provisioned."""
    with _connection() as connection:
        with connection.cursor() as cursor:
            if connection.sqlite_mode:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS nexus_login_accounts (
                        username TEXT NOT NULL,
                        username_key TEXT PRIMARY KEY,
                        password_hash TEXT NOT NULL
                    )
                    """
                )
            else:
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
