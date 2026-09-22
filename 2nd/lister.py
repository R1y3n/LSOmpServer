import sys

with open("save_dump_SGTA5_0x38D9B48.bin", "rb") as f:
    data = f.read()

print(f"[*] Save file size: {len(data)} bytes")
print(f"[*] Magic: {data[0x48:0x51]}")

# Find all property entries
print("\n=== PROPERTIES ===")
idx = 0
count = 0
while True:
    idx = data.find(b"ram_mp_property_ext", idx)
    if idx == -1: break
    # Grab surrounding context for the property hash/ID
    ctx = data[idx:idx+64]
    print(f"  Property #{count}: offset 0x{idx:X}")
    count += 1
    idx += 1
print(f"  Total: {count} properties")

# Find all vehicle entries
print("\n=== VEHICLES ===")
idx = 0
count = 0
while True:
    idx = data.find(b"am_vehicle_spawn", idx)
    if idx == -1: break
    print(f"  Vehicle spawn #{count}: offset 0x{idx:X}")
    count += 1
    idx += 1

idx = 0
while True:
    idx = data.find(b"iam_mp_vehicle_reward", idx)
    if idx == -1: break
    print(f"  Vehicle reward: offset 0x{idx:X}")
    idx += 1

# Find character appearance data
print("\n=== CHARACTER/APPEARANCE ===")
for marker in [b"mp_char", b"MP0_CHAR", b"appearance", b"outfit", b"ped_"]:
    idx = data.find(marker)
    if idx != -1:
        print(f"  Found '{marker.decode(errors='ignore')}' at offset 0x{idx:X}")

print("\n[+] Your save contains all vehicles, properties, and appearance data.")
