import logging
import asyncio
import socket
import threading

from pymodbus.server import ModbusTcpServer
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from pymodbus.device import ModbusDeviceIdentification

logger = logging.getLogger("MODBUS")


# ---------------------------------------------------------
# 1. TCP Wrapper listening on 0.0.0.0:502 (logs attackers)
# ---------------------------------------------------------
def tcp_logger_and_forward():
    source_port = 502
    dest_host = "127.0.0.1"
    dest_port = 1502  # internal pymodbus port

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("0.0.0.0", source_port))
    listener.listen(5)

    logger.info(f"[+] Wrapper listening on 0.0.0.0:{source_port}, forwarding to {dest_host}:{dest_port}")

    while True:
        client_sock, addr = listener.accept()
        logger.info(f"[+] Incoming MODBUS connection from {addr[0]}:{addr[1]}")

        # forward traffic
        threading.Thread(
            target=pipe_sockets,
            args=(client_sock, dest_host, dest_port),
            daemon=True
        ).start()


def pipe_sockets(source_sock, dest_host, dest_port):
    try:
        dest_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dest_sock.connect((dest_host, dest_port))
    except Exception as e:
        logger.error(f"Failed to connect to internal Modbus server: {e}")
        source_sock.close()
        return

    # Relay both directions
    threading.Thread(target=relay, args=(source_sock, dest_sock), daemon=True).start()
    threading.Thread(target=relay, args=(dest_sock, source_sock), daemon=True).start()


def relay(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except:
        pass
    finally:
        src.close()
        dst.close()


# ---------------------------------------------------------
# 2. Real Pymodbus server running internally on port 1502
# ---------------------------------------------------------
async def start_modbus_server_async():
    logger.info("Initializing Modbus datastore...")

    store = ModbusSlaveContext(
        hr=ModbusSequentialDataBlock(0, list(range(0, 200))),
        zero_mode=True,
    )
    context = ModbusServerContext(slaves=store, single=True)

    identity = ModbusDeviceIdentification()
    identity.VendorName = "SIEMENS AG"
    identity.ProductCode = "6ES7"
    identity.ProductName = "SIMATIC PLC"
    identity.ModelName = "S7-1200"
    identity.MajorMinorRevision = "4.2"

    # Real server runs on local port 1502
    server = ModbusTcpServer(
        context=context,
        identity=identity,
        address=("127.0.0.1", 1502),
    )

    logger.info("[+] Starting internal ModbusTcpServer on 127.0.0.1:1502")

    # Start wrapper thread
    threading.Thread(target=tcp_logger_and_forward, daemon=True).start()

    await server.serve_forever()


def start_modbus_server():
    asyncio.run(start_modbus_server_async())
