import base64
import struct

PS4_PLATFORM_KEY_B64 = "ps4 platform keys from lso repo"
SESSION_KEY_B64 = "your session key (both ps4 platform key & your session key must be in base 64 !!! "

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

def decrypt_save(input_file, output_file):
    with open(input_file, "rb") as f:
        data = f.read()
        
    print(f"[*] Loaded {len(data)} bytes from {input_file}")
    
    platform_key = base64.b64decode(PS4_PLATFORM_KEY_B64)
    rc4key = platform_key[1:33]
    xorkey = rc4_crypt(rc4key, platform_key[33:49])
    session_key = base64.b64decode(SESSION_KEY_B64)
    
    # 1. Extract and decrypt the 16-byte key
    enc_key = bytearray(data[:16])
    for i in range(16):
        enc_key[i] ^= session_key[i]
        enc_key[i] ^= xorkey[i]
        
    original_key = bytes(enc_key)
    print(f"[*] Derived RC4 Key: {original_key.hex()}")
    
    # 2. Initialize stateful RC4
    rc4 = StatefulRC4(original_key)
    
    # 3. Decrypt the 4-byte block size
    enc_block_size = data[16:20]
    dec_block_size = rc4.crypt(enc_block_size)
    block_size = struct.unpack('>I', dec_block_size)[0]
    print(f"[*] Block size: {block_size}")
    
    # 4. Decrypt the blocks
    pos = 20
    decrypted_data = bytearray()
    block_count = 0
    
    while pos < len(data):
        block = data[pos:pos+block_size]
        if not block: break
            
        dec_block = rc4.crypt(block)
        decrypted_data.extend(dec_block)
        
        pos += block_size
        block_count += 1
        
        # Skip the 20-byte SHA1 hash
        if pos + 20 <= len(data):
            pos += 20
            
    print(f"[+] Decrypted {block_count} blocks.")
    print(f"[+] Total decrypted size: {len(decrypted_data)} bytes")
    
    # Check for RPF7 magic
    if decrypted_data[:4] == b'7FPR':
        print("\n[!!!] SUCCESS: Decrypted file is a valid 7FPR (RPF7) Archive!")
    else:
        print(f"\n[*] Magic bytes: {decrypted_data[:4]}")
        
    with open(output_file, "wb") as f:
        f.write(decrypted_data)
    print(f"[+] Saved to {output_file}")

if __name__ == "__main__":
    decrypt_save("server_encrypted_save.bin", "server_save_decrypted.rpf7")
