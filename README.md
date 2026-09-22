```
██████╗ ██████╗ ██╗   ██╗██████╗ ███╗   ██╗
██╔══██╗╚═██╔═╝ ╚██╗ ██╔╝╚═══██╗████╗  ██║
██████╔╝  ██║    ╚████╔╝  █████╔╝██╔██╗ ██║
██╔══██╗  ██║     ╚██╔╝   ╚═══██╗██║╚██╗██║
██║  ██║██████╗    ██║   ██████╔╝██║ ╚████║
╚═╝  ╚═╝╚═════╝    ╚═╝   ╚═════╝ ╚═╝  ╚═══╝
```

# Los Santos Online (LSO) Save Extractor & Decryptor

A suite of reverse engineering tools designed to analyze, extract, download, and decrypt *Los Santos Online* (LSO) / Grand Theft Auto V PS4 save files directly from game memory and cloud servers.

---

## 📌 Overview & Workflow

This repository documents the complete pipeline required to extract live authentication tokens from a running PS4 memory space, pull the official master copy of a character's save file from LSO servers, and decrypt the proprietary payload locally.

```
┌────────────────────────┐     ┌────────────────────────┐
│   Phase 1: PS4 RAM     │ ──> │  Phase 2: Server Download│
│ (ps4debug + Creds)     │     │   (Wget + Master Save) │
└────────────────────────┘     └────────────────────────┘
            │                               │
            ▼                               ▼
┌────────────────────────┐     ┌────────────────────────┐
│ Phase 4: Verification  │ <── │  Phase 3: Decryptor    │
│  (Byte-for-Byte Match) │     │   (RC4 + SHA1 Cipher)  │
└────────────────────────┘     └────────────────────────┘
```

---

## 🚀 Execution Phases

### Phase 1: RAM Extractor
- Connects to the target PS4 running the `ps4debug` payload over local network.
- Scans process memory to identify the target `eboot.bin` PID.
- Extracts live active session credentials:
  - `SessionTicket`
  - `SessionKey`
  - `RockstarId`
- Dumps the raw, unencrypted active save file directly from the PS4's system RAM.

### Phase 2: Server Download
- Takes the live session credentials extracted during Phase 1.
- Formulates authentic HTTP requests to query the remote LSO cloud services.
- Downloads the encrypted master save file payload using `wget` / custom socket handlers.

### Phase 3: The Decryptor
- Implements the reverse-engineered LSO server cipher logic in Python.
- Translates the proprietary **RC4 + SHA1 block-cipher** routine used by the server to process cloud save files.
- Decrypts the raw cloud save archive locally into readable/usable game assets.

### Phase 4: Verification
- Performs a byte-for-byte binary diff comparison between:
  1. The live RAM dump captured directly from PS4 memory (Phase 1).
  2. The server-downloaded file decrypted by the Python script (Phase 3).
- Validates the decryption implementation by confirming identical output between memory state and cloud storage.

---

## ⚠️ Disclaimers & Technical Notes

1. **Forgotten Credentials Notice:**
   - Some python scripts or log dumps in this repository may contain leftover session tickets, keys, or tokens.
   - **All sessions, accounts, and passwords associated with these dumps have been completely reset.** These hardcoded values are strictly non-functional, invalid, and provided solely for historical context and schema analysis.so don't waste your time :)

2. **Status of `upload_save.py`:**
   - The script `upload_save.py` is **non-functional** and will fail due to a **CA signature mismatch** when attempting to transmit modified saves back to the cloud.
   - Modifying or uploading save files is **explicitly outside the scope of this project**. This repository exists strictly for reverse engineering, save downloading, and local decryption research.

---

## 🛠️ Usage Quickstart

```bash
# Clone repository
git clone https://github.com/R1y3n/LSOmpServer.git
cd LSOmpServer

# Stage & execute main handler script
python3 main.py
```
