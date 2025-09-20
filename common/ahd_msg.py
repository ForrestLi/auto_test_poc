#!/usr/bin/env python3
"""
Arrowhead Message Module
"""

import datetime
from enum import Enum, auto
from typing import Optional, Union, Dict, Any
from scapy.all import *
from scapy_utils import *


# Enums for better type safety and readability
class Side(Enum):
    SELL = "1"
    BUY = "3"


class ExecCond(Enum):
    NONE = "0"
    AT_OPEN = "2"
    AT_CLOSE = "4"
    FUNARI = "6"
    IOC = "8"


class PropBrokerageClass(Enum):
    BROKERAGE = "0"
    PROPRIETARY = "9"


class CashMarginCode(Enum):
    CASH = "0"
    TRUST = "2"
    LIQUIDATION = "4"


class ShortSellFlag(Enum):
    NONE = "0"
    WITH_PRICE_REG = "5"
    WITHOUT_PRICE_REG = "7"


class StabArbCode(Enum):
    NONE = "0"
    STABILIZATION = "6"
    ARBITRAGE = "8"


class OrderAttrCode(Enum):
    AUTOMATIC = "1"
    MANUAL = "2"
    LLT_MARKET_MAKING = "3"
    LLT_ARBITRAGE = "4"
    LLT_DIRECTIONAL = "5"
    LLT_OTHER = "6"


class SuppMemberClass(Enum):
    NONE = "0"
    SUPPORT_MEMBER_ORDER = "1"


class DataClassCode(Enum):
    NEW_ORDER = "1111"
    MOD_ORDER = "9132"
    CANCEL_ORDER = "7122"


class ExchClassCode(Enum):
    TOKYO = "1"
    NAGOYA = "3"
    FUKUOKA = "6"
    SAPPORO = "8"


class MarketClassCode(Enum):
    COMMON_INFO = "10"
    STOCKS = "11"
    CB = "12"


class ESPMsgTypeUp(Enum):
    LOGIN_REQUEST = "01"
    PRE_LOGOUT_REQUEST = "02"
    LOGOUT_REQUEST = "03"
    LOGOUT_RESPONSE = "04"
    HEARTBEAT = "05"
    RESEND_REQUEST = "06"
    SKIP = "07"
    REJECT = "08"
    QUERY_OP = "41"
    QUERY_ADM = "81"
    DC_OP = "42"
    DC_ADM = "82"


class MsgType(Enum):
    # ESP
    LOGIN_REQUEST = "01"
    PRE_LOGOUT_REQUEST = "02"
    LOGOUT_REQUEST = "03"
    LOGOUT_RESPONSE = "04"
    HEARTBEAT = "05"
    RESEND_REQUEST = "06"
    SKIP = "07"
    REJECT = "08"
    # Admin
    MARKET_ADMIN = "90"
    TRADING_HALT = "90"
    PRICE_LIMIT_INFO = "90"
    FREE_FORM_WARNING = "90"
    OP_START = "80"
    OP_START_RESPONSE = "90"
    OP_END = "80"
    OP_END_RESPONSE = "90"
    ADMIN_COMMON = "80"
    NOTICE_DEST_SETUP_REQUEST = "80"
    NOTICE_DEST_SETUP_RESPONSE = "90"
    NOTICE_DEST_ENQ_REQUEST = "80"
    NOTICE_DEST_ENQ_RESPONSE = "90"
    PROXY_REQUEST = "80"
    PROXY_RESPONSE = "90"
    PROXY_ABORT_REQUEST = "80"
    PROXY_ABORT_RESPONSE = "90"
    PROXY_STATUS_ENQ_REQUEST = "80"
    PROXY_STATUS_ENQ_RESPONSE = "90"
    RETRANSMISSION_REQUEST = "80"
    RETRANSMISSION_RESPONSE = "90"
    ORD_SEQ_NUM_ENQ = "80"
    ORD_SEQ_NUM_ENQ_RESPONSE = "90"
    NOTICE_SEQ_NUM_ENQ = "80"
    NOTICE_SEQ_NUM_ENQ_RESPONSE = "90"
    SYSTEM_ERROR = "80"
    # Ops
    ORDER_COMMON = "40"
    NEW_ORDER = "40"
    MOD_ORDER = "40"
    CANCEL_ORDER = "40"
    NEW_ORDER_ACCEPTANCE_NOTICE = "50"
    NEW_ORDER_ACCEPTANCE_ERROR = "50"
    NEW_ORDER_REGISTRATION_ERROR = "50"
    MOD_ACCEPTANCE_NOTICE = "50"
    MOD_ACCEPTANCE_ERROR = "50"
    MOD_REGISTRATION_ERROR = "50"
    MOD_RESULT_NOTICE = "50"
    CANCEL_ORDER_ACCEPTANCE_NOTICE = "50"
    CANCEL_ORDER_ACCEPTANCE_ERROR = "50"
    CANCEL_ORDER_REGISTRATION_ERROR = "50"
    CANCEL_ORDER_RESULT_NOTICE = "50"
    EXECUTION_COMPLETION_NOTICE = "50"
    INVALIDATION_RESULT_NOTICE = "50"
    ACCEPTANCE_OUTPUT_COMPLETION_NOTICE = "50"
    EXECUTION_OUTPUT_COMPLETION_NOTICE = "50"


class ESPMsgTypeDown(Enum):
    LOGIN_RESPONSE = "11"
    PRE_LOGOUT_RESPONSE = "12"
    LOGOUT_REQUEST = "13"
    LOGOUT_RESPONSE = "14"
    HEARTBEAT = "15"
    RESEND_REQUEST = "16"
    SKIP = "17"
    REJECT_DOWN = "18"
    QUERY_OP = "51"
    QUERY_ADM = "91"
    DC_OP = "52"
    DC_ADM = "92"


class RejectReason(Enum):
    INCORRECT_MESSAGE_TYPE = "0001"
    INCORRECT_MESSAGE_SEQUENCE_NUMBER = "0002"
    INCORRECT_PARTICIPANT_CODE = "0003"
    INCORRECT_VIRTUAL_SERVER_NUMBER = "0004"
    INCORRECT_RESEND_FLAG = "0005"
    INCORRECT_RESEND_START_MESSAGE_SEQ_NUM = "0006"
    MSN_GREATER_THAN_CURRENT_SAMSN = "0007"
    INCORRECT_ARMSN = "0008"
    INCORRECT_SAMSN = "0009"
    INCORRECT_MESSAGE_LENGTH = "0010"
    INCORRECT_NUM_OF_DATA_TRANSACTION = "0011"
    INCORRECT_SKIP_MSG_SEQ_NUM = "0012"
    INCORRECT_FORMAT = "0013"


