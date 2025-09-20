#!/usr/bin/env python3
"""
FIX Message Handler Module

Classes for building and parsing FIX messages
"""

import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import fix_msg

# TODO
# Need to add specific CUSTOM tags (e.g. the ones used to measure different component's performance
# & repeating groups' handling here later


# FIX Protocol Version
class FixVersion(Enum):
    FIX42 = "FIX.4.2"
    FIX44 = "FIX.4.4"
    FIX50 = "FIX.5.0"
    FIX50SP2 = "FIX.5.0SP2"


# FIX Message Types
class MsgType(Enum):
    HEARTBEAT = "0"
    TEST_REQUEST = "1"
    RESEND_REQUEST = "2"
    REJECT = "3"
    SEQUENCE_RESET = "4"
    LOGOUT = "5"
    LOGON = "A"
    NEW_ORDER_SINGLE = "D"
    EXECUTION_REPORT = "8"
    ORDER_CANCEL_REQUEST = "F"
    ORDER_CANCEL_REPLACE_REQUEST = "G"
    ORDER_CANCEL_REJECT = "9"
    BUSINESS_MESSAGE_REJECT = "j"


# FIX Fields
class Field(Enum):
    BEGIN_STRING = 8
    BODY_LENGTH = 9
    MSG_TYPE = 35
    SENDER_COMP_ID = 49
    TARGET_COMP_ID = 56
    MSG_SEQ_NUM = 34
    SENDING_TIME = 52
    CHECKSUM = 10
    ENCRYPT_METHOD = 98
    HEART_BT_INT = 108
    TEST_REQ_ID = 112
    ORIG_SENDING_TIME = 122
    GAP_FILL_FLAG = 123
    NEW_SEQ_NO = 36
    TEXT = 58
    ENCODED_TEXT_LEN = 354
    ENCODED_TEXT = 355
    POSS_DUP_FLAG = 43
    RESET_SEQ_NUM_FLAG = 141
    SESSION_REJECT_REASON = 373
    REF_MSG_TYPE = 372
    REF_TAG_ID = 371
    REF_SEQ_NUM = 45
    CL_ORD_ID = 11
    ORDER_ID = 37
    EXEC_ID = 17
    EXEC_TYPE = 150
    ORD_STATUS = 39
    SIDE = 54
    SYMBOL = 55
    ORDER_QTY = 38
    ORD_TYPE = 40
    PRICE = 44
    TIME_IN_FORCE = 59
    LAST_QTY = 32
    LAST_PX = 31
    LEAVES_QTY = 151
    CUM_QTY = 14
    AVG_PX = 6
    TRANSACT_TIME = 60
    ORIG_CL_ORD_ID = 41
    CXL_REJ_RESPONSE_TO = 434
    CXL_REJ_REASON = 102
    SECURITY_EXCHANGE = 207


# FIX Field Values
class Side(Enum):
    BUY = "1"
    SELL = "2"
    BUY_MINUS = "3"
    SELL_PLUS = "4"
    SELL_SHORT = "5"
    SELL_SHORT_EXEMPT = "6"
    UNDISCLOSED = "7"
    CROSS = "8"
    CROSS_SHORT = "9"


class OrdType(Enum):
    MARKET = "1"
    LIMIT = "2"
    STOP = "3"
    STOP_LIMIT = "4"
    MARKET_ON_CLOSE = "5"
    WITH_OR_WITHOUT = "6"
    LIMIT_OR_BETTER = "7"
    LIMIT_WITH_OR_WITHOUT = "8"
    ON_BASIS = "9"
    ON_CLOSE = "A"
    LIMIT_ON_CLOSE = "B"
    FOREX_MARKET = "C"
    PREVIOUSLY_QUOTED = "D"
    PREVIOUSLY_INDICATED = "E"
    FOREX_LIMIT = "F"
    FOREX_SWAP = "G"
    FOREX_PREVIOUSLY_QUOTED = "H"
    FUNARI = "I"
    MARKET_IF_TOUCHED = "J"
    MARKET_WITH_LEFTOVER = "K"
    PREVIOUS_FUND_VALUATION_POINT = "L"
    NEXT_FUND_VALUATION_POINT = "M"
    PEGGED = "P"


class TimeInForce(Enum):
    DAY = "0"
    GOOD_TILL_CANCEL = "1"
    AT_THE_OPENING = "2"
    IMMEDIATE_OR_CANCEL = "3"
    FILL_OR_KILL = "4"
    GOOD_TILL_CROSSING = "5"
    GOOD_TILL_DATE = "6"
    AT_THE_CLOSE = "7"


