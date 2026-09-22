import asyncio
import hashlib
from ps4debug import PS4Debug

PS4_IP = "your ps4 ip"

async def main():
    ps4 = PS4Debug(PS4_IP)
    print(f"[*] Connecting to PS4 at {PS4_IP}...")

    processes = await ps4.get_processes()
    pid = None
    for proc in processes:
        name = getattr(proc, "name", str(proc)).lower()
        if "eboot.bin" in name:
            pid = getattr(proc, "pid", None)
            break

    if not pid:
        print("[-] eboot.bin not found!")
        return

    print(f"[+] Target PID: {pid}")
    maps = await ps4.get_process_maps(pid)
    
    # We're looking for a buffer that:
    # 1. Is approximately the same size as our save (~514KB)
    # 2. Does NOT contain "SGTA50000" (meaning it's encrypted)
    # 3. Is in writable memory (the send buffer)
    
    print("[*] Scanning for ENCRYPTED save buffer in RAM...")
    print("[*] TRIGGER A SAVE IN-GAME NOW (change clothes, buy something, etc.)")
    print("[*] Looking for ~500KB encrypted blob without SGTA magic...")
    
    decrypted_size = 525452  # Size of our decrypted save
    size_tolerance = 50000  # Allow ±50KB variance
    
    candidates = []
    
    for m in maps:
        start = getattr(m, "start", getattr(m, "base", 0))
        end = getattr(m, "end", 0)
        prot = getattr(m, "prot", 0)
        length = end - start

        # Look for writable buffers close to our save size
        if (prot & 3 == 3) and (abs(length - decrypted_size) < size_tolerance) and length > 100000:
            try:
                data = await ps4.read_memory(pid, start, length)
                
                # Check if it does NOT contain the decrypted magic
                if b"SGTA50000" not in data and b"MP Stats" not in data:
                    # Check if it looks like encrypted data (high entropy)
                    # Simple heuristic: count unique bytes in first 1KB
                    sample = data[:1024]
                    unique_bytes = len(set(sample))
                    
                    if unique_bytes > 200:  # High entropy = likely encrypted
                        candidates.append((start, length, data, unique_bytes))
                        print(f"\n[+] ENCRYPTED CANDIDATE at 0x{start:X}!")
                        print(f"    Size: {length} bytes")
                        print(f"    Entropy: {unique_bytes}/256 unique bytes in first 1KB")
                        print(f"    First 64 bytes: {data[:64].hex()}")
                        
                        # Save it
                        fname = f"encrypted_live_capture_0x{start:X}.bin"
                        with open(fname, "wb") as f:
                            f.write(data)
                        print(f"    Saved to: {fname}")
                        
            except Exception:
                continue

    print("\n" + "="*70)
    if candidates:
        print(f"[+] Found {len(candidates)} encrypted save candidates!")
        print("[*] Compare these against the RC4-encrypted versions from Step 1")
        print("    to find the correct key.")
        
        # Compare first 64 bytes of each candidate against our encrypted versions
        print("\n[*] Comparing against RC4-encrypted versions...")
        import os
        for fname in os.listdir("."):
            if fname.startswith("encrypted_save_") and fname.endswith(".bin"):
                with open(fname, "rb") as f:
                    our_encrypted = f.read(64)
                for addr, size, data, entropy in candidates:
                    if data[:64] == our_encrypted:
                        print(f"    ✅ MATCH! {fname} matches live capture at 0x{addr:X}")
    else:
        print("[-] No encrypted candidates found.")
        print("[*] Make sure you triggered a save while the script was running.")
        print("[*] Try again: change clothes or buy a cheap item in-game.")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
