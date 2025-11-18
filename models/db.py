import os
import json
import mysql.connector
from utils.crypto import decrypt_password


def load_settings():
    path = os.path.join(os.path.dirname(__file__), '..', 'appsettings.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_connection():
    cfg = load_settings()

    key_phrase = cfg.get("key_encrypt_bd")
    salt = cfg.get("salt_encrypt", "SIS-ARIAS")

    db_cfg = cfg["db"]

    encrypted = db_cfg.get("password_encrypted_b64")
    plain = db_cfg.get("password")

    # Determinar contraseña final con fallback seguro
    if encrypted:
        try:
            db_password = decrypt_password(encrypted, key_phrase, salt)
        except Exception:
            db_password = plain
    else:
        db_password = plain

    return mysql.connector.connect(
        host=db_cfg["host"],
        port=db_cfg["port"],
        user=db_cfg["user"],
        password=db_password,
        database=db_cfg["database"],
        auth_plugin="mysql_native_password"
    )
