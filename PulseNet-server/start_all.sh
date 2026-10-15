#!/bin/bash
# Khoi dong DONG THOI backend + gateway BLE tren Pi
cd "$(dirname "$0")" || exit 1

echo "=== PulseNet: khoi dong toan bo ==="

./start_server.sh || exit 1
./start_gateway.sh || exit 1

echo ""
echo "Web: http://$(hostname -I | awk '{print $1}'):8000/"
echo "=== Done ==="