class ExecType(Enum):
    NEW = "0"
    PARTIAL_FILL = "1"
    FILL = "2"
    DONE_FOR_DAY = "3"
    CANCELED = "4"
    REPLACE = "5"
    PENDING_CANCEL = "6"
    STOPPED = "7"
    REJECTED = "8"
    SUSPENDED = "9"
    PENDING_NEW = "A"
    CALCULATED = "B"
    EXPIRED = "C"
    RESTATED = "D"
    PENDING_REPLACE = "E"
    TRADE = "F"
    TRADE_CORRECT = "G"
    TRADE_CANCEL = "H"
    ORDER_STATUS = "I"


class OrdStatus(Enum):
    NEW = "0"
    PARTIALLY_FILLED = "1"
    FILLED = "2"
    DONE_FOR_DAY = "3"
    CANCELED = "4"
    REPLACED = "5"
    PENDING_CANCEL = "6"
    STOPPED = "7"
    REJECTED = "8"
    SUSPENDED = "9"
    PENDING_NEW = "A"
    CALCULATED = "B"
    EXPIRED = "C"
    ACCEPTED_FOR_BIDDING = "D"
    PENDING_REPLACE = "E"


class FixMessage:
    """Base class for FIX messages"""

    def __init__(self, fix_version: FixVersion = FixVersion.FIX44):
        self.fix_version = fix_version
        self.msg_type = None
        self.fields = {}
        self.set_field(Field.BEGIN_STRING, fix_version.value)

    def set_field(self, field: Field, value: Any):
        """Set a FIX field value"""
        self.fields[field.value] = str(value)

    def get_field(self, field: Field) -> Optional[str]:
        """Get a FIX field value"""
        return self.fields.get(field.value)

    def to_fix_string(self) -> str:
        """Convert message to FIX string format"""
        # Create a copy of fields to avoid modifying the original
        fields = self.fields.copy()

        # Set message type if not already set
        if Field.MSG_TYPE.value not in fields and self.msg_type:
            fields[Field.MSG_TYPE.value] = self.msg_type.value

        # Add body length and checksum
        fix_str = self._build_fix_string(fields)
        return fix_str

    def _build_fix_string(self, fields: Dict[int, str]) -> str:
        """Build the FIX string with proper body length and checksum"""
        # Remove body length and checksum if present (we'll recalculate them)
        fields.pop(Field.BODY_LENGTH.value, None)
        fields.pop(Field.CHECKSUM.value, None)

        # Build the message without body length and checksum
        fix_parts = []
        for tag, value in sorted(fields.items()):
            fix_parts.append(f"{tag}={value}")

        body = "|".join(fix_parts) + "|"

        # Calculate body length (number of characters between BodyLength and Checksum)
        body_length = len(body)

        # Add body length field
        fix_msg = f"8={self.fix_version.value}|9={body_length}|{body}"

        # Calculate checksum (sum of all bytes mod 256)
        checksum = sum(fix_msg.encode("ascii")) % 256
        checksum_str = f"{checksum:03d}"

        # Add checksum
        fix_msg += f"10={checksum_str}|"

        return fix_msg

    def parse_fix_string(self, fix_string: str):
        """Parse a FIX string into this message object"""
        # Reset fields
        self.fields = {}

        # Split the FIX string into tag=value pairs
        parts = fix_string.split("|")
        for part in parts:
            if "=" in part:
                tag_str, value = part.split("=", 1)
                try:
                    tag = int(tag_str)
                    self.fields[tag] = value
                except ValueError:
                    # Skip invalid tags
                    continue

        # Set message type if available
        msg_type_val = self.fields.get(Field.MSG_TYPE.value)
        if msg_type_val:
            for msg_type in MsgType:
                if msg_type.value == msg_type_val:
                    self.msg_type = msg_type
                    break

    def __str__(self) -> str:
        return self.to_fix_string()


class LogonMessage(FixMessage):
    """FIX Logon Message (A)"""

    def __init__(self, fix_version: FixVersion = FixVersion.FIX44):
        super().__init__(fix_version)
        self.msg_type = MsgType.LOGON

    def set_heartbeat_interval(self, interval: int):
        """Set heartbeat interval"""
        self.set_field(Field.HEART_BT_INT, interval)

    def set_encrypt_method(self, method: int = 0):
        """Set encryption method (0 = None)"""
        self.set_field(Field.ENCRYPT_METHOD, method)

    def set_reset_seq_num_flag(self, reset: bool = True):
        """Set reset sequence number flag"""
        self.set_field(Field.RESET_SEQ_NUM_FLAG, "Y" if reset else "N")


