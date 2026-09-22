import asyncio
import re
from ps4debug import PS4Debug

PS4_IP = "your_ps4_ip"

async def main():
    ps4 = PS4Debug(PS4_IP)
    print(f"[*] Connecting to PS4 at {PS4_IP}...")

    # 1. Dynamically fetch the PID for eboot.bin
    try:
        processes = await ps4.get_processes()
    except Exception as e:
        print(f"[-] Failed to get process list: {e}")
        return

    pid = None
    for proc in processes:
        proc_name = getattr(proc, "name", str(proc)).lower()
        if "eboot.bin" in proc_name:
            pid = getattr(proc, "pid", None)
            print(f"[+] Found 'eboot.bin' (PID: {pid})")
            break

    if pid is None:
        print("[-] Error: 'eboot.bin' not found. Make sure GTA V is running!")
        return

    # 2. Get memory maps for the correct PID
    print(f"[*] Fetching memory maps for PID {pid}...")
    maps = await ps4.get_process_maps(pid)
    
    # Target the actual Rockstar/LSO game server traffic
    keywords = [
        b"mpstats", 
        b"ProfileStats", 
        b"cloudservices", 
        b"WriteStats", 
        b"ReadStats", 
        b"ros.rockstargames.com", 
        b"lossantosonline.com",
        b"SessionTicket",
        b"SessionKey"
    ]
    
    print(f"[*] Scanning RAM for Rockstar/LSO game server traffic...")
    print("[*] Trigger a save in-game (e.g., buy a mod, change clothes, save at apartment).")
    
    found_contexts = set()
    
    for m in maps:
        start = getattr(m, "start", getattr(m, "base", 0))
        end = getattr(m, "end", 0)
        prot = getattr(m, "prot", 0)
        length = end - start

        # Scan readable memory blocks up to 64MB
        if (prot & 1) and (0 < length <= 64 * 1024 * 1024):
            try:
                data = await ps4.read_memory(pid, start, length)
                
                for kw in keywords:
                    idx = 0
                    while True:
                        idx = data.find(kw, idx)
                        if idx == -1:
                            break
                        
                        # Extract 4096 bytes around the match to capture the full structure
                        window_start = max(0, idx - 2048)
                        window_end = min(len(data), idx + 2048)
                        snippet = data[window_start:window_end]
                        
                        # Save the raw binary for analysis
                        fname = f"rockstar_traffic_{kw.decode(errors='ignore')}_{idx}.bin"
                        with open(fname, "wb") as f:
                            f.write(snippet)
                        
                        text = snippet.decode("utf-8", errors="ignore")
                        clean = "".join(c for c in text if c.isprintable() or c in ['\n', '\r', '\t'])
                        
                        if clean not in found_contexts:
                            found_contexts.add(clean)
                            print(f"\n[+] FOUND ROCKSTAR/LSO TRAFFIC (Keyword: {kw.decode(errors='ignore')} at 0x{start+idx:X}):")
                            print(f"    Saved raw binary to {fname}")
                            
                            # Print any HTTP methods or paths
                            matches = re.findall(r'((?:GET|POST|PUT|DELETE)\s+/[^\s\x00]+|/cloud/11/[^\s\x00]+|/gta5/11/[^\s\x00]+)', clean)
                            if matches:
                                for match in matches:
                                    print(f"    URL/Path: {match}")
                            
                            # Print a snippet of the context
                            kw_str = kw.decode(errors='ignore')
                            context_start = max(0, clean.find(kw_str) - 100)
                            context_end = min(len(clean), clean.find(kw_str) + 200)
                            print(f"    Context: ...{clean[context_start:context_end]}...")
                        
                        idx += len(kw)
            except Exception:
                # Ignore read errors for protected/invalid memory regions
                continue

    print("\n" + "="*70)
    print(f"[+] SCAN COMPLETE. Found {len(found_contexts)} Rockstar/LSO contexts.")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