class LogoutReason(Enum):
    LOGOUT_REQUEST_IS_VALID = "0000"
    INCORRECT_MSG_LENGTH = "0101"
    TIME_OUT_PRE_LOGOUT_RESPONSE_TIMER = "0102"
    TIME_OUT_LOGOUT_REQUEST_TIMER = "0103"
    TIME_OUT_HEARTBEAT_RECEIPT_TIMER = "0105"
    NUMBER_OF_TIMES_OF_RE_RESEND_REQUEST_IS_REACHED = "0106"
    NUMBER_OF_TIMES_OF_REJECT_MESSAGE_IS_REACHED = "0107"
    NUMBER_OF_TIMES_SAME_MESSAGE_RECEIVED_REPEATEDLY_IS_REACHED = "0108"
    ESP_LINK_RELEASED_BY_INSTRUCTIONS_OF_THE_UPPER_LAYER = "0109"
    SYSTEM_ERROR = "0199"


# Create WENUMS from the Enums
WENUMS = {
    "Side": {e.name: e.value for e in Side},
    "ExecCond": {e.name: e.value for e in ExecCond},
    "PropBrokerageClass": {e.name: e.value for e in PropBrokerageClass},
    "CashMarginCode": {e.name: e.value for e in CashMarginCode},
    "ShortSellFlag": {e.name: e.value for e in ShortSellFlag},
    "StabArbCode": {e.name: e.value for e in StabArbCode},
    "OrderAttrCode": {e.name: e.value for e in OrderAttrCode},
    "SuppMemberClass": {e.name: e.value for e in SuppMemberClass},
    "DataClassCode": {e.name: e.value for e in DataClassCode},
    "ExchClassCode": {e.name: e.value for e in ExchClassCode},
    "MarketClassCode": {e.name: e.value for e in MarketClassCode},
    "ESPMsgTypeUp": {e.name: e.value for e in ESPMsgTypeUp},
    "MsgType": {e.name: e.value for e in MsgType},
    "ESPMsgTypeDown": {e.name: e.value for e in ESPMsgTypeDown},
    "RejectReason": {e.name: e.value for e in RejectReason},
    "LogoutReason": {e.name: e.value for e in LogoutReason},
}

# Create reverse mapping
RENUMS = {tag: {v: k for k, v in vals.items()} for tag, vals in WENUMS.items()}


class PriceField(LPaddedStrFixedLenField):
    __slots__ = ["fmt", "factor"]

    def __init__(
        self, name: str, default: Any, integer_digits: int, decimal_digits: int
    ):
        super().__init__(
            name, default, integer_digits + decimal_digits + 1, undefined_value=""
        )
        self.fmt = f"{{0:0{decimal_digits + 1}d}}"
        self.factor = float(10**decimal_digits)

    def i2m(self, pkt: Optional[Packet], x: Any) -> str:
        if x is None:
            return super().i2m(pkt, x)
        elif x == "market":
            length = self.length_from(pkt)
            return super().i2m(pkt, ("0" + " " * (length - 2)))
        else:
            x = int(round(float(x) * self.factor))
            return super().i2m(pkt, self.fmt.format(x))

    def m2i(self, pkt: Optional[Packet], s: str) -> Union[float, str, None]:
        length = self.length_from(pkt)
        x = super().m2i(pkt, s)
        if x == "0" + " " * (length - 2):
            return "market"
        else:
            return float(x) / self.factor if x is not None else None

    def any2i(self, pkt: Optional[Packet], x: Any) -> Union[float, None]:
        if isinstance(x, (int, float)):
            return float(x)
        x = super().any2i(pkt, x)
        return float(x) / self.factor if x is not None else None


class DateField(StrFixedLenField):
    def __init__(self, name: str, default: Any):
        super().__init__(name, default, 8)

    def i2m(self, pkt: Optional[Packet], x: Any) -> str:
        return super().i2m(pkt, x.strftime("%Y%m%d") if x is not None else " " * 8)

    def m2i(self, pkt: Optional[Packet], s: str) -> Optional[datetime.date]:
        if s == " " * 8:
            return None
        return self.any2i(pkt, super().m2i(pkt, s))

    def any2i(self, pkt: Optional[Packet], x: Any) -> Optional[datetime.date]:
        if x is None or isinstance(x, datetime.date):
            return x

        if isinstance(x, bytes):
            x = x.decode("ascii")

        if x == " " * 8:
            return None

        return datetime.datetime.strptime(x, "%Y%m%d").date()


class TimeField12(StrFixedLenField):
    def __init__(self, name: str, default: Any):
        super().__init__(name, default, 12)

    def i2m(self, pkt: Optional[Packet], x: Any) -> str:
        return super().i2m(pkt, x.strftime("%H%M%S%f") if x is not None else " " * 12)

    def m2i(self, pkt: Optional[Packet], s: str) -> Optional[datetime.time]:
        if s == " " * 12:
            return None
        return self.any2i(pkt, super().m2i(pkt, s))

    def any2i(self, pkt: Optional[Packet], x: Any) -> Optional[datetime.time]:
        if x is None or isinstance(x, datetime.time):
            return x

        if isinstance(x, bytes):
            x = x.decode("ascii")

        if x == " " * 12:
            return None

        return datetime.datetime.strptime(x, "%H%M%S%f").time()


class TimeField9(StrFixedLenField):
    def __init__(self, name: str, default: Any):
        super().__init__(name, default, 9)

    def i2m(self, pkt: Optional[Packet], x: Any) -> str:
        return super().i2m(
            pkt, x.strftime("%H%M%S%f")[:9] if x is not None else " " * 9
        )

    def m2i(self, pkt: Optional[Packet], s: str) -> Optional[datetime.time]:
        if s == " " * 9:
            return None
        return self.any2i(pkt, super().m2i(pkt, s))

    def any2i(self, pkt: Optional[Packet], x: Any) -> Optional[datetime.time]:
        if x is None or isinstance(x, datetime.time):
            return x

        if isinstance(x, bytes):
            x = x.decode("ascii")

        if x == " " * 9:
            return None

        return datetime.datetime.strptime(x + "000", "%H%M%S%f").time()


################## ESP layer #################


