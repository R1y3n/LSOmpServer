import asyncio
from ps4debug import PS4Debug

PS4_IP = "your ps4 ip here"

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
        print("[-] eboot.bin not found! Make sure GTA V is running.")
        return

    print(f"[+] Target PID: {pid}")
    maps = await ps4.get_process_maps(pid)
    
    # GTA V save files in memory contain these identifiers
    markers = [b"SGTA5", b"MP Stats_0001"]
    
    print("[*] Scanning for decrypted GTA V save file in writable RAM...")
    print("[*] (Make sure you are fully loaded into LSO online)")
    
    found_saves = []

    for m in maps:
        start = getattr(m, "start", getattr(m, "base", 0))
        end = getattr(m, "end", 0)
        prot = getattr(m, "prot", 0)
        length = end - start

        # ONLY scan readable+writable heap memory (prot & 3 == 3)
        # This skips the read-only code segments where the static string tables live
        if (prot & 3 == 3) and (0 < length <= 128 * 1024 * 1024):
            try:
                data = await ps4.read_memory(pid, start, length)
                
                for marker in markers:
                    idx = 0
                    while True:
                        idx = data.find(marker, idx)
                        if idx == -1:
                            break
                        
                        abs_addr = start + idx
                        
                        # Extract a large chunk around the marker
                        save_start = max(0, idx - 2048)
                        save_end = min(len(data), idx + 512 * 1024) # Read up to 512KB forward
                        save_blob = data[save_start:save_end]
                        
                        # Trim trailing null bytes
                        while save_blob and save_blob[-1] == 0:
                            save_blob = save_blob[:-1]
                        
                        # Real save files are large (usually > 50KB)
                        if len(save_blob) > 50000:
                            fname = f"save_dump_{marker.decode(errors='ignore')}_0x{abs_addr:X}.bin"
                            with open(fname, "wb") as f:
                                f.write(save_blob)
                            
                            print(f"\n[+] FOUND LIVE SAVE DATA at 0x{abs_addr:X}!")
                            print(f"    Dumped {len(save_blob)} bytes to {fname}")
                            print(f"    First 64 bytes: {save_blob[:64].hex()}")
                            
                            # Preview readable strings
                            sample = save_blob[:2048].decode("utf-8", errors="ignore")
                            readable = "".join(c if c.isprintable() else "." for c in sample)
                            print(f"    Preview: {readable[:200]}")
                            
                            found_saves.append(fname)
                        
                        idx += len(marker)
                        
            except Exception:
                continue

    print("\n" + "="*70)
    if found_saves:
        print(f"[+] SUCCESS! Found {len(found_saves)} live save file candidates in RAM:")
        for f in found_saves:
            print(f"    • {f}")
        print("\n[+] These are your DECRYPTED save files pulled directly from the game's working memory.")
    else:
        print("[-] No large save data found in writable memory.")
        print("[*] Make sure you are fully loaded into LSO online (not in a loading screen).")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
