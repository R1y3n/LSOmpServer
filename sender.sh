#!/bin/bash
echo "you should have binloader enabled and modify your ps4 local up addr here !!!"
curl -X POST --data-binary @ps4debug.bin http://your_ps4_ip_addr:9090/