class ESPCommon(Packet):
    name = "ESPCommon"
    fields_desc = [
        LPaddedAsciiIntFixedLenField("MessageLength", None, 5),
        StrFixedLenField("MessageType", " " * 2, 2),
        LPaddedAsciiIntFixedLenField("SeqNo", None, 8),
        CharEnumField("ResendFlag", "0", {"0": "Normal", "1": "Resent"}),
        RPaddedStrFixedLenField("ParticipantCode", None, 5),
        RPaddedStrFixedLenField("VirtualServerNo", None, 6),
        LPaddedAsciiIntFixedLenField("ARMSN", None, 8),
        LPaddedAsciiIntFixedLenField("SAMSN", None, 8),
        LPaddedAsciiIntFixedLenField("DataAreaLength", None, 5),
        LPaddedAsciiIntFixedLenField("NumberOfDataTransactions", 1, 3),
        DateField("TransmissionDate", None),
        TimeField12("TransmissionTime", None),
        StrFixedLenField("Reserved", " ", 1),
    ]

    def post_build(self, p: bytes, payload: bytes) -> bytes:
        total_len = len(p) + len(payload) - 5
        data_len = len(payload)
        p = (
            f"{total_len:5d}".encode("ascii")
            + p[5:43]
            + f"{data_len:5d}".encode("ascii")
            + p[48:]
        )
        return p + payload


class ESPBlankData(Packet):
    name = "ESPBlankData"
    fields_desc = [StrFixedLenField("Reserved", " " * 16, 16)]


class LoginRequest(ESPBlankData):
    name = "LoginRequest"


class LoginResponse(ESPBlankData):
    name = "LoginResponse"


class PreLogoutRequest(ESPBlankData):
    name = "PreLogoutRequest"


class PreLogoutResponse(ESPBlankData):
    name = "PreLogoutResponse"


class LogoutRequest(Packet):
    name = "LogoutRequest"
    fields_desc = [
        StrFixedLenField("LogoutReason", "0000", 4),
        StrFixedLenField("Reserved", " " * 12, 12),
    ]


class LogoutResponse(ESPBlankData):
    name = "LogoutResponse"


class Heartbeat(ESPBlankData):
    name = "Heartbeat"


class ResendRequest(Packet):
    name = "ResendRequest"
    fields_desc = [
        LPaddedAsciiIntFixedLenField("ResendStartSeqNo", None, 8),
        StrFixedLenField("Reserved", " " * 8, 8),
    ]


class Skip(Packet):
    name = "Skip"
    fields_desc = [
        LPaddedAsciiIntFixedLenField("SkipSeqNo", None, 8),
        StrFixedLenField("Reserved", " " * 8, 8),
    ]


class Reject(Packet):
    name = "Reject"
    fields_desc = [
        LPaddedAsciiIntFixedLenField("RejectSeqNo", None, 8),
        StrFixedLenField("RejectMessageType", " " * 2, 2),
        StrFixedLenField("RejectReasonCode", " " * 4, 4),
        StrFixedLenField("Reserved", " " * 2, 2),
    ]


################### Operations Layer ##############
# Admin Messages
class AdminCommon(Packet):
    name = "AdminCommon"
    fields_desc = [
        LPaddedAsciiIntFixedLenField("DataLength", None, 5),
        StrFixedLenField("DataCode", " " * 4, 4),
        StrFixedLenField("ExchangeCode", " ", 1),
        StrFixedLenField("MarketCode", " " * 2, 2),
        RPaddedStrFixedLenField("ParticipantCode", None, 5),
        RPaddedStrFixedLenField("VirtualServerNo", None, 6),
        StrFixedLenField("NumberOfResponseRecords", "    1", 5),
        StrFixedLenField("Reserved", " " * 17, 17),
        RPaddedStrFixedLenField("ReasonCode", None, 4),
    ]

    def post_build(self, p: bytes, payload: bytes) -> bytes:
        if self.DataLength is None:
            p = f"{len(p) + len(payload) - 5:5d}".encode("ascii") + p[5:]
        return p + payload


class AdminCommonOU(AdminCommon):  # Administrative Message (Order/Notice) (Up)
    pass


class AdminCommonOD(AdminCommon):  # Administrative Message (Order/Notice) (Down)
    pass


class AdminCommonQU(AdminCommon):  # Administrative Message (Query) (Up)
    pass


class AdminCommonQD(AdminCommon):  # Administrative Message (Query) (Down)
    pass


class AdminCommonDU(AdminCommon):  # Administrative Message (Drop Copy) (Up)
    pass


class AdminCommonDD(AdminCommon):  # Administrative Message (Drop Copy) (Down)
    pass


class MarketAdmin(Packet):
    name = "MarketAdmin"
    fields_desc = [
        CharEnumField("OperationStatus", "1", {"1": "Start", "0": "End"}),
        CharEnumField("OrderStatus", "1", {"1": "Accepting", "0": "Non-Accepting"}),
    ]


class TradingHalt(Packet):
    name = "TradingHalt"
    fields_desc = [
        StrFixedLenField("TypeCode", "A001", 4),
        StrFixedLenField("TargetRangeCode", " 1", 2),
        StrFixedLenField("TargetExchchangeCode", "1", 1),
        StrFixedLenField("TargetMarketCode", "11", 2),
        StrFixedLenField("Reserved", " " * 2, 2),
        RPaddedStrFixedLenField("TargetIssueCode", None, 12),
        TimeField9("TimeOfOccurence", None),
        TimeField9("OrderAcceptanceRestartTime", None),
        TimeField9("EffectiveTime", None),
        RPaddedStrFixedLenField("IssueCode1", None, 12),
        RPaddedStrFixedLenField("IssueCode2", None, 12),
        RPaddedStrFixedLenField("IssueCode3", None, 12),
        RPaddedStrFixedLenField("IssueCode4", None, 12),
        RPaddedStrFixedLenField("IssueCode5", None, 12),
        RPaddedStrFixedLenField("IssueCode6", None, 12),
        RPaddedStrFixedLenField("IssueCode7", None, 12),
        RPaddedStrFixedLenField("IssueCode8", None, 12),
        RPaddedStrFixedLenField("IssueCode9", None, 12),
        RPaddedStrFixedLenField("IssueCode10", None, 12),
    ]


class PriceLimitInfo(Packet):
    name = "PriceLimitInfo"
    fields_desc = [
        StrFixedLenField("TypeCode", "A031", 4),
        StrFixedLenField("TargetRangeCode", " 1", 2),
        StrFixedLenField("TargetExchangeCode", "1", 1),
        StrFixedLenField("TargetMarketCode", "11", 2),
        StrFixedLenField("Reserved", " " * 2, 2),
        RPaddedStrFixedLenField("IssueCode", None, 12),
        TimeField9("TimeOfOccurence", None),
        PriceField("BasePrice", None, 8, 4),
        PriceField("DailyUpperPriceLimit", None, 8, 4),
        PriceField("DailyLowerPriceLimit", None, 8, 4),
    ]


class FreeFormWarning(Packet):
    name = "FreeFormWarning"
    fields_desc = [
        StrFixedLenField("TypeCode", "A081", 4),
        StrFixedLenField("TargetRangeCode", " 1", 2),
        StrFixedLenField("TargetExchangeCode", "1", 1),
        StrFixedLenField("TargetMarketCode", "11", 2),
        StrFixedLenField("Reserved", " " * 2, 2),
        RPaddedStrFixedLenField("IssueCode", None, 12),
        TimeField9("TimeOfOccurence", None),
        RPaddedStrFixedLenField("Title", None, 60),
        RPaddedStrFixedLenField("Body", None, 600),
    ]


