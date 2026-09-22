import base64
import hashlib
import struct
import os
import sys

# The hardcoded PS4 Platform Key from GTAEncryption.js
PS4_PLATFORM_KEY_B64 = "you can find those from the LSO's github repo"

def rc4_crypt(key, data):
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) % 256
        S[i], S[j] = S[j], S[i]
    i = j = 0
    res = bytearray(len(data))
    for y in range(len(data)):
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        res[y] = data[y] ^ S[(S[i] + S[j]) % 256]
    return bytes(res)

class StatefulRC4:
    def __init__(self, key):
        self.S = list(range(256))
        j = 0
        for i in range(256):
            j = (j + self.S[i] + key[i % len(key)]) % 256
            self.S[i], self.S[j] = self.S[j], self.S[i]
        self.i = 0
        self.j = 0
        
    def crypt(self, data):
        res = bytearray(len(data))
        for y in range(len(data)):
            self.i = (self.i + 1) % 256
            self.j = (self.j + self.S[self.i]) % 256
            self.S[self.i], self.S[self.j] = self.S[self.j], self.S[self.i]
            res[y] = data[y] ^ self.S[(self.S[self.i] + self.S[self.j]) % 256]
        return bytes(res)

class GTACrypto:
    def __init__(self, session_key_b64):
        platform_key = base64.b64decode(PS4_PLATFORM_KEY_B64)
        self.rc4key = platform_key[1:33]
        self.xorkey = rc4_crypt(self.rc4key, platform_key[33:49])
        self.hashkey = rc4_crypt(self.rc4key, platform_key[49:])
        self.session_key = base64.b64decode(session_key_b64) if session_key_b64 else b""

    def encrypt(self, raw_data):
        original_key = os.urandom(16)
        enc_key = bytearray(original_key)
        
        if self.session_key:
            for i in range(16): enc_key[i] ^= self.session_key[i]
        for i in range(16): enc_key[i] ^= self.xorkey[i]
            
        full_buffer = bytearray(bytes(enc_key))
        rc4 = StatefulRC4(original_key)
        
        # Encrypt block size (1024)
        full_buffer.extend(rc4.crypt(struct.pack('>I', 1024)))
        
        # Encrypt data in 1024-byte blocks + SHA1 hashes
        for i in range(0, len(raw_data), 1024):
            block = raw_data[i:i+1024]
            enc_block = rc4.crypt(block)
            full_buffer.extend(enc_block)
            
            h = hashlib.sha1()
            h.update(enc_block)
            h.update(self.hashkey)
            full_buffer.extend(h.digest())
            
        return bytes(full_buffer)

if __name__ == "__main__":
    # Your SessionKey from RAM
    SESSION_KEY = "your session key here"
    crypto = GTACrypto(SESSION_KEY)
    
    if len(sys.argv) < 3:
        print("Usage: python3 gta_crypto.py <input_file> <output_file>")
        sys.exit(1)
        
    with open(sys.argv[1], "rb") as f:
        data = f.read()
        
    encrypted = crypto.encrypt(data)
    with open(sys.argv[2], "wb") as f:
        f.write(encrypted)
    print(f"[+] Encrypted {len(data)} bytes -> {len(encrypted)} bytes")
