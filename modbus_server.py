import logging
import asyncio
from pymodbus.server import ModbusTcpServer
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from pymodbus.device import ModbusDeviceIdentification

logger = logging.getLogger("MODBUS")


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

    server = ModbusTcpServer(
        context=context,
        identity=identity,
        address=("0.0.0.0", 502),
    )

    logger.info("Starting Modbus Server on TCP/502...")
    await server.serve_forever()


def start_modbus_server():
    """Blocking function to run Modbus server in main thread."""
    asyncio.run(start_modbus_server_async())

                                                           
