#!/bin/bash
# Dung PulseNet backend tren Raspberry Pi
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    pkill -f "uvicorn app.main:app"
    sleep 2
    echo "[OK] Backend da DUNG."
else
    echo "[OK] Backend khong dang chay (khong can lam gi)."
fi
