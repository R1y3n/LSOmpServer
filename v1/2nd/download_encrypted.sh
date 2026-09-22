wget --no-check-certificate \
  --header="User-Agent: ros YOUR_CUSTOM_USER_AGENT_HERE" \
  --header="ros-SessionTicket: YOUR_SESSION_TICKET_HERE" \
  --header="Scs-Ticket: YOUR_SCS_TICKET_HERE" \
  --header="Host: prod.ps4.lossantosonline.com" \
  -O server_encrypted_save_wget.bin \
  "https://prod.ps4.lossantosonline.com/cloud/11/cloudservices/members/np/YOUR_USER_ID_HERE/GTA5/saves/mpstats/save_char0001_ps4.save"
