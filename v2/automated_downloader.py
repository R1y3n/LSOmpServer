import asyncio
import base64
import struct
import ssl
import urllib.request
import hashlib
import re
import os
from datetime import datetime
from ps4debug import PS4Debug

# =====================================================================
# CONFIGURATION (Only 2 hardcoded values allowed!)
# =====================================================================
PS4_IP = "change_with_your_ps4_local_ip_addr_here" #your ps4 ip addr here
# PS4 Platform Key from GTAEncryption.js
PS4_PLATFORM_KEY_B64 = "C6i91R73oCD3qt1kUh0UIkDTu3Su5Qa7/r74q5ohUj1UxX/yQz7qB8a4y2TXfCMxqJo31tOPuZJMwG3jupDl7rs=" #this is a gift from reverse engineering dont edit it  :)

# =====================================================================
# SHARED STATE
# =====================================================================
state = {
    "ticket": None,
    "session_key": None,
    "rockstar_id": None,
    "scs_ticket": None,
    "ram_dumped": False,
    "server_downloaded": False,
    "seen_http": set()
}

# =====================================================================
# CRYPTOGRAPHY ENGINE (Translated from GTAEncryption.js)
# =====================================================================
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

def decrypt_save_data(enc_data, session_key_b64):
    platform_key = base64.b64decode(PS4_PLATFORM_KEY_B64)
    rc4key = platform_key[1:33]
    xorkey = rc4_crypt(rc4key, platform_key[33:49])
    session_key = base64.b64decode(session_key_b64)
    
    enc_key = bytearray(enc_data[:16])
    for i in range(16):
        enc_key[i] ^= session_key[i]
        enc_key[i] ^= xorkey[i]
        
    rc4 = StatefulRC4(bytes(enc_key))
    dec_block_size = rc4.crypt(enc_data[16:20])
    block_size = struct.unpack('>I', dec_block_size)[0]
    
    pos = 20
    decrypted = bytearray()
    while pos < len(enc_data):
        block = enc_data[pos:pos+block_size]
        if not block: break
        decrypted.extend(rc4.crypt(block))
        pos += block_size
        if pos + 20 <= len(enc_data): pos += 20 # Skip SHA1 hash
        
    return bytes(decrypted)

# =====================================================================
# NETWORK & DOWNLOAD ENGINE
# =====================================================================
def build_user_agent(rid):
    kvp = f"e=1,t=gta5,p=ps4,v=1,s=123456789,a={rid}"
    prefix = bytes([0x12, 0x34, 0x56, 0x78])
    obfuscated = bytearray(kvp.encode('utf-8'))
    for i in range(len(obfuscated)): obfuscated[i] ^= prefix[i % 4]
    return f"ros {base64.b64encode(prefix + bytes(obfuscated)).decode('ascii')}"

def download_and_decrypt_sync(rid, ticket, session_key):
    url = f"https://prod.ps4.lossantosonline.com/cloud/11/cloudservices/members/np/{rid}/GTA5/saves/mpstats/save_char0001_ps4.save"
    ua = build_user_agent(rid)
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, method='GET')
    req.add_header('User-Agent', ua)
    req.add_header('ros-SessionTicket', ticket)
    req.add_header('Host', 'prod.ps4.lossantosonline.com')
    
    print(f"\n[NET] Contacting LSO Cloud Servers...")
    with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
        enc_data = response.read()
        print(f"[NET] Downloaded {len(enc_data)} bytes (Encrypted RPF7 Archive)")
        
        with open("server_encrypted_save.bin", "wb") as f: f.write(enc_data)
        
        print(f"[CRYPTO] Decrypting with SessionKey...")
        dec_data = decrypt_save_data(enc_data, session_key)
        
        with open("server_decrypted_save.rpf7", "wb") as f: f.write(dec_data)
        print(f"[SUCCESS] Decrypted Server Save saved to: server_decrypted_save.rpf7 ({len(dec_data)} bytes)")
        if dec_data[:4] == b'7FPR' or b'SGTA5' in dec_data[:100]:
            print(f"[VERIFY] Magic header verified! Archive is valid.")

