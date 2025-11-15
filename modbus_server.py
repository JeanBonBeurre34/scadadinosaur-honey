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

    # thread: inbound traffic → internal server
    threading.Thread(
        target=relay_with_unit_filter,
        args=(source_sock, dst),
        daemon=True
    ).start()

    # thread: responses from internal server → attacker
    threading.Thread(
        target=relay_raw,
        args=(dst, source_sock),
        daemon=True
    ).start()


def relay_raw(src, dst):
    """Raw relay for outbound (server → attacker)."""
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


# ======================================================================
# FULL PACKET LOGGER + SIEMENS UNITID FILTERING
# ======================================================================
def relay_with_unit_filter(src, dst):
    """Logs every inbound Modbus ADU and enforces Siemens UnitID rules."""
    try:
        while True:
            adu = src.recv(4096)
            if not adu:
                break

            if len(adu) < 8:
                logger.warning(f"[BAD] Short ADU ({len(adu)} bytes)")
                continue

            # Parse ADU header
            transaction_id = int.from_bytes(adu[0:2], "big")
            protocol_id = int.from_bytes(adu[2:4], "big")
            length = int.from_bytes(adu[4:6], "big")
            unit_id = adu[6]
            function_code = adu[7]

            # Log the raw packet
            logger.info(
                f"[MODBUS RAW] TX={transaction_id} "
                f"PID={protocol_id} LEN={length} "
                f"UnitID={unit_id} FC=0x{function_code:02x} "
                f"RAW={adu.hex()}"
            )

            # ---------------------------------------------------------
            # 1. Siemens behavior: allow UnitID=255 only for MEI (0x2B)
            # ---------------------------------------------------------
            if unit_id == 255:
                if function_code == 0x2B:
                    logger.info("[ALLOW] UnitID=255 MEI device identification request")
                    dst.sendall(adu)
                else:
                    logger.warning(f"[DROP] UnitID 255 illegal FC=0x{function_code:02x}")
                continue

            # ---------------------------------------------------------
            # 2. Siemens PLCs normally respond ONLY to UnitID=1
            # ---------------------------------------------------------
            if unit_id != 1:
                logger.warning(f"[DROP] UnitID {unit_id} ignored (Siemens behavior)")
                continue

            # Valid → forward to internal Modbus server
            dst.sendall(adu)

    except Exception as e:
        logger.error(f"[relay_with_unit_filter] {e}")

    finally:
        src.close()
        dst.close()


# ======================================================================
# 2. INTERNAL PYMODBUS SERVER (PORT 1502)
# ======================================================================
async def start_modbus_server_async():
    logger.info("Initializing Modbus datastore...")

    store = ModbusSlaveContext(
        hr=ModbusSequentialDataBlock(0, [0] * 200),
        zero_mode=True,
    )

    context = ModbusServerContext(slaves=store, single=True)

    identity = ModbusDeviceIdentification()
    identity.VendorName = "SIEMENS AG"
    identity.ProductCode = "6ES7"
    identity.ProductName = "SIMATIC PLC"
    identity.ModelName = "S7-1200"
    identity.MajorMinorRevision = "4.2"

    # DB simulation → modbus registers
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

    server = ModbusTcpServer(
        context=context,
        identity=identity,
        address=("127.0.0.1", 1502),
    )

    logger.info("[+] Internal Pymodbus running on 1502")

    threading.Thread(target=tcp_logger_and_forward, daemon=True).start()

    await server.serve_forever()


def start_modbus_server():
    asyncio.run(start_modbus_server_async())

