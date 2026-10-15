#!/bin/bash
# Kiem tra trang thai gateway BLE PulseNet
if pgrep -f "send_ack.py" > /dev/null; then
    echo "[CHAY] Process: $(pgrep -f 'send_ack.py' | tr '\n' ' ')"
else
    echo "[DUNG] Gateway chua chay. Khoi dong bang: ./start_gateway.sh"
fi

echo "--- Trang thai gateway theo backend ---"
curl -s -m 3 http://127.0.0.1:8000/api/gateway/status || echo "(backend chua chay)"
echo
