#!/bin/bash
# Kiem tra trang thai PulseNet backend tren Raspberry Pi
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    ANSWER=$(curl -s -m 3 http://127.0.0.1:8000/health)
    echo "[CHAY] Process: $(pgrep -f 'uvicorn app.main:app' | tr '\n' ' ')"
    echo "[CHAY] /health: $ANSWER"
    echo "[CHAY] Web:     http://$(hostname -I | awk '{print $1}'):8000/"
else
    echo "[DUNG] Backend chua chay. Khoi dong bang: ./start_server.sh"
fi
