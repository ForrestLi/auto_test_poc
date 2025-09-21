import socket
import select
import struct
import threading
import time
import datetime
from collections import OrderedDict
from queue import Queue, Empty
from typing import Optional, Callable, List, Tuple
import logging

# Import your message modules
from .ahd_msg import *

logger = logging.getLogger(__name__)


class AHDClient:
    def __init__(
        self,
        remote_ip: str,
        remote_port: int,
        local_ip: str,
        local_port: int,
        participant_code: str,
        virtual_server_no: int,
        prefix: str = "VIRTUA",
        exchange_code: str = "1",
        market_code: str = "11",
    ):
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.local_ip = local_ip
        self.local_port = local_port
        self.participant_code = participant_code
        self.virtual_server_no = virtual_server_no
        self.exchange_code = exchange_code
        self.market_code = market_code

        self._heartbeats_allowed = False
        self.heartbeat_timeout = 1
        self.handle_heartbeats = True
        self.handlers = [self.default_handler]

        self.last_sent_internal = prefix + "0" * (20 - len(prefix))
        self.last_sent_order_entry_seq_no = 0
        self.last_rcvd_notice_seq_no = 0
        self.last_rcvd_execution_seq_no = 0

        self.send_queue: Optional[Queue] = None
        self.receive_queue: Optional[Queue] = None
        self.socket: Optional[socket.socket] = None
        self.recv_socket_pair: Optional[Tuple[socket.socket, socket.socket]] = None

        self._stop_event = threading.Event()

    def _generate_next_internal(self) -> str:
        """Generate next internal processing ID"""
        prefix = self.last_sent_internal.rstrip("0123456789")
        numeric_part = int(self.last_sent_internal[len(prefix) :])
        return f"{prefix}{numeric_part + 1:0{20 - len(prefix)}d}"

    def start(self):
        """Initialize and start the AHD client connection"""
        logger.info(
            "Starting AHD client %s:%d -> %s:%d",
            self.local_ip,
            self.local_port,
            self.remote_ip,
            self.remote_port,
        )

        self.send_queue = Queue()
        self.receive_queue = Queue()
        self._stop_event.clear()

        # Initialize sequence numbers
        self.last_sent_seq_no = 0
        self.last_sent_arm_sn = 0
        self.last_sent_sam_sn = 0
        self.last_rcvd_seq_no = 0
        self.last_rcvd_arm_sn = 0
        self.last_rcvd_sam_sn = 0

        # Create socket and connect
        self.socket = socket.socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0)
        )
        self.socket.bind((self.local_ip, self.local_port))

        # Connection retry logic
        for attempt in range(1, 14):
            try:
                self.socket.connect((self.remote_ip, self.remote_port))
                break
            except socket.error as e:
                if e.errno == 99 and attempt < 13:
                    logger.warning("Cannot connect: address taken, retrying...")
                    time.sleep(10)
                else:
                    raise
        else:
            self.socket.connect((self.remote_ip, self.remote_port))

        # Create socket pair for signaling
        self.recv_socket_pair = socket.socketpair()

        # Start threads
        self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)

        self.send_thread.start()
        self.receive_thread.start()

    def stop(self):
        """Stop the AHD client connection and clean up resources"""
        logger.info(
            "Stopping AHD client %s:%d -> %s:%d",
            self.local_ip,
            self.local_port,
            self.remote_ip,
            self.remote_port,
        )

        self._heartbeats_allowed = False
        self._stop_event.set()

        # Signal threads to stop
        if self.send_queue:
            self.send_queue.put(None)
        if self.recv_socket_pair:
            self.recv_socket_pair[0].send(b"x")

        # Wait for threads to terminate
        threads = []
        if self.send_thread.is_alive():
            threads.append(("send", self.send_thread))
        if self.receive_thread.is_alive():
            threads.append(("receive", self.receive_thread))

        for name, thread in threads:
            thread.join(timeout=2)
            if thread.is_alive():
                logger.error("%s thread didn't terminate properly", name.capitalize())

        # Clean up resources
        resources = [
            (self.socket, "socket"),
            (
                self.recv_socket_pair[0] if self.recv_socket_pair else None,
                "recv_socket_pair[0]",
            ),
            (
                self.recv_socket_pair[1] if self.recv_socket_pair else None,
                "recv_socket_pair[1]",
            ),
        ]

        for resource, name in resources:
            if resource:
                try:
                    resource.close()
                except Exception as e:
                    logger.error("Error closing %s: %s", name, e)

        self.send_queue = None
        self.receive_queue = None
        self.socket = None
        self.recv_socket_pair = None

    def _send_loop(self):
        """Main sending loop running in separate thread"""
        last_send = time.monotonic()

        while not self._stop_event.is_set():
            try:
                # Get message from queue with timeout
                msg = self.send_queue.get(timeout=1) if self.send_queue else None

                # Send heartbeat if needed
                if msg is None:
                    if (
                        self._heartbeats_allowed
                        and self.heartbeat_timeout
                        and time.monotonic() > last_send + self.heartbeat_timeout
                    ):
                        msg = self._prepare_msg(Heartbeat())
                    else:
                        continue

                # Exit if stop signal received
                if msg is ...:  # Using ... as stop signal
                    break

                # Send the message
                msg_bytes = bytes(msg)
                total_sent = 0

                while total_sent < len(msg_bytes) and not self._stop_event.is_set():
                    try:
                        sent = self.socket.send(msg_bytes[total_sent:])
                        if sent == 0:
                            raise ConnectionError("Socket connection broken")
                        total_sent += sent
                        last_send = time.monotonic()
                    except (BlockingIOError, socket.timeout):
                        continue

            except Empty:
                continue
            except Exception as e:
                logger.error("Error in send loop: %s", e)
                break

    def _prepare_msg(self, msg) -> bytes:
        """Prepare a message for sending with proper headers and sequence numbers"""
        # Add common layers if needed
        common_layers = [
            (AdminCommonOU, AdminCommonOULayers),
            (OrderCommonO, OrderCommonOLayers),
            (ESPCommon, ESPCommonLayers),
        ]

        for base, layers in common_layers:
            if base not in msg and any(layer in msg for layer in layers):
                msg = base() / msg

        # Set ESPCommon fields
        esp_layer = msg[ESPCommon]
        if esp_layer.SeqNo is None:
            esp_layer.SeqNo = self.last_sent_seq_no + 1
        if esp_layer.ResendFlag is None:
            esp_layer.ResendFlag = "0"
        if esp_layer.VirtualServerNo is None:
            esp_layer.VirtualServerNo = self.virtual_server_no
        if esp_layer.ParticipantCode is None:
            esp_layer.ParticipantCode = self.participant_code
        if esp_layer.ARMSN is None:
            esp_layer.ARMSN = self.last_rcvd_seq_no
        if esp_layer.SAMSN is None:
            esp_layer.SAMSN = 0

        now = datetime.datetime.now()
        if esp_layer.TransmissionDate is None:
            esp_layer.TransmissionDate = now.date()
        if esp_layer.TransmissionTime is None:
            esp_layer.TransmissionTime = now.time()

        # Update sequence numbers
        self.last_sent_seq_no = esp_layer.SeqNo
        self.last_sent_arm_sn = esp_layer.ARMSN
        self.last_sent_sam_sn = esp_layer.SAMSN

        # Set common fields in other layers
        common_layers = [OrderCommonO, OrderCommonQ, AdminCommonOU, AdminCommonQU]
        for layer in common_layers:
            if layer in msg:
                if msg[layer].ExchangeCode is None:
                    msg[layer].ExchangeCode = self.exchange_code
                if msg[layer].MarketCode is None:
                    msg[layer].MarketCode = self.market_code
                if msg[layer].ParticipantCode is None:
                    msg[layer].ParticipantCode = self.participant_code
                if msg[layer].VirtualServerNo is None:
                    msg[layer].VirtualServerNo = self.virtual_server_no

        # Handle order sequence numbers
        if OrderCommonO in msg or OrderCommonQ in msg:
            layer = OrderCommonO if OrderCommonO in msg else OrderCommonQ
            if msg[layer].OrderEntrySeqNo is None:
                msg[layer].OrderEntrySeqNo = self.last_sent_order_entry_seq_no + 1
            if layer is OrderCommonO:
                self.last_sent_order_entry_seq_no = msg[layer].OrderEntrySeqNo

        # Handle new order internal processing ID
        if NewOrder in msg and msg[NewOrder].InternalProcessing is None:
            self.last_sent_internal = self._generate_next_internal()
            msg[NewOrder].InternalProcessing = self.last_sent_internal

        return bytes(msg)

    def send_msg(self, msg):
        """Prepare and queue a message for sending"""
        prepared_msg = self._prepare_msg(msg)
        if self.send_queue:
            self.send_queue.put(prepared_msg)
        return prepared_msg

    def _receive_loop(self):
        """Main receiving loop running in separate thread"""
        if not self.socket or not self.recv_socket_pair:
            return

        poller = select.poll()
        poller.register(self.socket.fileno(), select.POLLIN)
        poller.register(self.recv_socket_pair[1].fileno(), select.POLLIN)

        header_size = len(ESPCommon())

        while not self._stop_event.is_set():
            try:
                # Wait for data with timeout
                events = poller.poll(1000)  # 1 second timeout
                if not events:
                    continue

                # Check if we should stop
                for fd, event in events:
                    if fd == self.recv_socket_pair[1].fileno():
                        return

                # Read header
                header_data = self._receive_exact(header_size)
                if not header_data:
                    break

                header = ESPCommon(header_data)

                # Read remaining message
                remaining_size = header.MessageLength - header_size + 5
                message_data = self._receive_exact(remaining_size)
                if not message_data:
                    break

                msg = ESPCommon(header_data + message_data)

                # Update sequence numbers
                self.last_rcvd_seq_no = msg[ESPCommon].SeqNo
                self.last_rcvd_arm_sn = msg[ESPCommon].ARMSN
                self.last_rcvd_sam_sn = msg[ESPCommon].SAMSN

                # Update notice/execution sequence numbers
                if NoticeCommonO in msg:
                    cls_name = msg[NoticeCommonO].payload.__class__.__name__
                    if cls_name.endswith(("AcceptanceNotice", "AcceptanceError")):
                        self.last_rcvd_notice_seq_no = msg[NoticeCommonO].NoticeSeqNo
                    else:
                        self.last_rcvd_execution_seq_no = msg[NoticeCommonO].NoticeSeqNo

                # Handle message with registered handlers
                handled = any(handler(msg) for handler in self.handlers)

                if not handled and self.receive_queue:
                    self.receive_queue.put(msg)

            except Exception as e:
                logger.error("Error in receive loop: %s", e)
                break

    def _receive_exact(self, size: int) -> Optional[bytes]:
        """Receive exactly size bytes from socket"""
        data = b""
        while len(data) < size and not self._stop_event.is_set():
            try:
                chunk = self.socket.recv(size - len(data))
                if not chunk:
                    return None
                data += chunk
            except (BlockingIOError, socket.timeout):
                continue
        return data

    def default_handler(self, msg) -> bool:
        """Default message handler (filters heartbeats)"""
        return Heartbeat in msg and self.handle_heartbeats

    def receive_msg(self, timeout: float = 10.0):
        """Get a received message from the queue"""
        if self.receive_queue:
            return self.receive_queue.get(timeout=timeout)
        raise RuntimeError("Receive queue not initialized")

    def login(self):
        """Perform login sequence"""
        self.send_msg(LoginRequest())
        response = self.receive_msg()
        assert LoginResponse in response
        self.last_sent_seq_no = response[ESPCommon].ARMSN
        self._heartbeats_allowed = True

    def admin_start(self):
        """Wait for market admin message"""
        while True:
            msg = self.receive_msg()
            if MarketAdmin in msg:
                break

    def op_start(self):
        """Send operation start request"""
        self.send_msg(
            OpStart(
                AcceptanceSeqNo=self.last_rcvd_notice_seq_no,
                ExecutionSeqNo=self.last_rcvd_execution_seq_no,
            )
        )

        while True:
            msg = self.receive_msg()
            if OpStartResponse in msg:
                break
            assert OpStartErrorResponse not in msg

    def logout(self):
        """Perform logout sequence"""
        self.send_msg(PreLogoutRequest())
        while True:
            msg = self.receive_msg()
            if PreLogoutResponse in msg:
                break

        self.send_msg(LogoutRequest())
        response = self.receive_msg()
        assert LogoutResponse in response
