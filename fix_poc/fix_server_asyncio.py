import argparse
import asyncio
import logging
import time
import uuid
from typing import Dict, Optional, Tuple, List

import sys
from pathlib import Path

# Ensure repository root is on sys.path when running this file directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SOH = "\x01"
SOH_b = b"\x01"


class FixSession:
    def __init__(self, server_comp_id: str) -> None:
        self.server_comp_id = server_comp_id
        self.client_sender: Optional[str] = None  # 49 from client
        self.client_target: Optional[str] = None  # 56 from client
        self.out_seq: int = 1

    def assign_from_incoming(self, msg: Dict[str, str]):
        # Capture peer IDs from the first message
        self.client_sender = msg.get("49", self.client_sender)
        self.client_target = msg.get("56", self.client_target)

    def server_sender(self) -> str:
        # Server's 49
        return self.client_target or self.server_comp_id or "SERVER"

    def server_target(self) -> str:
        # Server's 56 (should be client's 49)
        return self.client_sender or "CLIENT"


class FixCodec:
    @staticmethod
    def dict_to_fix(message: Dict[str, str]) -> str:
        # Remove BodyLength and CheckSum if present
        message.pop("9", None)
        message.pop("10", None)
        # Sort tags except 8/9/10 special handling
        pairs = [(int(k), v) for k, v in message.items() if k not in {"8", "9", "10"}]
        pairs.sort(key=lambda x: x[0])
        parts = [f"8={message['8']}"] + [f"{k}={v}" for k, v in pairs]
        body = SOH.join(parts) + SOH
        body_length = len(body)
        fix_msg = (
            f"8={message['8']}"
            + SOH
            + f"9={body_length}"
            + SOH
            + SOH.join(parts[1:])
            + SOH
        )
        checksum = sum(fix_msg.encode("ascii")) % 256
        fix_msg += f"10={checksum:03d}" + SOH
        return fix_msg

    @staticmethod
    def fix_to_dict(fix_str: str) -> Dict[str, str]:
        if fix_str.endswith(SOH):
            fix_str = fix_str[:-1]
        d: Dict[str, str] = {}
        for kv in fix_str.split(SOH):
            if "=" in kv:
                k, v = kv.split("=", 1)
                d[k] = v
        return d

    @staticmethod
    def extract_messages(buffer: bytes) -> Tuple[List[str], bytes]:
        messages: List[str] = []
        start = 0
        while True:
            idx = buffer.find(b"10=", start)
            if idx == -1:
                break
            end = buffer.find(SOH_b, idx)
            if end == -1:
                break
            msg_bytes = buffer[: end + 1]
            if not msg_bytes.startswith(b"8="):
                buffer = buffer[end + 1 :]
                start = 0
                continue
            messages.append(msg_bytes.decode("ascii", errors="ignore"))
            buffer = buffer[end + 1 :]
            start = 0
        return messages, buffer


