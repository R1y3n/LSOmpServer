import ssl
import urllib.request
import base64

SESSION_TICKET = "your sesstickt here"
SCS_TICKET = "your scs ticket here"
SC_ID = "scsid aka playerid aka userid aka profileid"
SAVE_FILENAME = "save_char0001_ps4.save" #keep as default by lso

def build_user_agent():
    kvp = "e=1,t=gta5,p=ps4,v=1,s=7564577543485193216,a=73059427" #get your own ones these are no more valid (from the ram dump)
    prefix = bytes([0x12, 0x34, 0x56, 0x78])
    obfuscated = bytearray(kvp.encode('utf-8'))
    for i in range(len(obfuscated)): obfuscated[i] ^= prefix[i % 4]
    return f"ros {base64.b64encode(prefix + bytes(obfuscated)).decode('ascii')}"

def upload_save(encrypted_file):
    url = f"https://prod.ps4.lossantosonline.com/cloud/11/cloudservices/members/np/{SC_ID}/GTA5/saves/mpstats/{SAVE_FILENAME}"
    
    with open(encrypted_file, "rb") as f:
        encrypted_data = f.read()
        
    print(f"[*] Uploading {len(encrypted_data)} bytes to {url}...")
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, data=encrypted_data, method='POST')
    req.add_header('User-Agent', build_user_agent())
    req.add_header('ros-SessionTicket', SESSION_TICKET)
    req.add_header('Scs-Ticket', SCS_TICKET)
    req.add_header('Host', 'prod.ps4.lossantosonline.com')
    req.add_header('Content-Type', 'application/octet-stream')
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            print(f"[+] HTTP Status: {response.status}")
            print(f"[+] Server Response: {response.read().decode('utf-8', errors='ignore')}")
            print("\n[!!!] UPLOAD SUCCESSFUL! Your modified save is now on the server.")
    except urllib.error.HTTPError as e:
        print(f"[-] HTTP Error: {e.code} - {e.reason}")
        print(f"[-] Body: {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"[-] Error: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 upload_save.py <encrypted_save_file.bin>")
        sys.exit(1)
    upload_save(sys.argv[1])
