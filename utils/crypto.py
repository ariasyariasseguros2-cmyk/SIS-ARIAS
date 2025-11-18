import base64
from typing import Union
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet


def derive_fernet_key(passphrase: str, salt: Union[str, bytes]) -> bytes:
    """Genera una clave compatible con Fernet desde una passphrase + salt."""
    if isinstance(salt, str):
        salt = salt.encode("utf-8")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))
    return key


def encrypt_password(password: str, passphrase: str, salt: str) -> str:
    """Devuelve la contraseña cifrada en base64."""
    key = derive_fernet_key(passphrase, salt)
    f = Fernet(key)
    encrypted = f.encrypt(password.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_password(encrypted_b64: str, passphrase: str, salt: str) -> str:
    """Descifra una contraseña desde base64."""
    key = derive_fernet_key(passphrase, salt)
    f = Fernet(key)
    return f.decrypt(encrypted_b64.encode("utf-8")).decode("utf-8")