class FixServer:
    def __init__(
        self,
        host: str,
        port: int,
        server_comp_id: str,
        begin_string: str = "FIX.4.4",
        auto_fill: bool = False,
        log_level: str = "INFO",
    ) -> None:
        self.host = host
        self.port = port
        self.server_comp_id = server_comp_id
        self.begin_string = begin_string
        self.auto_fill = auto_fill
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        )
        self.logger = logging.getLogger("fix-server")

    async def start(self) -> None:
        server = await asyncio.start_server(self._handle_client, self.host, self.port)
        addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
        self.logger.info("listening on %s", addrs)
        async with server:
            await server.serve_forever()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        self.logger.info("connection from %s", peer)
        session = FixSession(server_comp_id=self.server_comp_id)
        buffer = b""
        try:
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                buffer += chunk
                msgs, buffer = FixCodec.extract_messages(buffer)
                for raw in msgs:
                    msg = FixCodec.fix_to_dict(raw)
                    session.assign_from_incoming(msg)
                    await self._handle_message(session, msg, writer)
        except Exception as e:
            self.logger.exception("client error: %s", e)
        finally:
            with contextlib.suppress(Exception):
                writer.close()
                await writer.wait_closed()
            self.logger.info("connection closed: %s", peer)

    async def _handle_message(
        self, session: FixSession, msg: Dict[str, str], writer: asyncio.StreamWriter
    ) -> None:
        mtype = msg.get("35")
        if mtype == "A":
            # Logon: reply Logon
            reply = {
                "8": self.begin_string,
                "35": "A",
                "49": session.server_sender(),
                "56": session.server_target(),
                "34": str(session.out_seq),
                "52": time.strftime("%Y%m%d-%H:%M:%S", time.gmtime()),
                "98": "0",
                "108": msg.get("108", "30"),
            }
            session.out_seq += 1
            await self._send(writer, reply)
            self.logger.info("logon ack sent to %s", session.server_target())
        elif mtype == "0":
            # Heartbeat: optionally ignore or echo
            self.logger.debug("heartbeat received")
        elif mtype == "1":
            # TestRequest: reply Heartbeat with same 112
            reply = {
                "8": self.begin_string,
                "35": "0",
                "49": session.server_sender(),
                "56": session.server_target(),
                "34": str(session.out_seq),
                "52": time.strftime("%Y%m%d-%H:%M:%S", time.gmtime()),
                "112": msg.get("112", "TEST"),
            }
            session.out_seq += 1
            await self._send(writer, reply)
            self.logger.info("heartbeat in response to test request")
        elif mtype == "D":
            # NewOrderSingle: reply ExecutionReport NEW (and possibly FILL)
            clid = msg.get("11", f"CL{uuid.uuid4().hex[:8]}")
            symbol = msg.get("55", "SYM")
            side = msg.get("54", "1")
            qty = msg.get("38", "0")
            price = msg.get("44")

            order_id = f"ORD{uuid.uuid4().hex[:8]}"
            exec_id = f"EX{uuid.uuid4().hex[:8]}"

            er_new = {
                "8": self.begin_string,
                "35": "8",
                "49": session.server_sender(),
                "56": session.server_target(),
                "34": str(session.out_seq),
                "52": time.strftime("%Y%m%d-%H:%M:%S", time.gmtime()),
                "150": "0",  # ExecType=NEW
                "39": "0",  # OrdStatus=NEW
                "11": clid,
                "37": order_id,
                "17": exec_id,
                "55": symbol,
                "54": side,
                "38": qty,
                "151": qty,  # LeavesQty
                "14": "0",  # CumQty
                "6": "0",  # AvgPx
            }
            if price is not None:
                er_new["44"] = price

            session.out_seq += 1
            await self._send(writer, er_new)
            self.logger.info("sent ER NEW for clOrdID=%s", clid)

            if self.auto_fill:
                # Immediately send a FILL
                exec_id2 = f"EX{uuid.uuid4().hex[:8]}"
                er_fill = {
                    "8": self.begin_string,
                    "35": "8",
                    "49": session.server_sender(),
                    "56": session.server_target(),
                    "34": str(session.out_seq),
                    "52": time.strftime("%Y%m%d-%H:%M:%S", time.gmtime()),
                    "150": "2",  # ExecType=FILL
                    "39": "2",  # OrdStatus=FILLED
                    "11": clid,
                    "37": order_id,
                    "17": exec_id2,
                    "55": symbol,
                    "54": side,
                    "38": qty,
                    "32": qty,  # LastQty
                    "151": "0",  # LeavesQty
                    "14": qty,  # CumQty
                    "6": price or "0",
                }
                if price is not None:
                    er_fill["31"] = price  # LastPx
                session.out_seq += 1
                await self._send(writer, er_fill)
                self.logger.info("sent ER FILL for clOrdID=%s", clid)
        else:
            self.logger.debug("message type %s ignored", mtype)

    async def _send(self, writer: asyncio.StreamWriter, msg: Dict[str, str]) -> None:
        fix_str = FixCodec.dict_to_fix(msg)
        writer.write(fix_str.encode("ascii"))
        await writer.drain()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simple asyncio FIX 4.4 server for testing clients",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default="127.0.0.1", help="Listen host")
    parser.add_argument("--port", type=int, default=9876, help="Listen port")
    parser.add_argument("--comp-id", default="SERVER", help="Server SenderCompID (49)")
    parser.add_argument(
        "--auto-fill",
        action="store_true",
        help="Immediately send a FILLED ER after NEW",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    args = parser.parse_args()

    server = FixServer(
        host=args.host,
        port=args.port,
        server_comp_id=args.comp_id,
        auto_fill=args.auto_fill,
        log_level=args.log_level,
    )

    asyncio.run(server.start())


if __name__ == "__main__":
    import contextlib

    main()
