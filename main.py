#!/usr/bin/env python3
import threading
import socket
import logging

from s7comm import handle_s7_request
from db_simulation import PLCDataBlocks
from cpu_logic import start_cpu_cycle
from modbus_server import start_modbus_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def start_s7_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 102))
    s.listen(5)
    logging.info("S7Comm Server listening on TCP/102...")

    while True:
        client_sock, addr = s.accept()
        logging.info(f"[S7] Connection from {addr}")
        threading.Thread(target=handle_s7_request, args=(client_sock, addr), daemon=True).start()


if __name__ == "__main__":
    # Start CPU logic thread
    db = PLCDataBlocks()
    threading.Thread(target=start_cpu_cycle, args=(db,), daemon=True).start()

    # Start S7 server
    threading.Thread(target=start_s7_server, daemon=True).start()

    # Start Modbus server (blocking)
    start_modbus_server()

