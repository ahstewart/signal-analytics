#!/usr/bin/env python3

import os
import json

from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA1
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

def aes_decrypt_cbc(key, iv, data):
	cipher = AES.new(key, AES.MODE_CBC, iv)
	return cipher.decrypt(data)

password = ""

prefix = b'v10'
salt = 'saltysalt'
derived_key_len = 128 // 8
num_iterations = 1003
iv = b' ' * 16
config_file_path = 'C:\\Users\\ahste\\AppData\\Roaming\\Signal\\config.json'

with open(os.path.expanduser(config_file_path), 'r') as f:
	config = json.loads(f.read())
encrypted_key = bytes.fromhex(config['encryptedKey'])
assert encrypted_key.startswith(prefix)
encrypted_key = encrypted_key[len(prefix):]

kek = PBKDF2(password, salt, dkLen = derived_key_len, count = num_iterations, hmac_hash_module = SHA1)
decrypted_key = unpad(aes_decrypt_cbc(kek, iv, encrypted_key), block_size = 16).decode('ascii')
print('0x' + decrypted_key)