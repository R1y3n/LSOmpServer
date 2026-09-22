import base64

# Your exact credentials
SESSION_KEY_B64 = "your sessionkey here"
PLATFORM_KEY_B64 = "your platform key here"

def rc4_init(key: bytes):
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) % 256
        s[i], s[j] = s[j], s[i]
    return s

def rc4_decrypt_step(s_state, data: bytes):
    s = s_state[:]
    i = 0
    j = 0
    res = bytearray(len(data))
    for y in range(len(data)):
        i = (i + 1) % 256
        j = (j + s[i]) % 256
        s[i], s[j] = s[j], s[i]
        res[y] = data[y] ^ s[(s[i] + s[j]) % 256]
    return bytes(res), s

def decrypt_lso_save(encrypted_data: bytes, session_key_b64: str):
    platform_key = base64.b64decode(PLATFORM_KEY_B64)
    rc4key = platform_key[1:33]
    
    # Step 1: Get XOR key
    s_xor = rc4_init(rc4key)
    xorkey, _ = rc4_decrypt_step(s_xor, platform_key[33:49])
    
    # Step 2: Derive final RC4 key
    key = bytearray(encrypted_data[:16])
    for i in range(len(key)):
        key[i] ^= xorkey[i]
        
    sk = base64.b64decode(session_key_b64)
    for i in range(len(key)):
        key[i] ^= sk[i]
        
    # Step 3: Decrypt payload
    s_main = rc4_init(bytes(key))
    _, s_main = rc4_decrypt_step(s_main, encrypted_data[16:20]) # Skip 4-byte block marker
    
    pos = 20
    chunks = []
    enc_len = len(encrypted_data)
    while pos < enc_len:
        remaining = enc_len - pos
        take = min(1024, remaining - 20)
        if take <= 0:
            break
        chunk, s_main = rc4_decrypt_step(s_main, encrypted_data[pos : pos + take])
        chunks.append(chunk)
        pos += take + 20
        
    return b"".join(chunks)

print("[*] Reading captured save file...")
try:
    with open("/home/hp/chouchou/captured_online_save.bin", "rb") as f:
        save_data = f.read()
        
    print(f"[*] File size: {len(save_data)} bytes")
    
    # Check if it's already raw multipart (unencrypted HTTP body)
    if b"filename=" in save_data and b"Content-Disposition" in save_data:
        print("[*] File is raw multipart HTTP. Extracting payload...")
        idx = save_data.find(b"filename=")
        start = save_data.find(b"\r\n\r\n", idx)
        if start != -1:
            content = save_data[start+4:]
            if content.endswith(b"\r\n"):
                content = content[:-2]
            with open("/home/hp/chouchou/extracted_save.bin", "wb") as f:
                f.write(content)
            print(f"[+] Extracted {len(content)} bytes to extracted_save.bin")
        else:
            print("[-] Could not find payload start.")
    else:
        print("[*] File appears encrypted. Decrypting with provided SessionKey...")
        decrypted_save = decrypt_lso_save(save_data, SESSION_KEY_B64)
        
        with open("/home/hp/chouchou/decrypted_save.bin", "wb") as f:
            f.write(decrypted_save)
        print(f"[+] Successfully decrypted to decrypted_save.bin ({len(decrypted_save)} bytes)")
        
        # Validate
        if b"SGTA5" in decrypted_save or b"SAVEDATA" in decrypted_save or b"Rockstar" in decrypted_save:
            print("[!] SAVE FILE SUCCESSFULLY DECRYPTED AND VALIDATED!")
        else:
            print("[*] Decrypted. Checking raw header to verify...")
            print("First 100 bytes (hex):", decrypted_save[:100].hex())
            print("First 100 bytes (ascii):", decrypted_save[:100])
            
except Exception as e:
    print(f"[-] Failed to process save file: {e}")
    import traceback
    traceback.print_exc()
