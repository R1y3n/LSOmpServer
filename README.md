```
██████╗ ██████╗ ██╗   ██╗██████╗ ███╗   ██╗
██╔══██╗╚═██╔═╝ ╚██╗ ██╔╝╚═══██╗████╗  ██║
██████╔╝  ██║    ╚████╔╝  █████╔╝██╔██╗ ██║
██╔══██╗  ██║     ╚██╔╝   ╚═══██╗██║╚██╗██║
██║  ██║██████╗    ██║   ██████╔╝██║ ╚████║
╚═╝  ╚═╝╚═════╝    ╚═╝   ╚═════╝ ╚═╝  ╚═══╝

```

# Los Santos Online (LSO) Save Extractor & Decryptor

An automated reverse-engineering toolkit to dump, capture, download, and decrypt *Los Santos Online* (LSO) / Grand Theft Auto V PS4 save files directly from PS4 memory and Rockstar cloud servers.

> ⏱️ **Research & Engineering Effort:** This project represents **65+ hours of security research** and **8 hours of active development**, reverse engineering key schedules, cipher structures, and successfully decrypting cloud save files.

---

## 📁 Repository Structure

* **`v1/` (Deprecated / Research Phase):**
  * Contains initial proof-of-concept scripts, raw socket dumps, and experimental tools.
  * **Status:** Deprecated and intentionally kept as a messy historical archive to document how individual conclusions, memory offsets, and decryption routines were discovered.
* **`v2/` (Production Engine):**
  * Contains the clean, fully integrated, multi-threaded master pipeline (`lso_master_pipeline.py`).
  * **Status:** Active, maintained, and recommended for all usage.

---

## ⚡ The `v2/` Engine: `lso_master_pipeline.py`

`v2/lso_master_pipeline.py` automates the entire memory extraction, server interception, cloud download, and local decryption process inside a single script.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        lso_master_pipeline.py                          │
├────────────────────────────────────────────────────────────────────────┤
│ 1. PS4 Connection & Process Lock (eboot.bin PID)                       │
│ 2. Spawns Background Hunters:                                          │
│     ├── RAM Scanner   ➔ <SessionKey>, <RockstarId>, Ticket, Save Magic │
│     └── HTTP Sniffer  ➔ libSceHttp buffer monitor (lossantosonline)   │
│ 3. Memory Event Trigger (Fires when all credentials resolve)           │
│ 4. Auto-Download (XOR User-Agent build, TLS bypass, Master Save pull)  │
│ 5. Auto-Decrypt (RC4 block-cipher ➔ server_decrypted_save.rpf7)        │
│ 6. RAM Dump (Extracts unpacked memory save ➔ ram_decrypted_save.bin)  │
│ 7. Idle Mode (Continuous HTTP traffic logging)                         │
└────────────────────────────────────────────────────────────────────────┘
```

### Detailed Execution Pipeline

1. **Connection & Lock:** Connects to your PS4 over local IP, resolves the `eboot.bin` PID, and locks onto active process memory.
2. **Background Hunters:** Spawns two invisible asynchronous threads:
   * **RAM Scanner:** Continuously sweeps process memory for `<SessionKey>`, `<RockstarId>`, `ros-SessionTicket`, and the `SGTA50000` save header magic.
   * **HTTP Sniffer:** Monitors `libSceHttp` network buffers in real-time, logging any requests targeting `lossantosonline.com`.
3. **The Trigger:** The main process waits passively until the RAM scanner detects all requisite session tokens, waking up the moment credentials resolve.
4. **Auto-Download:** Dynamically constructs the required XOR-obfuscated `User-Agent`, bypasses remote TLS certificate validation, and pulls the master encrypted save from Rockstar cloud servers.
5. **Auto-Decrypt:** Translates and applies the custom RC4 + SHA1 block-cipher logic to write the decrypted archive as `server_decrypted_save.rpf7`.
6. **RAM Dump:** Continues monitoring system memory until the active unpacked save state is located in writable RAM, dumping it directly as `ram_decrypted_save.bin`.
7. **Idle:** Remains operational to log any subsequent background HTTP traffic generated during game execution.

---

## 🛠️ Prerequisites & Quickstart

### Installation

Ensure you have Python 3.8+ and the async `ps4debug` wrapper installed:

```bash
pip install ps4debug
```

### Execution

1. Open `v2/lso_master_pipeline.py` and set your PS4 local IP address:
   ```python
   PS4_IP = "192.168.1.XXX"
   ```
2. Boot your PS4, launch GTA V, and load into Los Santos Online.
3. Run the master engine:
   ```bash
   python3 v2/lso_master_pipeline.py
   ```
4. Sit back and watch the CLI matrix automate the entire pipeline!

---

## ⚠️ Technical Disclaimers

1. **Leftover Credentials Notice:**
   * Certain log files or legacy scripts in `v1/` may contain hardcoded session tickets, keys, or IDs.
   * **All associated account sessions, tokens, and credentials have been completely reset.** These values are non-functional and serve strictly as static schema examples for analysis.
2. **Status of `upload_save.py`:**
   * The legacy script `upload_save.py` is **non-functional** and will consistently fail due to a **CA signature mismatch**.
   * Cloud save uploading/modification is **explicitly out of scope** for this project. This repository focuses solely on security research, memory analysis, save extraction, and offline decryption.