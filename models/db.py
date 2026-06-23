import os
import json
import mysql.connector
from utils.crypto import decrypt_password


def load_settings():
    path = os.path.join(os.path.dirname(__file__), '..', 'appsettings.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def get_encrypt_key():
    cfg = load_settings()
    return cfg.get("key_encrypt_bd")


def get_connection(connect_timeout=None, read_timeout=None, write_timeout=None):
    cfg = load_settings()

    key_phrase = cfg.get("key_encrypt_bd")
    salt = cfg.get("salt_encrypt", "SIS-ARIAS")

    db_cfg = cfg.get("db") or {}

    host = os.environ.get("SIS_ARIAS_DB_HOST") or db_cfg.get("host") or "127.0.0.1"
    port_raw = os.environ.get("SIS_ARIAS_DB_PORT") or db_cfg.get("port") or 3306
    database = os.environ.get("SIS_ARIAS_DB_NAME") or db_cfg.get("database")
    user = os.environ.get("SIS_ARIAS_DB_USER") or db_cfg.get("user")

    encrypted = os.environ.get("SIS_ARIAS_DB_PASSWORD_ENCRYPTED_B64") or db_cfg.get("password_encrypted_b64")
    plain = os.environ.get("SIS_ARIAS_DB_PASSWORD") or db_cfg.get("password")

    # Determinar contraseña final con fallback seguro
    if encrypted:
        try:
            db_password = decrypt_password(encrypted, key_phrase, salt)
        except Exception:
            db_password = plain
    else:
        db_password = plain

    connect_timeout_raw = connect_timeout
    if connect_timeout_raw is None:
        connect_timeout_raw = (
            os.environ.get("SIS_ARIAS_DB_CONNECT_TIMEOUT")
            or db_cfg.get("connect_timeout")
            or db_cfg.get("connection_timeout")
            or 5
        )

    read_timeout_raw = read_timeout
    if read_timeout_raw is None:
        read_timeout_raw = (
            os.environ.get("SIS_ARIAS_DB_READ_TIMEOUT")
            or db_cfg.get("read_timeout")
            or 30
        )

    write_timeout_raw = write_timeout
    if write_timeout_raw is None:
        write_timeout_raw = (
            os.environ.get("SIS_ARIAS_DB_WRITE_TIMEOUT")
            or db_cfg.get("write_timeout")
            or 30
        )

    auth_plugin = os.environ.get("SIS_ARIAS_DB_AUTH_PLUGIN") or db_cfg.get("auth_plugin")

    connect_kwargs = {
        "host": host,
        "port": int(port_raw),
        "user": user,
        "password": db_password,
        "database": database,
        "connection_timeout": int(connect_timeout_raw),
        "read_timeout": int(read_timeout_raw),
        "write_timeout": int(write_timeout_raw),
    }
    if auth_plugin:
        connect_kwargs["auth_plugin"] = auth_plugin

    try:
        cnx = mysql.connector.connect(**connect_kwargs)
    except TypeError:
        connect_kwargs.pop("read_timeout", None)
        connect_kwargs.pop("write_timeout", None)
        cnx = mysql.connector.connect(**connect_kwargs)

    tz_raw = os.environ.get("SIS_ARIAS_DB_TIMEZONE") or (db_cfg.get("timezone") if isinstance(db_cfg, dict) else None) or "-05:00"
    tz = tz_raw or "-05:00"
    if str(tz).upper() in {"UTC", "+00:00", "Z"}:
        tz = "-05:00"
    if str(tz).upper() == "AMERICA/LIMA":
        tz = "-05:00"
    try:
        cur_tz = cnx.cursor()
        cur_tz.execute("SET time_zone = %s", (tz,))
        cur_tz.close()
    except Exception:
        try:
            cur_tz = cnx.cursor()
            cur_tz.execute("SET time_zone = %s", ("-05:00",))
            cur_tz.close()
        except Exception:
            pass

    try:
        cur_cs = cnx.cursor()
        try:
            cur_cs.execute("SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci")
            cur_cs.execute("SET collation_connection = 'utf8mb4_0900_ai_ci'")
        except Exception:
            cur_cs.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
            cur_cs.execute("SET collation_connection = 'utf8mb4_unicode_ci'")
        cur_cs.close()
    except Exception:
        pass

    try:
        cur_key = cnx.cursor()
        cur_key.execute("SET @SIS_KEY = %s", (key_phrase or "",))
        cur_key.close()
    except Exception:
        pass

    return cnx
