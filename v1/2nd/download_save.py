import ssl
import urllib.request
import base64
import os
import sys

# Your session data from RAM
SESSION_TICKET = "YOUR SESSION TICKET ERE"
SCS_TICKET = "YOUR SCS TICKET HERE"
SC_ID = "YOUR PLAYER ID HERE (same as user id)"
SAVE_FILENAME = "save_char0001_ps4.save" # keep this one as hardcoded by lso

# Construct the User-Agent in the format the server expects
# Format: "ros " + base64(4_random_bytes + XOR_obfuscated(kvp_string))
def build_user_agent():
    kvp = "e=1,t=gta5,p=ps4,v=1,s=7564577543485193216,a=73059427"
    kvp_bytes = kvp.encode('utf-8')
    
    # 4 random prefix bytes
    prefix = bytes([0x12, 0x34, 0x56, 0x78])
    
    # XOR obfuscate the payload with the prefix bytes
    obfuscated = bytearray(kvp_bytes)
    for i in range(len(obfuscated)):
        obfuscated[i] ^= prefix[i % 4]
    
    # Combine: prefix + obfuscated payload
    payload = prefix + bytes(obfuscated)
    
    # Base64 encode
    b64 = base64.b64encode(payload).decode('ascii')
    
    return f"ros {b64}"

def download_save():
    url = f"https://prod.ps4.lossantosonline.com/cloud/11/cloudservices/members/np/{SC_ID}/GTA5/saves/mpstats/{SAVE_FILENAME}"
    
    user_agent = build_user_agent()
    print(f"[*] URL: {url}")
    print(f"[*] User-Agent: {user_agent}")
    print(f"[*] SessionTicket: {SESSION_TICKET[:40]}...")
    
    # Create SSL context that skips cert verification (server uses custom cert)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, method='GET')
    req.add_header('User-Agent', user_agent)
    req.add_header('ros-SessionTicket', SESSION_TICKET)
    req.add_header('Scs-Ticket', SCS_TICKET)
    req.add_header('Host', 'prod.ps4.lossantosonline.com')
    
    try:
        print(f"\n[*] Sending GET request...")
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            status = response.status
            headers = dict(response.headers)
            data = response.read()
            
            print(f"[+] HTTP Status: {status}")
            print(f"[+] Content-Length: {len(data)} bytes")
            print(f"[+] Content-Type: {headers.get('Content-Type', 'unknown')}")
            print(f"[+] First 64 bytes (hex): {data[:64].hex()}")
            
            # Save the encrypted response
            outfile = "server_encrypted_save.bin"
            with open(outfile, "wb") as f:
                f.write(data)
            print(f"\n[+] Saved encrypted save to: {outfile}")
            print(f"[+] Size: {len(data)} bytes")
            
            # Check if it looks encrypted (high entropy) or plaintext
            sample = data[:64]
            if b"SGTA5" in data[:100]:
                print("[!] WARNING: Response appears to be PLAINTEXT (not encrypted)")
            else:
                print("[+] Response appears to be ENCRYPTED (as expected)")
            
            return True
            
    except urllib.error.HTTPError as e:
        print(f"[-] HTTP Error: {e.code}")
        print(f"[-] Reason: {e.reason}")
        body = e.read()
        if body:
            print(f"[-] Response body: {body[:500]}")
        return False
    except Exception as e:
        print(f"[-] Error: {e}")
        return False

if __name__ == "__main__":
    download_save()
