#!/bin/bash
# Dung gateway BLE PulseNet
if pgrep -f "send_ack.py" > /dev/null; then
    pkill -f "send_ack.py"
    sleep 2
    echo "[OK] Gateway da DUNG."
else
    echo "[OK] Gateway khong dang chay."
fi
