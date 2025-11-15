#!/bin/bash

set -e

IMAGE_NAME="scada-s7-honeypot"
CONTAINER_NAME="scada-s7-honeypot"

echo ""
echo "=============================="
echo "  Siemens S7 Honeypot Deploy"
echo "=============================="
echo ""

# ------------------------------------------
# STOP & REMOVE EXISTING CONTAINER
# ------------------------------------------
if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}\$"; then
    echo "[+] Stopping existing container..."
    docker stop $CONTAINER_NAME >/dev/null 2>&1 || true

    echo "[+] Removing existing container..."
    docker rm $CONTAINER_NAME >/dev/null 2>&1 || true
fi

# ------------------------------------------
# BUILD NEW IMAGE
# ------------------------------------------
echo "[+] Building new Docker image: $IMAGE_NAME"
docker build -t $IMAGE_NAME .

echo ""
echo "[+] Image build completed."
echo ""

# ------------------------------------------
# START CONTAINER WITH CAPABILITY TO BIND TO LOW PORTS
# ------------------------------------------
echo "[+] Starting honeypot container on ports 102 and 502..."

docker run -d \
    --name $CONTAINER_NAME \
    --cap-add=NET_BIND_SERVICE \
    -p 102:102 \
    -p 502:502 \
    --restart unless-stopped \
    $IMAGE_NAME

echo ""
echo "=============================="
echo " Honeypot successfully deployed!"
echo "=============================="
echo "[*] S7Comm server     → port 102"
echo "[*] Modbus server     → port 502"
echo "[*] Container name    → $CONTAINER_NAME"

# ------------------------------------------
# OPTIONAL LOG TAILING
# ------------------------------------------
if [[ "$1" == "--logs" ]]; then
    echo ""
    echo "[+] Tailing logs (Ctrl+C to exit)..."
    docker logs -f $CONTAINER_NAME
fi

echo ""
echo "[+] Done."

     