class LogoutMessage(FixMessage):
    """FIX Logout Message (5)"""

    def __init__(self, fix_version: FixVersion = FixVersion.FIX44):
        super().__init__(fix_version)
        self.msg_type = MsgType.LOGOUT

    def set_text(self, text: str):
        """Set logout text"""
        self.set_field(Field.TEXT, text)


class HeartbeatMessage(FixMessage):
    """FIX Heartbeat Message (0)"""

    def __init__(self, fix_version: FixVersion = FixVersion.FIX44):
        super().__init__(fix_version)
        self.msg_type = MsgType.HEARTBEAT

    def set_test_req_id(self, req_id: str):
        """Set test request ID"""
        self.set_field(Field.TEST_REQ_ID, req_id)


class TestRequestMessage(FixMessage):
    """FIX Test Request Message (1)"""

    def __init__(self, fix_version: FixVersion = FixVersion.FIX44):
        super().__init__(fix_version)
        self.msg_type = MsgType.TEST_REQUEST

    def set_test_req_id(self, req_id: str):
        """Set test request ID"""
        self.set_field(Field.TEST_REQ_ID, req_id)


class ResendRequestMessage(FixMessage):
    """FIX Resend Request Message (2)"""

    def __init__(self, fix_version: FixVersion = FixVersion.FIX44):
        super().__init__(fix_version)
        self.msg_type = MsgType.RESEND_REQUEST

    def set_begin_seq_no(self, seq_no: int):
        """Set beginning sequence number"""
        self.set_field(Field.BEGIN_SEQ_NO, seq_no)

    def set_end_seq_no(self, seq_no: int):
        """Set ending sequence number"""
        self.set_field(Field.END_SEQ_NO, seq_no)


class SequenceResetMessage(FixMessage):
    """FIX Sequence Reset Message (4)"""

    def __init__(self, fix_version: FixVersion = FixVersion.FIX44):
        super().__init__(fix_version)
        self.msg_type = MsgType.SEQUENCE_RESET

    def set_gap_fill_flag(self, gap_fill: bool = True):
        """Set gap fill flag"""
        self.set_field(Field.GAP_FILL_FLAG, "Y" if gap_fill else "N")

    def set_new_seq_no(self, seq_no: int):
        """Set new sequence number"""
        self.set_field(Field.NEW_SEQ_NO, seq_no)


class RejectMessage(FixMessage):
    """FIX Reject Message (3)"""

    def __init__(self, fix_version: FixVersion = FixVersion.FIX44):
        super().__init__(fix_version)
        self.msg_type = MsgType.REJECT

    def set_ref_seq_num(self, seq_num: int):
        """Set reference sequence number"""
        self.set_field(Field.REF_SEQ_NUM, seq_num)

    def set_ref_tag_id(self, tag_id: int):
        """Set reference tag ID"""
        self.set_field(Field.REF_TAG_ID, tag_id)

    def set_ref_msg_type(self, msg_type: MsgType):
        """Set reference message type"""
        self.set_field(Field.REF_MSG_TYPE, msg_type.value)

    def set_session_reject_reason(self, reason: int):
        """Set session reject reason"""
        self.set_field(Field.SESSION_REJECT_REASON, reason)

    def set_text(self, text: str):
        """Set reject text"""
        self.set_field(Field.TEXT, text)


class NewOrderSingleMessage(FixMessage):
    """FIX New Order Single Message (D)"""

    def __init__(self, fix_version: FixVersion = FixVersion.FIX44):
        super().__init__(fix_version)
        self.msg_type = MsgType.NEW_ORDER_SINGLE

    def set_cl_ord_id(self, cl_ord_id: str):
        """Set client order ID"""
        self.set_field(Field.CL_ORD_ID, cl_ord_id)

    def set_symbol(self, symbol: str):
        """Set symbol"""
        self.set_field(Field.SYMBOL, symbol)

    def set_side(self, side: Side):
        """Set side"""
        self.set_field(Field.SIDE, side.value)

    def set_order_qty(self, qty: float):
        """Set order quantity"""
        self.set_field(Field.ORDER_QTY, qty)

    def set_ord_type(self, ord_type: OrdType):
        """Set order type"""
        self.set_field(Field.ORD_TYPE, ord_type.value)

    def set_price(self, price: float):
        """Set price (for limit orders)"""
        self.set_field(Field.PRICE, price)

    def set_time_in_force(self, tif: TimeInForce):
        """Set time in force"""
        self.set_field(Field.TIME_IN_FORCE, tif.value)

    def set_transact_time(self, time: datetime.datetime = None):
        """Set transaction time (defaults to now)"""
        if time is None:
            time = datetime.datetime.utcnow()
        self.set_field(Field.TRANSACT_TIME, time.strftime("%Y%m%d-%H:%M:%S.%f")[:-3])


