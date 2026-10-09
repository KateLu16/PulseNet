#!/bin/bash
# Dung DONG THOI backend + gateway BLE tren Pi
cd "$(dirname "$0")" || exit 1

./stop_gateway.sh
./stop_server.sh

echo "[OK] Da dung toan bo PulseNet."
