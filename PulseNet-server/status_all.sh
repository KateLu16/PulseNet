#!/bin/bash
# Kiem tra trang thai backend + gateway
cd "$(dirname "$0")" || exit 1

echo "=== Backend ==="
./status_server.sh

echo ""
echo "=== Gateway ==="
./status_gateway.sh
