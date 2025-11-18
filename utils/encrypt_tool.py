from utils.crypto import encrypt_password

# Configurar:
passphrase = "MiPassphraseSegura$$2025"
salt = "SIS-ARIAS"
password_to_encrypt = "ariasyArias@$%$"  # contraseña real de MySQL

encrypted = encrypt_password(password_to_encrypt, passphrase, salt)
print("Copia y pega en appsettings.json:\n")
print(encrypted)
