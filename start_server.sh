#!/bin/bash
# Khoi dong PulseNet backend tren Raspberry Pi
cd "$(dirname "$0")/backend" || exit 1

if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "[OK] Backend DANG CHAY roi, khong can khoi dong lai."
    echo "     Web: http://$(hostname -I | awk '{print $1}'):8000/"
    exit 0
fi

nohup .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &
sleep 3

if curl -s http://127.0.0.1:8000/health | grep -q ok; then
    echo "[OK] Backend da KHOI DONG thanh cong."
    echo "     Web: http://$(hostname -I | awk '{print $1}'):8000/"
else
    echo "[LOI] Backend chay khong thanh cong. 20 dong log cuoi:"
    tail -20 uvicorn.log
    exit 1
fi
