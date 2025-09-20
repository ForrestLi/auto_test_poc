import socket
import select
import threading
import time
import datetime
import logging
from queue import Queue, Empty
from typing import Optional, Dict, Callable, List, Any
from enum import Enum
from fix_msg import MsgType as FixMessageType

logger = logging.getLogger(__name__)


class FixClient:
    def __init__(
        self,
        host: str,
        port: int,
        sender_comp_id: str,
        target_comp_id: str,
        heartbeat_interval: int = 30,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.heartbeat_interval = heartbeat_interval
        self.username = username
        self.password = password

        self.socket: Optional[socket.socket] = None
        self.send_queue: Queue = Queue()
        self.receive_queue: Queue = Queue()
        self._stop_event = threading.Event()

        # Sequence numbers
        self.out_seq_num = 1
        self.in_seq_num = 1

        # Message handlers
        self.handlers: Dict[str, List[Callable]] = {
            msg_type.value: [] for msg_type in FixMessageType
        }

        # Register default handlers
        self.register_handler(FixMessageType.HEARTBEAT.value, self._handle_heartbeat)
        self.register_handler(FixMessageType.LOGON.value, self._handle_logon)
        self.register_handler(FixMessageType.LOGOUT.value, self._handle_logout)
        self.register_handler(
            FixMessageType.TEST_REQUEST.value, self._handle_test_request
        )

    def register_handler(self, msg_type: str, handler: Callable) -> None:
        """Register a handler for a specific message type"""
        if msg_type in self.handlers:
            self.handlers[msg_type].append(handler)
        else:
            self.handlers[msg_type] = [handler]

    def connect(self) -> None:
        """Establish connection to FIX server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to FIX server {self.host}:{self.port}")

            # Start send and receive threads
            self._stop_event.clear()
            self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
            self.receive_thread = threading.Thread(
                target=self._receive_loop, daemon=True
            )

            self.send_thread.start()
            self.receive_thread.start()

            # Send logon message
            self.logon()

        except Exception as e:
            logger.error(f"Failed to connect to FIX server: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from FIX server"""
        logger.info("Disconnecting from FIX server")
        self._stop_event.set()

        # Send logout message if connected
        if self.socket:
            try:
                self.logout()
            except Exception:
                pass

        # Close socket
        if self.socket:
            self.socket.close()
            self.socket = None

        # Clear queues
        while not self.send_queue.empty():
            try:
                self.send_queue.get_nowait()
            except Empty:
                break

        while not self.receive_queue.empty():
            try:
                self.receive_queue.get_nowait()
            except Empty:
                break

    def logon(self) -> None:
        """Send logon message to FIX server"""
        logon_msg = self._create_message(FixMessageType.LOGON.value)

        # Add logon-specific fields
        logon_msg["98"] = "0"  # EncryptMethod (0 = None)
        logon_msg["108"] = str(self.heartbeat_interval)  # HeartBtInt

        # Add username and password if provided
        if self.username:
            logon_msg["553"] = self.username
        if self.password:
            logon_msg["554"] = self.password

        self.send_message(logon_msg)

    def logout(self) -> None:
        """Send logout message to FIX server"""
        logout_msg = self._create_message(FixMessageType.LOGOUT.value)
        self.send_message(logout_msg)

    def send_heartbeat(self) -> None:
        """Send heartbeat message"""
        heartbeat_msg = self._create_message(FixMessageType.HEARTBEAT.value)
        self.send_message(heartbeat_msg)

    def send_test_request(self, test_req_id: str) -> None:
        """Send test request message"""
        test_request_msg = self._create_message(FixMessageType.TEST_REQUEST.value)
        test_request_msg["112"] = test_req_id  # TestReqID
        self.send_message(test_request_msg)

    def send_message(self, message: Dict[str, str]) -> None:
        """Queue a message for sending"""
        # Add standard header fields if not present
        if "8" not in message:
            message["8"] = "FIX.4.4"  # BeginString
        if "49" not in message:
            message["49"] = self.sender_comp_id  # SenderCompID
        if "56" not in message:
            message["56"] = self.target_comp_id  # TargetCompID
        if "34" not in message:
            message["34"] = str(self.out_seq_num)  # MsgSeqNum
            self.out_seq_num += 1
        if "52" not in message:
            message["52"] = datetime.datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")[
                :-3
            ]  # SendingTime

        # Calculate and add checksum
        fix_str = self._dict_to_fix(message)
        checksum = self._calculate_checksum(fix_str)
        message["10"] = checksum

        # Convert to FIX format and queue for sending
        fix_message = self._dict_to_fix(message)
        self.send_queue.put(fix_message)

    def receive_message(
        self, timeout: Optional[float] = None
    ) -> Optional[Dict[str, str]]:
        """Get a received message from the queue"""
        try:
            fix_str = self.receive_queue.get(timeout=timeout)
            return self._fix_to_dict(fix_str)
        except Empty:
            return None

    def _send_loop(self) -> None:
        """Main sending loop running in separate thread"""
        last_heartbeat = time.monotonic()

        while not self._stop_event.is_set() and self.socket:
            try:
                # Check if it's time to send a heartbeat
                if time.monotonic() - last_heartbeat > self.heartbeat_interval:
                    self.send_heartbeat()
                    last_heartbeat = time.monotonic()

                # Get message from queue with timeout
                try:
                    message = self.send_queue.get(timeout=1)
                except Empty:
                    continue

                # Send the message
                if self.socket:
                    self.socket.sendall(message.encode())
                    logger.debug(f"Sent: {message.replace(chr(1), '|')}")

            except Exception as e:
                logger.error(f"Error in send loop: {e}")
                break

    def _receive_loop(self) -> None:
        """Main receiving loop running in separate thread"""
        buffer = ""

        while not self._stop_event.is_set() and self.socket:
            try:
                # Receive data from socket
                data = self.socket.recv(4096)
                if not data:
                    logger.warning("Connection closed by server")
                    break

                # Add to buffer
                buffer += data.decode()

                # Process complete messages from buffer
                while chr(1) in buffer:
                    # Extract the first complete message
                    message, _, buffer = buffer.partition(chr(1))
                    message += chr(1)  # Add the delimiter back

                    # Parse and handle the message
                    try:
                        msg_dict = self._fix_to_dict(message)
                        self._handle_message(msg_dict)

                        # Add to receive queue
                        self.receive_queue.put(message)

                    except Exception as e:
                        logger.error(f"Error processing message: {e}")

            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                break

    def _handle_message(self, message: Dict[str, str]) -> None:
        """Handle an incoming message"""
        # Update incoming sequence number
        if "34" in message:
            self.in_seq_num = int(message["34"]) + 1

        # Call registered handlers for this message type
        msg_type = message.get("35", "")
        if msg_type in self.handlers:
            for handler in self.handlers[msg_type]:
                try:
                    handler(message)
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")

    def _handle_heartbeat(self, message: Dict[str, str]) -> None:
        """Handle heartbeat message"""
        logger.debug("Received heartbeat")

    def _handle_logon(self, message: Dict[str, str]) -> None:
        """Handle logon response"""
        logger.info("Logon successful")

    def _handle_logout(self, message: Dict[str, str]) -> None:
        """Handle logout message"""
        logger.info("Received logout request")
        self.disconnect()

    def _handle_test_request(self, message: Dict[str, str]) -> None:
        """Handle test request by responding with a heartbeat"""
        test_req_id = message.get("112")
        if test_req_id:
            heartbeat = self._create_message(FixMessageType.HEARTBEAT.value)
            heartbeat["112"] = test_req_id  # Echo the TestReqID
            self.send_message(heartbeat)

    def _create_message(self, msg_type: str) -> Dict[str, str]:
        """Create a base FIX message with standard headers"""
        return {
            "8": "FIX.4.4",  # BeginString
            "35": msg_type,  # MsgType
            "49": self.sender_comp_id,  # SenderCompID
            "56": self.target_comp_id,  # TargetCompID
            "34": str(self.out_seq_num),  # MsgSeqNum
            "52": datetime.datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")[
                :-3
            ],  # SendingTime
        }

    def _dict_to_fix(self, message: Dict[str, str]) -> str:
        """Convert a dictionary to a FIX string"""
        # Sort by tag number (except BeginString, BodyLength, and CheckSum which have special positions)
        tags = sorted(
            (int(k), v) for k, v in message.items() if k not in ["8", "9", "10"]
        )

        # Build the message parts
        parts = [f"8={message['8']}"] if "8" in message else []

        # Add the other tags
        parts.extend([f"{k}={v}" for k, v in tags])

        # Calculate body length (number of characters between BodyLength and CheckSum)
        body = chr(1).join(parts)
        body_length = len(body)

        # Insert BodyLength after BeginString
        fix_str = f"8={message['8']}{chr(1)}9={body_length}{chr(1)}{body}{chr(1)}"

        # Calculate and add checksum
        checksum = self._calculate_checksum(fix_str)
        fix_str += f"10={checksum}{chr(1)}"

        return fix_str

    def _fix_to_dict(self, fix_str: str) -> Dict[str, str]:
        """Convert a FIX string to a dictionary"""
        # Remove the SOH delimiter at the end if present
        if fix_str.endswith(chr(1)):
            fix_str = fix_str[:-1]

        # Split into key-value pairs
        pairs = fix_str.split(chr(1))
        result = {}

        for pair in pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
                result[key] = value

        return result

    def _calculate_checksum(self, fix_str: str) -> str:
        """Calculate the FIX checksum for a message"""
        # Calculate sum of all bytes modulo 256
        total = sum(ord(c) for c in fix_str) % 256
        # Format as 3-digit number with leading zeros
        return f"{total:03d}"

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Example usage
if __name__ == "__main__":
    import socket
    import fix
    import logging
    import sys
    import contextlib
    from typing import Optional, Dict, Set
    from collections import OrderedDict
    from fix.util import ch_delim, iter_rawmsg

    # Colorama can be kept but we'll use it more appropriately
    import colorama

    colorama.init()

    class UnexpectedMessageException(Exception):
        def __init__(self, message: str = "", *, offending_msg):
            detail = f"(unexpected message: {offending_msg})"
            super().__init__(f"{message} {detail}" if message else detail)
            self.offending_msg = offending_msg

    class NoMessageResponseException(Exception):
        def __init__(self, message: str = ""):
            detail = "(no message received)"
            super().__init__(f"{message} {detail}" if message else detail)

    class FixClient:
        def __init__(
            self,
            config=None,
            *,
            conn_name="default",
            timeout=5,
            auto=True,
            verbose=1,
            log_level=logging.INFO,
            filter_tags: Optional[Set[int]] = None,
        ):
            self.config = config
            self.auto = auto
            self.seqnum = 1
            self.conn_name = conn_name
            self.ip = config[conn_name]["OMSIP"]
            self.port = config[conn_name].getint("OMSPort")
            self.targetcompid = config[conn_name]["OMSTarget"].encode()
            self.sendercompid = config[conn_name]["OMSSender"].encode()
            self.beginstring = config[conn_name]["BeginString"].encode()
            self.heartbeat = config[conn_name]["OMSHeartBeat"].encode()

            self.header_fill = {
                8: self.beginstring,
                49: self.sendercompid,
                56: self.targetcompid,
            }

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.logged_on = False
            self.verbose = verbose
            self.filter_tags = filter_tags or {8, 9, 49, 56, 52, 10, 60, 11, 43, 97}
            self.timeout = timeout

            self._setup_logging(log_level)

        def _setup_logging(self, log_level: int) -> None:
            """Configure logging for the client."""
            self.log = logging.getLogger(f"FixClient-{self.conn_name}")
            self.log.setLevel(log_level)

            formatter = logging.Formatter(
                f"{colorama.Back.BLACK}[%(asctime)s - %(name)s - %(levelname)s]{colorama.Style.RESET_ALL} %(message)s"
            )

            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(formatter)

            self.log.addHandler(handler)

        def seq(self, no_raise: bool = False) -> int:
            if not no_raise and not self.logged_on:
                raise Exception(
                    "Next sequence number when not logged on can be meaningless. "
                    "Use no_raise kwarg to turn this exception off"
                )
            seqnum = self.seqnum
            self.seqnum += 1
            return seqnum

        @staticmethod
        def _set_keepalive_linux(
            sock: socket.socket,
            after_idle_sec: int = 1,
            interval_sec: int = 3,
            max_fails: int = 5,
        ) -> None:
            """Configure TCP keepalive for Linux systems."""
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, after_idle_sec)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)

        def connect(self) -> None:
            """Establish connection to the server."""
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._set_keepalive_linux(self.sock)
            self.sock.connect((self.ip, self.port))

        def reconnect(self) -> None:
            """Reconnect to the server and optionally logon."""
            self.sock.close()
            self.logged_on = False
            self.seqnum = 1
            self.connect()

            if self.auto:
                self.logon_recv_response()

        def close(self) -> None:
            """Close the connection."""
            self.sock.close()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        def logon_recv_response(self) -> None:
            """Send logon and handle response."""
            self.logon()

            while True:
                rmsg = self.recv_fix(log_level=logging.DEBUG)
                prmsg = fix.Message.parse(rmsg)

                if prmsg.msgtype == b"A":
                    self.log.info("Logged on response received")
                    break
                elif prmsg.msgtype == b"1":
                    self.log.debug(f"Test request received: {ch_delim(rmsg)}")
                    self.send_heartbeat(prmsg[112])
                elif prmsg.msgtype == b"2":
                    raise UnexpectedMessageException(
                        "Sequence number is off", offending_msg=prmsg
                    )
                else:
                    raise UnexpectedMessageException(
                        "Non-login response received", offending_msg=prmsg
                    )

        def logout_recv_response(self) -> None:
            """Send logout and handle response."""
            self.logout()

            while True:
                rmsg = self.recv_fix(log_level=logging.DEBUG)
                prmsg = fix.Message.parse(rmsg)

                if prmsg.msgtype == b"5":
                    self.log.info(f"Logged out response received: {prmsg}")
                    self.logged_on = False
                    break
                elif prmsg.msgtype == b"1":
                    self.log.debug(f"Test request received: {ch_delim(rmsg)}")
                    self.send_heartbeat(prmsg[112])
                elif prmsg.msgtype == b"2":
                    raise UnexpectedMessageException(
                        "Sequence number is off", offending_msg=prmsg
                    )
                else:
                    self.log.info(f"Other message received during logout: {prmsg}")

        @contextlib.contextmanager
        def session(self):
            """Context manager for the client session."""
            self.connect()
            self.seqnum = 1

            if self.auto:
                self.logon_recv_response()

            try:
                yield self
            finally:
                if self.auto:
                    try:
                        self.logout_recv_response()
                    except Exception as e:
                        self.log.error(f"Exception during logout: {e}")
                        # Re-raise if needed or handle appropriately
                self.close()

        def send_msg(self, msg: bytes, log_level: int = logging.INFO) -> None:
            """Send a FIX message."""
            self.sock.sendall(msg)

            if self.filter_tags:
                filtered_msg = b"| ".join(
                    t + b": " + v
                    for t, v in iter_rawmsg(msg)
                    if int(t.decode()) not in self.filter_tags
                )
                self.log.log(log_level, f">>: {filtered_msg}")
            else:
                self.log.log(log_level, f">>: {ch_delim(msg)}")

            # Use context manager for file handling
            with open("traffic.log", "a") as traffic_log:
                traffic_log.write(f"client sent >> OMS session: {msg.decode()}\n")

        def send_recv(self, msg: bytes) -> bytes:
            """Send a message and return the response."""
            self.send_msg(msg)
            return self.recv_fix()

        def new_msg(
            self,
            msgtype_cls: type,
            extra: Optional[OrderedDict] = None,
            seq: bool = True,
            **kwargs,
        ) -> fix.Message:
            """Create a new FIX message."""
            d = OrderedDict(self.header_fill)
            if seq:
                d[34] = str(self.seq()).encode()
            if extra:
                d.update(extra)
            return msgtype_cls(fix.Group(d), **kwargs)

        def recv_fix(
            self, *, up_to_tag9_anchor_len: int = 22, log_level: int = logging.INFO
        ) -> bytes:
            """Receive a FIX message."""
            msg_recv1 = self.sock.recv(up_to_tag9_anchor_len)
            if not msg_recv1:
                raise NoMessageResponseException()

            def get_bodylen(msg: bytes) -> tuple[int, int]:
                """Extract body length from FIX message."""
                after_tag9_equal_sign = msg.partition(b"\x01")[-1].partition(b"=")[-1]
                len_bytes, _, extra = after_tag9_equal_sign.partition(b"\x01")
                return int(len_bytes.decode()), len(extra)

            body_len, extra = get_bodylen(msg_recv1)
            msg_recv2 = self.sock.recv(body_len + 7 - extra)
            msg = msg_recv1 + msg_recv2

            if self.filter_tags:
                filtered_msg = b"| ".join(
                    t + b": " + v
                    for t, v in iter_rawmsg(msg)
                    if int(t.decode()) not in self.filter_tags
                )
                self.log.log(log_level, f"<<: {filtered_msg}")
            else:
                self.log.log(log_level, f"<<: {ch_delim(msg)}")

            with open("traffic.log", "a") as traffic_log:
                traffic_log.write(f"OMS sent >> client session: {msg.decode()}\n")

            return msg

        def _find_matching_message(
            self, check_field: int, expected_value: bytes
        ) -> Dict[bytes, bytes]:
            """Helper to find messages matching specific criteria."""
            while True:
                msg = self.recv_fix()
                parsed_msg = fix.Message.parse(msg)

                try:
                    if parsed_msg[check_field] == expected_value:
                        return parsed_msg
                except KeyError:
                    continue

        def recv_linked_ack_dic(
            self, org_ordId: bytes, org_seqNum: bytes
        ) -> Dict[bytes, bytes]:
            """Find acknowledgment with matching order ID and sequence number."""
            return self._find_matching_message(11, org_ordId)

        def recv_linked_ack_use_id(self, org_ordId: bytes) -> Dict[bytes, bytes]:
            """Find acknowledgment with matching order ID."""
            return self._find_matching_message(11, org_ordId)

        def recv_linked_ack_use_clientorderid(
            self, org_ordId: bytes
        ) -> Dict[bytes, bytes]:
            """Find acknowledgment with matching client order ID."""
            return self._find_matching_message(37, org_ordId)

        def logon(self) -> None:
            """Send logon message."""
            self.log.info("Logging on...")
            logon_msg = fix.LogonMessage(
                fix.Group(
                    {
                        **self.header_fill,
                        34: str(self.seq(no_raise=True)).encode(),
                        108: self.heartbeat,
                    }
                )
            )
            self.send_msg(bytes(logon_msg), log_level=logging.DEBUG)
            self.logged_on = True

        def logout(self) -> None:
            """Send logout message."""
            self.log.info("Logging out...")
            logout_msg = fix.LogoutMessage(
                fix.Group(
                    {
                        **self.header_fill,
                        34: str(self.seq(no_raise=True)).encode(),
                    }
                )
            )
            self.send_msg(bytes(logout_msg), log_level=logging.DEBUG)

        def send_heartbeat(self, testReqID: bytes) -> None:
            """Send heartbeat message."""
            heartbtmsg = fix.message.HeartBeatMessage(
                {
                    **self.header_fill,
                    34: str(self.seq(no_raise=True)).encode(),
                    112: testReqID,
                }
            )
            self.send_msg(bytes(heartbtmsg), log_level=logging.DEBUG)