class ExecutionReportMessage(FixMessage):
    """FIX Execution Report Message (8)"""

    def __init__(self, fix_version: FixVersion = FixVersion.FIX44):
        super().__init__(fix_version)
        self.msg_type = MsgType.EXECUTION_REPORT

    def set_order_id(self, order_id: str):
        """Set order ID"""
        self.set_field(Field.ORDER_ID, order_id)

    def set_cl_ord_id(self, cl_ord_id: str):
        """Set client order ID"""
        self.set_field(Field.CL_ORD_ID, cl_ord_id)

    def set_exec_id(self, exec_id: str):
        """Set execution ID"""
        self.set_field(Field.EXEC_ID, exec_id)

    def set_exec_type(self, exec_type: ExecType):
        """Set execution type"""
        self.set_field(Field.EXEC_TYPE, exec_type.value)

    def set_ord_status(self, ord_status: OrdStatus):
        """Set order status"""
        self.set_field(Field.ORD_STATUS, ord_status.value)

    def set_symbol(self, symbol: str):
        """Set symbol"""
        self.set_field(Field.SYMBOL, symbol)

    def set_side(self, side: Side):
        """Set side"""
        self.set_field(Field.SIDE, side.value)

    def set_order_qty(self, qty: float):
        """Set order quantity"""
        self.set_field(Field.ORDER_QTY, qty)

    def set_leaves_qty(self, qty: float):
        """Set leaves quantity"""
        self.set_field(Field.LEAVES_QTY, qty)

    def set_cum_qty(self, qty: float):
        """Set cumulative quantity"""
        self.set_field(Field.CUM_QTY, qty)

    def set_avg_px(self, px: float):
        """Set average price"""
        self.set_field(Field.AVG_PX, px)

    def set_last_qty(self, qty: float):
        """Set last quantity"""
        self.set_field(Field.LAST_QTY, qty)

    def set_last_px(self, px: float):
        """Set last price"""
        self.set_field(Field.LAST_PX, px)

    def set_transact_time(self, time: datetime.datetime = None):
        """Set transaction time (defaults to now)"""
        if time is None:
            time = datetime.datetime.utcnow()
        self.set_field(Field.TRANSACT_TIME, time.strftime("%Y%m%d-%H:%M:%S.%f")[:-3])


class OrderCancelRequestMessage(FixMessage):
    """FIX Order Cancel Request Message (F)"""

    def __init__(self, fix_version: FixVersion = FixVersion.FIX44):
        super().__init__(fix_version)
        self.msg_type = MsgType.ORDER_CANCEL_REQUEST

    def set_orig_cl_ord_id(self, orig_cl_ord_id: str):
        """Set original client order ID"""
        self.set_field(Field.ORIG_CL_ORD_ID, orig_cl_ord_id)

    def set_cl_ord_id(self, cl_ord_id: str):
        """Set client order ID"""
        self.set_field(Field.CL_ORD_ID, cl_ord_id)

    def set_symbol(self, symbol: str):
        """Set symbol"""
        self.set_field(Field.SYMBOL, symbol)

    def set_side(self, side: Side):
        """Set side"""
        self.set_field(Field.SIDE, side.value)

    def set_order_qty(self, qty: float):
        """Set order quantity"""
        self.set_field(Field.ORDER_QTY, qty)

    def set_transact_time(self, time: datetime.datetime = None):
        """Set transaction time (defaults to now)"""
        if time is None:
            time = datetime.datetime.utcnow()
        self.set_field(Field.TRANSACT_TIME, time.strftime("%Y%m%d-%H:%M:%S.%f")[:-3])