class OpStart(Packet):
    name = "OpStart"
    fields_desc = [
        LPaddedAsciiIntFixedLenField("AcceptanceSeqNo", None, 8),
        LPaddedAsciiIntFixedLenField("ExecutionSeqNo", None, 8),
        RPaddedStrFixedLenField("ProxySourceVirtualServerNo1", None, 6),
        LPaddedAsciiIntFixedLenField("ProxySourceAcceptanceSeqNo1", None, 8),
        LPaddedAsciiIntFixedLenField("ProxySourceExecutionSeqNo1", None, 8),
        RPaddedStrFixedLenField("ProxySourceVirtualServerNo2", None, 6),
        LPaddedAsciiIntFixedLenField("ProxySourceAcceptanceSeqNo2", None, 8),
        LPaddedAsciiIntFixedLenField("ProxySourceExecutionSeqNo2", None, 8),
        RPaddedStrFixedLenField("ProxySourceVirtualServerNo3", None, 6),
        LPaddedAsciiIntFixedLenField("ProxySourceAcceptanceSeqNo3", None, 8),
        LPaddedAsciiIntFixedLenField("ProxySourceExecutionSeqNo3", None, 8),
    ]


class OpStartResponse(Packet):
    name = "OpStartResponse"
    fields_desc = [
        LPaddedAsciiIntFixedLenField("AcceptanceSeqNo", None, 8),
        LPaddedAsciiIntFixedLenField("ExecutionSeqNo", None, 8),
        LPaddedAsciiIntFixedLenField("OrderEntrySeqNo", None, 8),
        RPaddedStrFixedLenField("ProxySourceVirtualServerNo1", None, 6),
        LPaddedAsciiIntFixedLenField("ProxySourceAcceptanceSeqNo1", None, 8),
        LPaddedAsciiIntFixedLenField("ProxySourceExecutionSeqNo1", None, 8),
        RPaddedStrFixedLenField("ProxySourceVirtualServerNo2", None, 6),
        LPaddedAsciiIntFixedLenField("ProxySourceAcceptanceSeqNo2", None, 8),
        LPaddedAsciiIntFixedLenField("ProxySourceExecutionSeqNo2", None, 8),
        RPaddedStrFixedLenField("ProxySourceVirtualServerNo3", None, 6),
        LPaddedAsciiIntFixedLenField("ProxySourceAcceptanceSeqNo3", None, 8),
        LPaddedAsciiIntFixedLenField("ProxySourceExecutionSeqNo3", None, 8),
    ]


class OpStartErrorResponse(OpStartResponse):
    name = "OpStartErrorResponse"


class OpEnd(Packet):
    name = "OpEnd"


class OpEndResponse(Packet):
    name = "OpEndResponse"


class OpEndErrorResponse(OpEndResponse):
    name = "OpEndErrorResponse"


class NoticeDestSetupRequest(Packet):
    name = "NoticeDestSetupRequest"
    fields_desc = [
        RPaddedStrFixedLenField("VirtualServerNo", None, 6),
        StrFixedLenField("Reserved", " " * 6, 6),
    ]


class NoticeDestSetupResponse(NoticeDestSetupRequest):
    name = "NoticeDestSetupResponse"


class NoticeDestSetupErrorResponse(NoticeDestSetupResponse):
    name = "NoticeDestSetupErrorResponse"


class NoticeDestEnqRequest(Packet):
    name = "NoticeDestEnqRequest"
    fields_desc = [
        StrFixedLenField("EnquiryTarget", "0", 1),
        RPaddedStrFixedLenField("VirtualServerNo", None, 6),
    ]


class NoticeDestEnqResponse(Packet):
    name = "NoticeDestEnqResponse"
    fields_desc = [
        StrFixedLenField("EnquiryTarget", "0", 1),
        RPaddedStrFixedLenField("VirtualServerNo1", None, 6),
        RPaddedStrFixedLenField("VirtualServerNo2", None, 6),
        RPaddedStrFixedLenField("VirtualServerNo3", None, 6),
    ]


class NoticeDestEnqErrorResponse(NoticeDestEnqResponse):
    name = "NoticeDestEnqErrorResponse"


class ProxyRequest(Packet):
    name = "ProxyRequest"
    fields_desc = [
        RPaddedStrFixedLenField("ProxySrcVirtualServerNo", None, 6),
        RPaddedStrFixedLenField("ProxyDestVirtualServerNo", None, 6),
        LPaddedAsciiIntFixedLenField("AcceptanceSeqNo", None, 8),
        LPaddedAsciiIntFixedLenField("ExecutionSeqNo", None, 8),
    ]


class ProxyResponse(ProxyRequest):
    name = "ProxyResponse"


class ProxyErrorResponse(ProxyResponse):
    name = "ProxyErrorResponse"


class ProxyAbortRequest(Packet):
    name = "ProxyAbortRequest"
    fields_desc = [
        RPaddedStrFixedLenField("ProxySrcVirtualServerNo", None, 6),
    ]


class ProxyAbortResponse(ProxyAbortRequest):
    name = "ProxyAbortResponse"


class ProxyAbortErrorResponse(ProxyAbortResponse):
    name = "ProxyAbortErrorResponse"


class ProxyStatusEnqRequest(NoticeDestEnqRequest):
    name = "ProxyStatusEnqRequest"


class ProxyStatusEnqResponse(NoticeDestEnqResponse):
    name = "ProxyStatusEnqResponse"


class ProxyStatusEnqErrorResponse(NoticeDestEnqResponse):
    name = "ProxyStatusEnqErrorResponse"


class RetransmissionRequest(Packet):
    name = "RetransmissionRequest"
    fields_desc = [
        RPaddedStrFixedLenField("VirtualServerNo", None, 6),
        StrFixedLenField("NoticeType", "0", 1),
        LPaddedAsciiIntFixedLenField("StartSeqNo", None, 8),
        LPaddedAsciiIntFixedLenField("EndSeqNo", None, 8),
    ]


class RetransmissionResponse(RetransmissionRequest):
    name = "RetransmissionResponse"


class RetransmissionErrorResponse(RetransmissionResponse):
    name = "RetransmissionErrorResponse"


class OrderSeqNoEnquiryRequest(Packet):
    name = "OrderSeqNoEnquiryRequest"
    fields_desc = [
        RPaddedStrFixedLenField("VirtualServerNo", None, 6),
    ]