# =====================================================================
# ASYNC TASKS (RAM Scanner, HTTP Sniffer, Orchestrator)
# =====================================================================
async def ram_scanner(ps4, pid):
    print("[RAM] Initializing continuous memory scanner...")
    maps_cache = []
    last_map_fetch = 0
    
    while True:
        try:
            # Refresh memory maps every 30 seconds to catch new allocations
            if not maps_cache or (asyncio.get_event_loop().time() - last_map_fetch > 30):
                maps_cache = await ps4.get_process_maps(pid)
                last_map_fetch = asyncio.get_event_loop().time()
                
            for m in maps_cache:
                start = getattr(m, "start", 0)
                end = getattr(m, "end", 0)
                prot = getattr(m, "prot", 0)
                length = end - start
                
                if not (0 < length <= 64 * 1024 * 1024): continue
                
                try:
                    data = await ps4.read_memory(pid, start, length)
                    
                    # 1. Hunt Credentials
                    if not state["ticket"]:
                        m_ticket = re.search(rb'ros-SessionTicket:\s*([A-Za-z0-9+/=]+)', data)
                        if m_ticket: 
                            state["ticket"] = m_ticket.group(1).decode()
                            print(f"[RAM] >>> FOUND SessionTicket: {state['ticket'][:40]}...")
                            
                    if not state["session_key"]:
                        m_skey = re.search(rb'<SessionKey>(.*?)</SessionKey>', data)
                        if m_skey: 
                            state["session_key"] = m_skey.group(1).decode()
                            print(f"[RAM] >>> FOUND SessionKey: {state['session_key']}")
                            
                    if not state["rockstar_id"]:
                        m_rid = re.search(rb'<RockstarId>(.*?)</RockstarId>', data)
                        if m_rid: 
                            state["rockstar_id"] = m_rid.group(1).decode()
                            print(f"[RAM] >>> FOUND RockstarId: {state['rockstar_id']}")

                    # 2. Hunt Decrypted Save in Writable Memory
                    if not state["ram_dumped"] and (prot & 3 == 3):
                        idx = data.find(b"SGTA50000")
                        if idx != -1:
                            print(f"[RAM] >>> FOUND LIVE DECRYPTED SAVE at 0x{start+idx:X}!")
                            save_start = max(0, idx - 2048)
                            save_end = min(len(data), idx + 512 * 1024)
                            save_blob = data[save_start:save_end]
                            while save_blob and save_blob[-1] == 0: save_blob = save_blob[:-1]
                            
                            if len(save_blob) > 50000:
                                with open("ram_decrypted_save.bin", "wb") as f: f.write(save_blob)
                                print(f"[SUCCESS] RAM Dump saved to: ram_decrypted_save.bin ({len(save_blob)} bytes)")
                                state["ram_dumped"] = True
                                
                except Exception:
                    continue
                    
            await asyncio.sleep(1.5)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[RAM] Scanner error: {e}. Reconnecting...")
            await asyncio.sleep(3)

async def http_sniffer(ps4, pid):
    print("[NET] Initializing live HTTP endpoint sniffer...")
    maps_cache = []
    
    while True:
        try:
            if not maps_cache:
                maps = await ps4.get_process_maps(pid)
                maps_cache = [m for m in maps if ("http" in getattr(m, "name", "").lower() or "ssl" in getattr(m, "name", "").lower()) and getattr(m, "prot", 0) & 3 == 3]
                
            for m in maps_cache:
                start = getattr(m, "start", 0)
                length = getattr(m, "end", 0) - start
                if length > 20 * 1024 * 1024: continue
                
                try:
                    data = await ps4.read_memory(pid, start, length)
                    for trigger in [b"GET /", b"POST /", b"PUT /"]:
                        idx = data.find(trigger)
                        if idx != -1 and b"lossantosonline.com" in data[idx:idx+500]:
                            snippet = data[idx:idx+200].decode("utf-8", errors="ignore")
                            clean = "".join(c for c in snippet if c.isprintable())
                            h = hashlib.md5(clean.encode()).hexdigest()
                            if h not in state["seen_http"]:
                                state["seen_http"].add(h)
                                url_match = re.search(r'(?:GET|POST|PUT)\s+(/[^\s]+)', clean)
                                if url_match:
                                    print(f"[HTTP] >>> Intercepted Live Request: {url_match.group(1)}")
                except Exception:
                    continue
            await asyncio.sleep(2)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(3)

async def orchestrator():
    print("="*60)
    print(f" LSO MASTER PIPELINE | Target: {PS4_IP}")
    print("="*60)
    ps4 = PS4Debug(PS4_IP)
    
    while True:
        try:
            processes = await ps4.get_processes()
            pid = next((getattr(p, "pid") for p in processes if "eboot.bin" in getattr(p, "name", "").lower()), None)
            if pid: break
            print("[SYS] Waiting for eboot.bin to start...")
            await asyncio.sleep(3)
        except Exception:
            print("[SYS] PS4 connection lost. Retrying...")
            await asyncio.sleep(3)
            
    print(f"[SYS] Locked onto eboot.bin (PID: {pid})")
    
    # Launch background scanners
    scanner_task = asyncio.create_task(ram_scanner(ps4, pid))
    http_task = asyncio.create_task(http_sniffer(ps4, pid))
    
    try:
        # Wait for credentials
        print("[WAIT] Hunting for authentication credentials in RAM...")
        while not (state["ticket"] and state["session_key"] and state["rockstar_id"]):
            await asyncio.sleep(1)
            
        print("\n" + "="*60)
        print(" CREDENTIALS ACQUIRED. INITIATING SERVER DOWNLOAD.")
        print("="*60)
        
        # Run blocking download/decrypt in thread to not block asyncio
        await asyncio.to_thread(
            download_and_decrypt_sync, 
            state["rockstar_id"], 
            state["ticket"], 
            state["session_key"]
        )
        state["server_downloaded"] = True
        
        # Wait for RAM dump
        print("\n[WAIT] Waiting for live decrypted save to appear in RAM...")
        while not state["ram_dumped"]:
            await asyncio.sleep(1)
            
        print("\n" + "="*60)
        print(" PIPELINE EXECUTION COMPLETE!")
        print("="*60)
        print(" Generated Files:")
        print("  1. server_encrypted_save.bin (Raw from LSO Cloud)")
        print("  2. server_decrypted_save.rpf7 (Decrypted RPF7 Archive)")
        print("  3. ram_decrypted_save.bin (Live Memory Dump)")
        print("="*60)
        
        # Keep alive so HTTP sniffer continues running
        while True:
            await asyncio.sleep(10)
            
    except asyncio.CancelledError:
        pass
    finally:
        scanner_task.cancel()
        http_task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(orchestrator())
    except KeyboardInterrupt:
        print("\n[SYS] Pipeline terminated by user.")
