import bcrypt

import secrets 
print(secrets.token_hex(32))

password = b'password'
hashed = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))
print(hashed.decode())