class OrderSeqNoEnquiryResponse(Packet):
    name = "OrderSeqNoEnquiryResponse"
    fields_desc = [
        RPaddedStrFixedLenField("VirtualServerNo", None, 6),
        LPaddedAsciiIntFixedLenField("LastSeqNo", None, 8),
        LPaddedAsciiIntFixedLenField("LastOrderClassification", "0", 1),
    ]


class OrderSeqNoEnquiryErrorResponse(OrderSeqNoEnquiryResponse):
    name = "OrderSeqNoEnquiryErrorResponse"


class NoticeSeqNoEnquiryRequest(OrderSeqNoEnquiryRequest):
    name = "NoticeSeqNoEnquiryRequest"


class NoticeSeqNoEnquiryResponse(Packet):
    name = "NoticeSeqNoEnquiryResponse"
    fields_desc = [
        RPaddedStrFixedLenField("VirtualServerNo", None, 6),
        LPaddedAsciiIntFixedLenField("AcceptanceSeqNo", None, 8),
        LPaddedAsciiIntFixedLenField("ExecutionSeqNo", None, 8),
    ]


class NoticeSeqNoEnquiryErrorResponse(NoticeSeqNoEnquiryResponse):
    name = "NoticeSeqNoEnquiryErrorResponse"


class OrderSuspensionRequest(Packet):
    name = "OrderSuspensionRequest"
    fields_desc = [
        RPaddedStrFixedLenField("TargetVirtualServerNo", None, 6),
    ]


class OrderSuspensionResponse(OrderSuspensionRequest):
    name = "OrderSuspensionResponse"


class OrderSuspensionErrorResponse(OrderSuspensionResponse):
    name = "OrderSuspensionErrorResponse"


class OrderSuspensionReleaseRequest(Packet):
    name = "OrderSuspensionReleaseRequest"
    fields_desc = [
        RPaddedStrFixedLenField("TargetVirtualServerNo", "0" * 6, 6),
    ]


class OrderSuspensionReleaseResponse(OrderSuspensionReleaseRequest):
    name = "OrderSuspensionReleaseResponse"


class OrderSuspensionReleaseErrorResponse(OrderSuspensionReleaseResponse):
    name = "OrderSuspensionReleaseErrorResponse"


class HardLimitSetupRequest(Packet):
    name = "HardLimitSetupRequest"
    fields_desc = [
        RPaddedStrFixedLenField("VirtualServerNo", "0" * 6, 6),
        PriceField("OrderLimit", None, 15, 4),
        PriceField("CumulativeOrderLimit", None, 15, 4),
        LPaddedAsciiIntFixedLenField("CumulativeOrderInterval", None, 5),
        PriceField("CumulativeExecutionLimit", None, 15, 4),
        LPaddedAsciiIntFixedLenField("CumulativeExectutionInterval", None, 5),
    ]


class HardLimitSetupResponse(HardLimitSetupRequest):
    name = "HardLimitSetupResponse"


class HardLimitSetupErrorResponse(HardLimitSetupResponse):
    name = "HardLimitSetupErrorResponse"


class HardLimitEnquiryRequest(Packet):
    name = "HardLimitEnquiryRequest"
    fields_desc = [
        RPaddedStrFixedLenField("TargetVirtualServerNo", "0" * 6, 6),
    ]


class HardLimitEnquiryResponse(Packet):
    name = "HardLimitEnquiryRequest"
    fields_desc = [
        RPaddedStrFixedLenField("TargetVirtualServerNo", None, 6),
        CharEnumField(
            "SuspensionStatus", " ", {"1": "Suspending", "0": "NotSuspending"}
        ),
        PriceField("OrderLimit", None, 15, 4),
        PriceField("CumulativeOrderLimit", None, 15, 4),
        LPaddedAsciiIntFixedLenField("CumulativeOrderInterval", None, 5),
        PriceField("CumulativeOrderLast", None, 15, 4),
        TimeField9("CumulativeOrderStartTime", None),
        LPaddedAsciiIntFixedLenField("CumulativeOrderFirstSeqNo", None, 8),
        LPaddedAsciiIntFixedLenField("CumulativeOrderLastSeqNo", None, 8),
        PriceField("CumulativeExecutionLimit", None, 15, 4),
        LPaddedAsciiIntFixedLenField("CumulativeExectutionInterval", None, 5),
        PriceField("CumulativeExecutionLast", None, 15, 4),
        TimeField9("CumulativeExecutionStartTime", None),
        LPaddedAsciiIntFixedLenField("CumulativeExecutionFirstSeqNo", None, 8),
        LPaddedAsciiIntFixedLenField("CumulativeExecutionLastSeqNo", None, 8),
    ]


class HardLimitEnquiryErrorResponse(HardLimitEnquiryResponse):
    name = "HardLimitEnquiryErrorResponse"


class SystemError(Packet):
    name = "SystemError"
    fields_desc = [
        StrFixedLenField("ReceivedData", " " * 200, 200),  # actually up to 2000 in spec
    ]


# Order Entry Messages
class OrderCommon(Packet):
    name = "OrderCommon"
    fields_desc = [
        LPaddedAsciiIntFixedLenField("DataLen", None, 5),
        RPaddedStrFixedLenField("DataCode", None, 4),
        RPaddedStrFixedLenField("ExchangeCode", None, 1),
        RPaddedStrFixedLenField("MarketCode", None, 2),
        RPaddedStrFixedLenField("ParticipantCode", None, 5),
        RPaddedStrFixedLenField("VirtualServerNo", None, 6),
        StrFixedLenField("Reserved", " " * 6, 6),
        LPaddedAsciiIntFixedLenField("OrderEntrySeqNo", None, 8),
        StrFixedLenField("Reserved2", " " * 5, 5),
    ]

    def post_build(self, p: bytes, payload: bytes) -> bytes:
        if self.DataLen is None:
            p = f"{len(p) + len(payload) - 5:5d}".encode("ascii") + p[5:]
        return p + payload


class OrderCommonO(OrderCommon):  # operation message (Order/Notice)
    pass


class OrderCommonQ(OrderCommon):  # operation message (Query)
    pass


class OrderCommonD(OrderCommon):  # operation message (Drop Copy)
    pass


class NewOrder(Packet):
    name = "NewOrder"
    fields_desc = [
        StrFixedLenField("Reserved", " " * 2, 2),
        RPaddedStrFixedLenField("IssueCode", None, 12),
        CharEnumField("Side", "3", RENUMS["Side"]),
        CharEnumField("ExecutionCondition", "0", RENUMS["ExecCond"]),
        PriceField("OrderPrice", None, 8, 4),
        LPaddedAsciiIntFixedLenField("OrderQuantity", None, 13),
        CharEnumField("ProprietaryBrokerage", "0", RENUMS["PropBrokerageClass"]),
        CharEnumField("CashMarginCode", "0", RENUMS["CashMarginCode"]),
        CharEnumField("ShortSellFlag", "0", RENUMS["ShortSellFlag"]),
        CharEnumField("StabilizationArbitrageCode", "0", RENUMS["StabArbCode"]),
        CharEnumField("OrderAttribute", "1", RENUMS["OrderAttrCode"]),
        CharEnumField("SupportMember", "0", RENUMS["SuppMemberClass"]),
        RPaddedStrFixedLenField("InternalProcessing", None, 20),
        RPaddedStrFixedLenField("Optional", "0000", 4),
        StrFixedLenField("Reserved", " " * 19, 19),
    ]


