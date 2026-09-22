import asyncio
from ps4debug import PS4Debug

PS4_IP = "your ps4 ip here"

async def main():
    ps4 = PS4Debug(PS4_IP)
    print(f"[*] Connecting to PS4 at {PS4_IP}...")
    processes = await ps4.get_processes()
    pid = next((getattr(p, "pid") for p in processes if "eboot.bin" in getattr(p, "name", "").lower()), None)
    if not pid:
        print("[-] eboot.bin not found!")
        return
        
    print(f"[+] Targeting eboot.bin (PID: {pid})")
    maps = await ps4.get_process_maps(pid)
    
    # GTA V save files start with the magic header "SGTA5"
    magic = b"SGTA5"
    
    print("[*] Hunting for decrypted GTA V save file (SGTA5) in RAM...")
    
    for m in maps:
        start = getattr(m, "start", 0)
        end = getattr(m, "end", 0)
        prot = getattr(m, "prot", 0)
        length = end - start
        
        # Only scan large, readable/writable heaps where the game loads assets/saves
        if (prot & 3 == 3) and (length > 10 * 1024 * 1024) and (length < 512 * 1024 * 1024):
            try:
                # Read in chunks to avoid timeout
                chunk_size = 32 * 1024 * 1024
                for i in range(0, length, chunk_size):
                    read_len = min(chunk_size, length - i)
                    data = await ps4.read_memory(pid, start + i, read_len)
                    idx = data.find(magic)
                    if idx != -1:
                        print(f"\n[!] FOUND 'SGTA5' MAGIC HEADER at 0x{start + i + idx:X}!")
                        # Dump 2MB starting from the magic header (save files are usually < 2MB)
                        save_data = await ps4.read_memory(pid, start + i + idx, 2 * 1024 * 1024)
                        with open("decrypted_save_file.save", "wb") as f:
                            f.write(save_data)
                        print(f"[+] SUCCESS! Dumped 2MB to 'decrypted_save_file.save'")
                        return
            except Exception:
                continue
                
    print("[-] Could not find 'SGTA5' in RAM. The save might be compressed or use a different magic.")

if __name__ == "__main__":
    asyncio.run(main())
