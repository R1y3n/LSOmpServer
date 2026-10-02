#!/bin/bash
echo "you should have binloader enabled and modify your ps4 local up addr here !!!"
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
curl --fail --show-error -X POST \
  --data-binary "@${SCRIPT_DIR}/ps4debug.bin" \
  http://your_ps4_ip_addr:9090/