class ModificationOrder(Packet):
    name = "ModificationOrder"
    fields_desc = [
        StrFixedLenField("Reserved", " " * 2, 2),
        RPaddedStrFixedLenField("IssueCode", None, 12),
        LPaddedAsciiIntFixedLenField("OrderAcceptanceNo", None, 14),
        RPaddedStrFixedLenField("InternalProcessing", None, 20),
        CharEnumField("ExecutionCondition", " ", RENUMS["ExecCond"]),
        PriceField("OrderPrice", None, 8, 4),
        LPaddedAsciiIntFixedLenField("ReductionQuantity", None, 13),
        RPaddedStrFixedLenField("Optional", None, 4),
    ]


class ModificationOrderByAcceptanceNo(ModificationOrder):
    pass


class ModificationOrderByInternal(ModificationOrder):
    pass


class CancelOrder(Packet):
    name = "CancelOrder"
    fields_desc = [
        StrFixedLenField("Reserved", " " * 2, 2),
        RPaddedStrFixedLenField("IssueCode", None, 12),
        LPaddedAsciiIntFixedLenField("OrderAcceptanceNo", None, 14),
        RPaddedStrFixedLenField("InternalProcessing", None, 20),
    ]


class CancelOrderByAcceptanceNo(CancelOrder):
    pass


class CancelOrderByInternal(CancelOrder):
    pass


# Notice Messages
class NoticeCommon(Packet):
    name = "NoticeCommon"
    fields_desc = [
        LPaddedAsciiIntFixedLenField("DataLength", None, 5),
        StrFixedLenField("DataCode", " " * 4, 4),
        StrFixedLenField("ExchangeCode", " " * 4, 1),
        StrFixedLenField("MarketCode", " " * 4, 2),
        RPaddedStrFixedLenField("ParticipantCode", None, 5),
        RPaddedStrFixedLenField("SourceVirtualServerNo", None, 6),
        RPaddedStrFixedLenField("DestinationVirtualServerNo", None, 6),
        LPaddedAsciiIntFixedLenField("OrderEntrySeqNo", None, 8),
        LPaddedAsciiIntFixedLenField("NoticeSeqNo", None, 8),
        StrFixedLenField("ReasonCode", " " * 4, 4),
        CharEnumField(
            "Retransmission Flag", "0", {"0": "Normal", "1": "Retransmission"}
        ),
        TimeField12("Time", None),
        StrFixedLenField("Reserved", " " * 2, 2),
    ]

    def post_build(self, p: bytes, payload: bytes) -> bytes:
        p = f"{len(p) + len(payload) - 5:5d}".encode("ascii") + p[5:]
        return p + payload


class NoticeCommonO(NoticeCommon):  # Order/Notice
    pass


class NoticeCommonQ(NoticeCommon):  # Query
    pass


class NoticeCommonD(NoticeCommon):  # Drop Copy
    pass


class NewOrderAcceptanceNotice(Packet):
    name = "NewOrderAcceptanceNotice"
    fields_desc = [
        StrFixedLenField("Reserved", " " * 2, 2),
        RPaddedStrFixedLenField("IssueCode", None, 12),
        CharEnumField("Side", "3", RENUMS["Side"]),
        CharEnumField("ExecutionCondition", "0", RENUMS["ExecCond"]),
        PriceField("OrderPrice", None, 8, 4),
        LPaddedAsciiIntFixedLenField("OrderQuantity", None, 13),
        CharEnumField("PropriataryBrokerage", "0", RENUMS["PropBrokerageClass"]),
        CharEnumField("CashMarginCode", "0", RENUMS["CashMarginCode"]),
        CharEnumField("ShortSellFlag", "0", RENUMS["ShortSellFlag"]),
        CharEnumField("StabilizationArbitrageCode", "0", RENUMS["StabArbCode"]),
        CharEnumField("OrderAttribute", "1", RENUMS["OrderAttrCode"]),
        CharEnumField("SupportMember", "0", RENUMS["SuppMemberClass"]),
        RPaddedStrFixedLenField("InternalProcessing", None, 20),
        RPaddedStrFixedLenField("Optional", "0000", 4),
        RPaddedStrFixedLenField("OrderAcceptanceNo", None, 14),
        StrFixedLenField("Reserved2", " " * 19, 19),
    ]


class NewOrderAcceptanceError(NewOrderAcceptanceNotice):
    name = "NewOrderAcceptanceError"


class NewOrderRegistrationError(NewOrderAcceptanceNotice):
    name = "NewOrderRegistrationError"


class ModificationOrderAcceptanceNotice(Packet):
    name = "ModificationOrderAcceptanceNotice"
    fields_desc = [
        StrFixedLenField("Reserved", " " * 2, 2),
        RPaddedStrFixedLenField("IssueCode", None, 12),
        RPaddedStrFixedLenField("OrderAcceptanceNo", None, 14),
        RPaddedStrFixedLenField("InternalProcessing", None, 20),
        CharEnumField("ExecutionCondition", "0", RENUMS["ExecCond"]),
        PriceField("OrderPrice", None, 8, 4),
        LPaddedAsciiIntFixedLenField("ReductionQuantity", None, 13),
        RPaddedStrFixedLenField("Optional", None, 4),
    ]


class ModificationOrderAcceptanceError(ModificationOrderAcceptanceNotice):
    name = "ModificationOrderAcceptanceError"


class ModificationOrderRegistrationError(ModificationOrderAcceptanceNotice):
    name = "ModificationOrderRegistrationError"


class ModificationOrderResultNotice(Packet):
    name = "ModResultNotice"
    fields_desc = [
        StrFixedLenField("Reserved", " " * 2, 2),
        RPaddedStrFixedLenField("IssueCode", None, 12),
        RPaddedStrFixedLenField("OrderAcceptanceNo", None, 14),
        RPaddedStrFixedLenField("InternalProcessing", None, 20),
        RPaddedStrFixedLenField("Optional", None, 4),
        CharEnumField("ExecutionCondition", "0", RENUMS["ExecCond"]),
        PriceField("OrderPrice", None, 8, 4),
        LPaddedAsciiIntFixedLenField("OrderQuantity", None, 13),
        RPaddedStrFixedLenField("Optional2", None, 4),
        LPaddedAsciiIntFixedLenField("PartiallyExecutedQuantity", None, 13),
        LPaddedAsciiIntFixedLenField("ReductionCompletedQuantity", None, 13),
        LPaddedAsciiIntFixedLenField("NoticeNo", None, 13),
    ]


