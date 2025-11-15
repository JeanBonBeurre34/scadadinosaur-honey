import logging
import time

logger = logging.getLogger("PLC_LOGIC")

def start_cpu_cycle(db):
    logger.info("CPU in RUN mode. Starting OB1 scan cycle...")

    while True:
        db.cycle_update()
        logger.info(f"[DB UPDATE] {db.dump()}")
        time.sleep(1.0)

                