class OrderCancelReplaceRequestMessage(FixMessage):
    """FIX Order Cancel/Replace Request Message (G)"""

    def __init__(self, fix_version: FixVersion = FixVersion.FIX44):
        super().__init__(fix_version)
        self.msg_type = MsgType.ORDER_CANCEL_REPLACE_REQUEST

    def set_orig_cl_ord_id(self, orig_cl_ord_id: str):
        """Set original client order ID"""
        self.set_field(Field.ORIG_CL_ORD_ID, orig_cl_ord_id)

    def set_cl_ord_id(self, cl_ord_id: str):
        """Set client order ID"""
        self.set_field(Field.CL_ORD_ID, cl_ord_id)

    def set_symbol(self, symbol: str):
        """Set symbol"""
        self.set_field(Field.SYMBOL, symbol)

    def set_side(self, side: Side):
        """Set side"""
        self.set_field(Field.SIDE, side.value)

    def set_order_qty(self, qty: float):
        """Set order quantity"""
        self.set_field(Field.ORDER_QTY, qty)

    def set_ord_type(self, ord_type: OrdType):
        """Set order type"""
        self.set_field(Field.ORD_TYPE, ord_type.value)

    def set_price(self, price: float):
        """Set price (for limit orders)"""
        self.set_field(Field.PRICE, price)

    def set_transact_time(self, time: datetime.datetime = None):
        """Set transaction time (defaults to now)"""
        if time is None:
            time = datetime.datetime.utcnow()
        self.set_field(Field.TRANSACT_TIME, time.strftime("%Y%m%d-%H:%M:%S.%f")[:-3])


class OrderCancelRejectMessage(FixMessage):
    """FIX Order Cancel Reject Message (9)"""

    def __init__(self, fix_version: FixVersion = FixVersion.FIX44):
        super().__init__(fix_version)
        self.msg_type = MsgType.ORDER_CANCEL_REJECT

    def set_order_id(self, order_id: str):
        """Set order ID"""
        self.set_field(Field.ORDER_ID, order_id)

    def set_cl_ord_id(self, cl_ord_id: str):
        """Set client order ID"""
        self.set_field(Field.CL_ORD_ID, cl_ord_id)

    def set_orig_cl_ord_id(self, orig_cl_ord_id: str):
        """Set original client order ID"""
        self.set_field(Field.ORIG_CL_ORD_ID, orig_cl_ord_id)

    def set_ord_status(self, ord_status: OrdStatus):
        """Set order status"""
        self.set_field(Field.ORD_STATUS, ord_status.value)

    def set_cxl_rej_response_to(self, response_to: int):
        """Set cancel reject response to"""
        self.set_field(Field.CXL_REJ_RESPONSE_TO, response_to)

    def set_cxl_rej_reason(self, reason: int):
        """Set cancel reject reason"""
        self.set_field(Field.CXL_REJ_REASON, reason)

    def set_text(self, text: str):
        """Set reject text"""
        self.set_field(Field.TEXT, text)


class FixMessageFactory:
    """Factory for creating FIX messages from strings"""

    @staticmethod
    def from_string(fix_string: str) -> Optional[FixMessage]:
        """Create a FIX message from a string"""
        # Extract message type
        msg_type = None
        parts = fix_string.split("|")
        for part in parts:
            if part.startswith("35="):
                msg_type_val = part[3:]
                for mt in MsgType:
                    if mt.value == msg_type_val:
                        msg_type = mt
                        break
                break

        if not msg_type:
            return None

        # Create appropriate message type
        if msg_type == MsgType.LOGON:
            msg = LogonMessage()
        elif msg_type == MsgType.LOGOUT:
            msg = LogoutMessage()
        elif msg_type == MsgType.HEARTBEAT:
            msg = HeartbeatMessage()
        elif msg_type == MsgType.TEST_REQUEST:
            msg = TestRequestMessage()
        elif msg_type == MsgType.RESEND_REQUEST:
            msg = ResendRequestMessage()
        elif msg_type == MsgType.SEQUENCE_RESET:
            msg = SequenceResetMessage()
        elif msg_type == MsgType.REJECT:
            msg = RejectMessage()
        elif msg_type == MsgType.NEW_ORDER_SINGLE:
            msg = NewOrderSingleMessage()
        elif msg_type == MsgType.EXECUTION_REPORT:
            msg = ExecutionReportMessage()
        elif msg_type == MsgType.ORDER_CANCEL_REQUEST:
            msg = OrderCancelRequestMessage()
        elif msg_type == MsgType.ORDER_CANCEL_REPLACE_REQUEST:
            msg = OrderCancelReplaceRequestMessage()
        elif msg_type == MsgType.ORDER_CANCEL_REJECT:
            msg = OrderCancelRejectMessage()
        else:
            # Generic message for unsupported types
            msg = FixMessage()
            msg.msg_type = msg_type

        # Parse the string
        msg.parse_fix_string(fix_string)
        return msg