class CancelOrderAcceptanceNotice(Packet):
    name = "CancelOrderAcceptanceNotice"
    fields_desc = [
        StrFixedLenField("Reserved", " " * 2, 2),
        RPaddedStrFixedLenField("IssueCode", None, 12),
        RPaddedStrFixedLenField("OrderAcceptanceNo", None, 14),
        RPaddedStrFixedLenField("InternalProcessing", None, 20),
    ]


class CancelOrderAcceptanceError(CancelOrderAcceptanceNotice):
    name = "CancelOrderAcceptanceError"


class CancelOrderRegistrationError(CancelOrderAcceptanceNotice):
    name = "CancelOrderRegistrationError"


class CancelOrderResultNotice(Packet):
    name = "CancelOrderResultNotice"
    fields_desc = [
        StrFixedLenField("Reserved", "  ", 2),
        RPaddedStrFixedLenField("IssueCode", None, 12),
        RPaddedStrFixedLenField("OrderAcceptanceNo", None, 14),
        RPaddedStrFixedLenField("InternalProcessing", None, 20),
        RPaddedStrFixedLenField("Optional", "0000", 4),
        LPaddedAsciiIntFixedLenField("PartiallyExecutedQuantity", None, 13),
        LPaddedAsciiIntFixedLenField("ReductionCompletedQuantity", None, 13),
        LPaddedAsciiIntFixedLenField("NoticeNo", None, 13),
    ]


class ExecutionCompletionNotice(Packet):
    name = "ExecutionCompletionNotice"
    fields_desc = [
        StrFixedLenField("Reserved", "  ", 2),
        RPaddedStrFixedLenField("IssueCode", None, 12),
        CharEnumField("Side", " ", RENUMS["Side"]),
        CharEnumField("ExecutionCondition", "0", RENUMS["ExecCond"]),
        PriceField("ExecutionPrice", None, 8, 4),
        LPaddedAsciiIntFixedLenField("ExecutedQuantity", None, 13),
        CharEnumField("PropriataryBrokerage", "0", RENUMS["PropBrokerageClass"]),
        CharEnumField("CashMarginCode", "0", RENUMS["CashMarginCode"]),
        CharEnumField("ShortSellFlag", "0", RENUMS["ShortSellFlag"]),
        CharEnumField("StabilizationArbitrageCode", "0", RENUMS["StabArbCode"]),
        CharEnumField("OrderAttribute", "1", RENUMS["OrderAttrCode"]),
        CharEnumField("SupportMember", "0", RENUMS["SuppMemberClass"]),
        RPaddedStrFixedLenField("InternalProcessing", None, 20),
        RPaddedStrFixedLenField("Optional", "0000", 4),
        StrFixedLenField("Reserved2", " " * 19, 19),
        LPaddedAsciiIntFixedLenField("ValidOrderQuantity", None, 13),
        CharEnumField("CrossFlag", " ", {"0": "0", "8": "8"}),
        CharEnumField(
            "PriceFlag", " ", {"1": "Fixed", "9": "LimitAllocation", "0": "Other"}
        ),
        LPaddedAsciiIntFixedLenField("ExecutionNoticeNo", None, 8),
        RPaddedStrFixedLenField("OrderAcceptanceNo", None, 14),
        LPaddedAsciiIntFixedLenField("NoticeNo", None, 13),
    ]


class InvalidationResultNotice(Packet):
    name = "InvalidationResultNotice"
    fields_desc = [
        StrFixedLenField("Reserved", "  ", 2),
        RPaddedStrFixedLenField("IssueCode", None, 12),
        CharEnumField("Side", " ", RENUMS["Side"]),
        CharEnumField("ExecutionCondition", "0", RENUMS["ExecCond"]),
        PriceField("ExecutionPrice", None, 8, 4),
        LPaddedAsciiIntFixedLenField("ExecutedQuantity", None, 13),
        CharEnumField("PropriataryBrokerage", "0", RENUMS["PropBrokerageClass"]),
        CharEnumField("CashMarginCode", "0", RENUMS["CashMarginCode"]),
        CharEnumField("ShortSellFlag", "0", RENUMS["ShortSellFlag"]),
        CharEnumField("StabilizationArbitrageCode", "0", RENUMS["StabArbCode"]),
        CharEnumField("OrderAttribute", "1", RENUMS["OrderAttrCode"]),
        CharEnumField("SupportMember", "0", RENUMS["SuppMemberClass"]),
        RPaddedStrFixedLenField("InternalProcessing", None, 20),
        RPaddedStrFixedLenField("Optional", "0000", 4),
        RPaddedStrFixedLenField("OrderAcceptanceNo", None, 14),
        StrFixedLenField("Reserved", " " * 19, 19),
        LPaddedAsciiIntFixedLenField("PartiallyExecutedQuantity", None, 13),
        CharEnumField("LimitFlag", " ", {"9": "LimitAllocation", "0": "Other"}),
        LPaddedAsciiIntFixedLenField("NoticeNo", None, 13),
    ]


class AcceptanceOutputCompletionNotice(Packet):
    name = "AcceptanceOutputCompletionNotice"
    fields_desc = [
        StrFixedLenField("SessionType", "1", 1),
    ]


class ExecutionOutputCompletionNotice(AcceptanceOutputCompletionNotice):
    name = "ExecutionOutputCompletionNotice"


# Layer bindings
bind_layers(ESPCommon, LoginRequest, MessageType="01")
bind_layers(ESPCommon, LoginResponse, MessageType="11")
bind_layers(ESPCommon, PreLogoutRequest, MessageType="02")
bind_layers(ESPCommon, PreLogoutResponse, MessageType="12")
bind_layers(ESPCommon, LogoutRequest, MessageType="13")
bind_layers(ESPCommon, LogoutRequest, MessageType="03")
bind_layers(ESPCommon, LogoutResponse, MessageType="14")
bind_layers(ESPCommon, LogoutResponse, MessageType="04")
bind_layers(ESPCommon, Heartbeat, MessageType="15")
bind_layers(ESPCommon, Heartbeat, MessageType="05")
bind_layers(ESPCommon, ResendRequest, MessageType="16")
bind_layers(ESPCommon, ResendRequest, MessageType="06")
bind_layers(ESPCommon, Skip, MessageType="17")
bind_layers(ESPCommon, Skip, MessageType="07")
bind_layers(ESPCommon, Reject, MessageType="18")
bind_layers(ESPCommon, Reject, MessageType="08")
bind_layers(ESPCommon, OrderCommonO, MessageType="40")
bind_layers(ESPCommon, OrderCommonQ, MessageType="41")
bind_layers(ESPCommon, OrderCommonD, MessageType="42")
bind_layers(ESPCommon, NoticeCommonO, MessageType="50")
bind_layers(ESPCommon, NoticeCommonQ, MessageType="51")
bind_layers(ESPCommon, NoticeCommonD, MessageType="52")
bind_layers(ESPCommon, AdminCommonOU, MessageType="80")
bind_layers(ESPCommon, AdminCommonOD, MessageType="90")
bind_layers(ESPCommon, AdminCommonQU, MessageType="81")
bind_layers(ESPCommon, AdminCommonQD, MessageType="91")
bind_layers(ESPCommon, AdminCommonDU, MessageType="82")
bind_layers(ESPCommon, AdminCommonDD, MessageType="92")

