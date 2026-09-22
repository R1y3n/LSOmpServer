import base64
import hashlib
import sys

def rc4(key, data):
    """RC4 encryption/decryption"""
    S = list(range(256))
    j = 0
    key_bytes = key if isinstance(key, bytes) else key.encode()
    
    for i in range(256):
        j = (j + S[i] + key_bytes[i % len(key_bytes)]) % 256
        S[i], S[j] = S[j], S[i]
    
    i = j = 0
    result = bytearray()
    for byte in data:
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        result.append(byte ^ S[(S[i] + S[j]) % 256])
    
    return bytes(result)

# Read the decrypted save
with open("save_dump_SGTA5_0x38D9B48.bin", "rb") as f:
    decrypted_save = f.read()

print(f"[*] Loaded decrypted save: {len(decrypted_save)} bytes")
print(f"[*] First 32 bytes (decrypted): {decrypted_save[:32].hex()}")

# Keys we found in RAM
keys_to_try = [
    ("CloudKey (base64)", base64.b64decode("lso cloud key here in b64")),
    ("SessionKey (raw)", b"your sess key here"),
    ("SessionKey (base64)", base64.b64decode("your sesskey here in base64")),
    ("SessionTicket (first 32 bytes)", base64.b64decode("your sess tickt here")[:32]),
]

for name, key in keys_to_try:
    print(f"\n[*] Trying key: {name}")
    print(f"    Key hex: {key.hex()}")
    
    encrypted = rc4(key, decrypted_save)
    
    fname = f"encrypted_save_{name.split(' ')[0].lower()}.bin"
    with open(fname, "wb") as f:
        f.write(encrypted)
    
    print(f"    First 32 bytes (encrypted): {encrypted[:32].hex()}")
    print(f"    Saved to: {fname}")
    
    # Verify: decrypting should give us back the original
    decrypted_back = rc4(key, encrypted)
    if decrypted_back[:64] == decrypted_save[:64]:
        print(f"    ✅ RC4 round-trip verified (encrypt→decrypt matches)")
    else:
        print(f"    ❌ Round-trip failed")

print("\n[+] Done. The encrypted files are ready.")
print("[*] To verify which one matches the server's expectation,")
print("    you'll need to compare against a live capture (Step 2).")
