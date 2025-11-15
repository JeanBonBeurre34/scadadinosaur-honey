import logging
import asyncio
import socket
import threading
import time

from pymodbus.server import ModbusTcpServer
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from pymodbus.device import ModbusDeviceIdentification

logger = logging.getLogger("MODBUS")


# ======================================================================
# 1. TCP WRAPPER (PORT 502 → INTERNAL 1502) WITH FULL PACKET LOGGING
# ======================================================================
def tcp_logger_and_forward():
    source_port = 502
    dest_host = "127.0.0.1"
    dest_port = 1502

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("0.0.0.0", source_port))
    listener.listen(5)

    logger.info(f"[+] Wrapper listening on port {source_port}")

    while True:
        client_sock, addr = listener.accept()
        logger.info(f"[+] Incoming MODBUS from {addr[0]}:{addr[1]}")
        threading.Thread(
            target=pipe_sockets,
            args=(client_sock, dest_host, dest_port),
            daemon=True
        ).start()


def pipe_sockets(source_sock, dest_host, dest_port):
    try:
        dst = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dst.connect((dest_host, dest_port))
    except Exception as e:
        logger.error(f"[!] Cannot connect to internal Modbus: {e}")
        source_sock.close()
        return

    # inbound → server (log + filter)
    threading.Thread(
        target=relay_with_unit_filter,
        args=(source_sock, dst),
        daemon=True
    ).start()

    # outbound → attacker (log responses)
    threading.Thread(
        target=relay_raw,
        args=(dst, source_sock),
        daemon=True
    ).start()


# ======================================================================
# REQUEST LOGGING + UNIT FILTER (attacker → server)
# ======================================================================
def relay_with_unit_filter(src, dst):
    """Relay inbound requests, apply Siemens UnitID rules, and log raw packets."""
    try:
        while True:
            adu = src.recv(4096)
            if not adu:
                break

            # Minimal Modbus TCP ADU = 8 bytes
            if len(adu) < 8:
                logger.info(f"[MODBUS RAW] SHORT RAW={adu.hex()}")
                continue

            txid = int.from_bytes(adu[0:2], "big")
            pid = int.from_bytes(adu[2:4], "big")
            length = int.from_bytes(adu[4:6], "big")
            unit = adu[6]
            fc = adu[7]

            logger.info(
                f"[MODBUS RAW] TX={txid} PID={pid} LEN={length} "
                f"UnitID={unit} FC=0x{fc:02x} RAW={adu.hex()}"
            )

            # Siemens rules:
            # Allow MEI14 ID query (UnitID 255, FC 0x2B)
            if unit == 255 and fc == 0x2B:
                dst.sendall(adu)
                continue

            # All other traffic allowed ONLY on UnitID=1
            if unit != 1:
                logger.warning(f"[DROP] UnitID {unit} ignored (Siemens behavior)")
                continue

            dst.sendall(adu)

    except Exception as e:
        logger.error(f"[relay_with_unit_filter] {e}")

    finally:
        src.close()
        dst.close()


# ======================================================================
# RESPONSE LOGGING (server → attacker)
# ======================================================================
def relay_raw(src, dst):
    """
    Raw relay for outbound (server → attacker).
    Logs the response paired with the request above.
    """
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break

            if len(data) >= 8:
                txid = int.from_bytes(data[0:2], "big")
                pid = int.from_bytes(data[2:4], "big")
                length = int.from_bytes(data[4:6], "big")
                unit = data[6]
                fc = data[7]

                logger.info(
                    f"[MODBUS RESP] TX={txid} PID={pid} LEN={length} "
                    f"UnitID={unit} FC=0x{fc:02x} RAW={data.hex()}"
                )
            else:
                logger.info(f"[MODBUS RESP] SHORT RAW={data.hex()}")

            dst.sendall(data)

    except Exception as e:
        logger.error(f"[relay_raw] {e}")

    finally:
        src.close()
        dst.close()


# ======================================================================
# 2. INTERNAL PYMODBUS SERVER (PORT 1502)
# ======================================================================
async def start_modbus_server_async():
    logger.info("Initializing Modbus datastore...")

    # 200 registers
    store = ModbusSlaveContext(
        hr=ModbusSequentialDataBlock(0, [0] * 200),
        zero_mode=True,
    )

    # Wrapper enforces single UnitID → so use single=True
    context = ModbusServerContext(slaves=store, single=True)

    # Device ID data
    identity = ModbusDeviceIdentification()
    identity.VendorName = "SIEMENS AG"
    identity.ProductCode = "6ES7"
    identity.ProductName = "SIMATIC PLC"
    identity.ModelName = "S7-1200"
    identity.MajorMinorRevision = "4.2"

    # DB simulation to holding registers
    from db_simulation import PLCDataBlocks
    db = PLCDataBlocks()

    def sync_db_to_modbus():
        while True:
            store.setValues(3, 0,  [int(db.DB1["Temperature"] * 10)])
            store.setValues(3, 1,  [int(db.DB1["Pressure"] * 1000)])
            store.setValues(3, 2,  [int(db.DB10["Level"])])
            store.setValues(3, 3,  [1 if db.DB10["Valve_Open"] else 0])
            store.setValues(3, 4,  [1 if db.DB1["Motor1_Running"] else 0])
            store.setValues(3, 5,  [1 if db.DB1["Motor2_Running"] else 0])
            store.setValues(3, 100, [int(db.DB100["CPU_Load"])])
            store.setValues(3, 101, [int(db.DB100["Scan_Time"] * 10)])
            time.sleep(1)

    threading.Thread(target=sync_db_to_modbus, daemon=True).start()

    # Internal server on localhost:1502
    server = ModbusTcpServer(
        context=context,
        identity=identity,
        address=("127.0.0.1", 1502),
    )

    logger.info("[+] Internal Pymodbus running on 1502")

    # Start wrapper before server loop
    threading.Thread(target=tcp_logger_and_forward, daemon=True).start()

    await server.serve_forever()


def start_modbus_server():
    asyncio.run(start_modbus_server_async())

                                     
