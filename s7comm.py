import socket
import logging
from binascii import hexlify

logger = logging.getLogger("S7COMM")

TPKT_VERSION = 0x03
COTP_CR = 0xE0
COTP_CC = 0xD0
S7_ROSCTR_JOB = 0x01
S7_ROSCTR_ACK = 0x03

def recv_all(sock, size):
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def build_s7_header(payload):
    length = 4 + len(payload)
    return bytes([
        TPKT_VERSION,
        0x00,
        (length >> 8) & 0xFF,
        length & 0xFF
    ]) + b"\x02\xF0\x80" + payload


def szl_system_id():
    """
    Fake SZL: Return plausible Siemens S7-1200 system information.
    These values are intentionally realistic but non-proprietary.
    """
    return build_s7_header(
        b"\x32\x03\x00\x02\x00\x00\x00\x01\x00\x0C" +
        b"\x00\xB4" +                 # SZL ID (system info)
        b"\x00\x01" +                 # Index
        b"\x00\x0A" +                 # Length
        b"\x11\x22\x33\x44" +         # Module Serial
        b"\x12\x34\x12\x34"           # Firmware ID
    )


def handle_s7_request(sock, client):
    try:
        header = recv_all(sock, 4)
        if not header:
            return

        if header[0] != TPKT_VERSION:
            logger.warning(f"Non-TPKT traffic from {client}")
            return

        size = (header[2] << 8) | header[3]
        remaining = recv_all(sock, size - 4)
        if not remaining:
            return

        logger.info(f"[RAW] {client} → {hexlify(header + remaining).decode()}")

        # COTP
        if remaining[0] == COTP_CR:
            logger.info(f"[COTP] Connection Request from {client}")
            resp = build_s7_header(b"\xD0\x00")
            sock.send(resp)
            return

        # S7 JOB
        if remaining[3] == S7_ROSCTR_JOB:
            logger.info(f"[S7] JOB from {client}")

            # SZL request
            if remaining[10:12] == b"\x00\x01":
                sock.send(szl_system_id())
                return

            # Read Var request (fake OK response)
            if remaining[11] == 0x04:
                sock.send(build_s7_header(
                    b"\x32\x03\x00\x00\x00\x01\x00"
                    b"\xFF\x04\x01\x00\x02\x00\x00"
                ))
                return

            # Write Var request (log the write)
            if remaining[11] == 0x05:
                logger.info(f"[WRITE] S7 Write detected from {client}")
                sock.send(build_s7_header(
                    b"\x32\x03\x00\x00\x00\x01\x00\xFF"
                ))
                return

        logger.info(f"[S7] Unknown S7Comm payload received")

    except Exception as e:
        logger.error(f"S7 handler error: {e}")