# Requests
bind_layers(OrderCommonO, NewOrder, DataCode="1111")
bind_layers(OrderCommonO, ModificationOrderByAcceptanceNo, DataCode="5131")
bind_layers(OrderCommonO, ModificationOrderByInternal, DataCode="9132")
bind_layers(OrderCommonO, CancelOrderByAcceptanceNo, DataCode="3121")
bind_layers(OrderCommonO, CancelOrderByInternal, DataCode="7122")

# Notices
bind_layers(NoticeCommonO, NewOrderAcceptanceNotice, DataCode="A111")
bind_layers(NoticeCommonO, ModificationOrderAcceptanceNotice, DataCode="B131")
bind_layers(NoticeCommonO, CancelOrderAcceptanceNotice, DataCode="B121")
bind_layers(NoticeCommonO, NewOrderAcceptanceError, DataCode="C119")
bind_layers(NoticeCommonO, ModificationOrderAcceptanceError, DataCode="D139")
bind_layers(NoticeCommonO, CancelOrderAcceptanceError, DataCode="D129")
bind_layers(NoticeCommonO, AcceptanceOutputCompletionNotice, DataCode="A191")
bind_layers(NoticeCommonO, ExecutionCompletionNotice, DataCode="J211")
bind_layers(NoticeCommonO, ModificationOrderResultNotice, DataCode="F231")
bind_layers(NoticeCommonO, CancelOrderResultNotice, DataCode="F221")
bind_layers(NoticeCommonO, NewOrderRegistrationError, DataCode="K219")
bind_layers(NoticeCommonO, ModificationOrderRegistrationError, DataCode="K239")
bind_layers(NoticeCommonO, CancelOrderRegistrationError, DataCode="K229")
bind_layers(NoticeCommonO, InvalidationResultNotice, DataCode="K241")
bind_layers(NoticeCommonO, ExecutionOutputCompletionNotice, DataCode="J291")

# Admin
bind_layers(AdminCommonOD, MarketAdmin, DataCode="T111")
bind_layers(AdminCommonOD, TradingHalt, DataCode="T311")
bind_layers(AdminCommonOD, PriceLimitInfo, DataCode="T321")
bind_layers(AdminCommonOD, FreeFormWarning, DataCode="T331")

bind_layers(AdminCommonOU, OpStart, DataCode="6211")
bind_layers(AdminCommonOU, OpEnd, DataCode="6221")
bind_layers(AdminCommonOU, RetransmissionRequest, DataCode="6231")
bind_layers(AdminCommonOU, ProxyRequest, DataCode="6241")
bind_layers(AdminCommonOU, ProxyAbortRequest, DataCode="6251")
bind_layers(AdminCommonOU, ProxyStatusEnqRequest, DataCode="6261")
bind_layers(AdminCommonOU, OrderSeqNoEnquiryRequest, DataCode="6271")
bind_layers(AdminCommonOU, NoticeSeqNoEnquiryRequest, DataCode="6281")
bind_layers(AdminCommonOU, NoticeDestSetupRequest, DataCode="6291")
bind_layers(AdminCommonOU, NoticeDestEnqRequest, DataCode="62A1")

bind_layers(AdminCommonOD, OpStartResponse, DataCode="T211")
bind_layers(AdminCommonOD, OpStartErrorResponse, DataCode="T219")
bind_layers(AdminCommonOD, OpEndResponse, DataCode="T221")
bind_layers(AdminCommonOD, OpEndErrorResponse, DataCode="T229")
bind_layers(AdminCommonOD, RetransmissionResponse, DataCode="T231")
bind_layers(AdminCommonOD, RetransmissionErrorResponse, DataCode="T239")
bind_layers(AdminCommonOD, ProxyResponse, DataCode="T241")
bind_layers(AdminCommonOD, ProxyErrorResponse, DataCode="T249")
bind_layers(AdminCommonOD, ProxyAbortResponse, DataCode="T251")
bind_layers(AdminCommonOD, ProxyAbortErrorResponse, DataCode="T259")
bind_layers(AdminCommonOD, ProxyStatusEnqResponse, DataCode="T261")
bind_layers(AdminCommonOD, ProxyStatusEnqErrorResponse, DataCode="T269")
bind_layers(AdminCommonOD, OrderSeqNoEnquiryResponse, DataCode="T271")
bind_layers(AdminCommonOD, OrderSeqNoEnquiryErrorResponse, DataCode="T279")
bind_layers(AdminCommonOD, NoticeSeqNoEnquiryResponse, DataCode="T281")
bind_layers(AdminCommonOD, NoticeSeqNoEnquiryErrorResponse, DataCode="T289")
bind_layers(AdminCommonOD, NoticeDestSetupResponse, DataCode="T291")
bind_layers(AdminCommonOD, NoticeDestSetupErrorResponse, DataCode="T299")
bind_layers(AdminCommonOD, NoticeDestEnqResponse, DataCode="T2A1")
bind_layers(AdminCommonOD, NoticeDestEnqErrorResponse, DataCode="T2A9")
bind_layers(AdminCommonOD, OrderSuspensionRequest, DataCode="62B1")
bind_layers(AdminCommonOD, OrderSuspensionErrorResponse, DataCode="T2B1")
bind_layers(AdminCommonOD, OrderSuspensionReleaseRequest, DataCode="62C1")
bind_layers(AdminCommonOD, OrderSuspensionReleaseErrorResponse, DataCode="T2C1")
bind_layers(AdminCommonOD, HardLimitSetupRequest, DataCode="62D1")
bind_layers(AdminCommonOD, HardLimitSetupErrorResponse, DataCode="T2D1")
bind_layers(AdminCommonOD, HardLimitEnquiryRequest, DataCode="62E1")
bind_layers(AdminCommonOD, HardLimitEnquiryErrorResponse, DataCode="T2E1")
bind_layers(AdminCommonOD, SystemError, DataCode="T999")
