#!/bin/bash
# Khoi dong gateway BLE PulseNet (headless: tu dong day cau hoi xuong thiet bi)
# Tu THU LAI toi 3 lan neu gateway chet ngay sau khi khoi dong
# (vi du: bluetooth chua san sang ngay sau khi Pi boot).
cd "$(dirname "$0")/gateway" || exit 1

if pgrep -f "send_ack.py" > /dev/null; then
    echo "[OK] Gateway DANG CHAY roi."
    echo "     Trang thai: ./status_gateway.sh"
    exit 0
fi

for attempt in 1 2 3; do
    nohup .venv/bin/python -u send_ack.py > gateway.log 2>&1 < /dev/null &
    sleep 4

    if pgrep -f "send_ack.py" > /dev/null; then
        echo "[OK] Gateway da KHOI DONG (headless, tu dong day cau hoi)."
        echo "     Xem log: tail -f ~/pulsenet/gateway/gateway.log"
        exit 0
    fi

    echo "[CANH BAO] Lan thu $attempt that bai, thu lai sau 3 giay..."
    sleep 3
done

echo "[LOI] Gateway khong chay duoc sau 3 lan thu. 20 dong log cuoi:"
tail -20 gateway.log
exit 1
