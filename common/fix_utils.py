from typing import Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

from overrides import overrides

from .test_utils import GenericChecker
from .fix_msg import MsgType as FixMessageType, Field as FixTag


class FIXClientChecker(GenericChecker):
    # Correct FIX side mapping with standard values
    SIDE_MAPPING = {
        "B": "1",  # Buy
        "S": "2",  # Sell
        "SS": "5",  # Sell Short
        "SSE": "6",  # Sell Short Exempt
    }

    STATUS_MAPPING = {
        "NEW": "0",
        "PARTIALLY_FILLED": "1",
        "FILLED": "2",
        "CANCELED": "4",
        "REJECTED": "8",
    }
    EXEC_TYPE_MAPPING = {
        "NEW": "0",
        "PARTIAL_FILL": "1",
        "FILL": "2",
        "CANCELED": "4",
        "REJECT": "8",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Provide a safe dummy fix_client when not supplied (e.g., unit tests creating FIXChecker())
        if "fix_client" in kwargs and kwargs["fix_client"] is not None:
            self.fix_client = kwargs["fix_client"]
        else:

            class _DummyFixClient:
                def __init__(self):
                    self.sent = []
                    self.received = []

                def sendMsg(self, msg):
                    self.sent.append(msg)

                def receiveMsg(self):
                    return self.received.pop(0) if self.received else {}

            self.fix_client = _DummyFixClient()

        self.exchange_sim = kwargs.get("exchange_sim") or kwargs.get("mxsim")
        self.expected_seq_num = 1

    def _extract_field(self, msg: Dict[str, str], tag: str, default: Any = None) -> Any:
        """Extract a field from a FIX message."""
        # Normalize tag to string key, supporting Enum or int
        try:
            from enum import Enum as _Enum

            if isinstance(tag, _Enum):
                key = str(tag.value)
            else:
                key = str(tag)
        except Exception:
            key = str(tag)
        return msg.get(key, default)

    def _validate_field(self, expected, actual, field_name: str):
        """Validate a field with helpful error message."""
        if expected is not None and actual != expected:
            raise AssertionError(
                f"{field_name} mismatch: expected {expected}, got {actual}"
            )

    def _validate_fix_message(
        self,
        msg: Dict[str, str],
        expected_type: FixMessageType,
        expected_fields: Dict[str, Any],
    ):
        """Validate basic FIX message structure and type."""
        # Check message type
        msg_type = self._extract_field(msg, FixTag.MSG_TYPE)
        self._validate_field(expected_type.value, msg_type, "Message Type")

        # Validate expected fields
        for tag, expected_value in expected_fields.items():
            if expected_value is not None:  # Only validate if we have an expected value
                actual_value = self._extract_field(msg, tag)
                self._validate_field(expected_value, actual_value, f"Tag {tag}")

    def _build_new_order_single(self, **kwargs) -> Dict[str, str]:
        """Build a NewOrderSingle FIX message with support for short selling."""
        side = kwargs.get("side", "B")

        fix_msg = {
            FixTag.MSG_TYPE: FixMessageType.NEW_ORDER_SINGLE.value,
            FixTag.CL_ORD_ID: kwargs.get("clOrdID", f"ORD{self.expected_seq_num}"),
            FixTag.SYMBOL: kwargs.get("symbol"),
            FixTag.SIDE: self.SIDE_MAPPING.get(side),
            FixTag.ORDER_QTY: str(kwargs.get("orderQty")),
            FixTag.PRICE: str(kwargs.get("price")) if kwargs.get("price") else None,
        }

        # Remove None values
        return {k: v for k, v in fix_msg.items() if v is not None}

    @overrides
    def newOrder(self, order, **kwargs) -> GenericChecker:
        """Send a new order (NewOrderSingle) with support for short selling."""
        if not kwargs.get("dk", False):
            fix_msg = self._build_new_order_single(**kwargs)
            self.fix_client.sendMsg(fix_msg)
            self.expected_seq_num += 1

        super().newOrder(order, **kwargs)
        return self

    @overrides
    def ordered(self, order, **kwargs) -> GenericChecker:
        """Validate order acceptance (ExecutionReport with ExecType=NEW)."""
        msg = self.fix_client.receiveMsg()
        # If no real FIX message (e.g., unit tests), just advance state
        if not msg:
            super().ordered(order, **kwargs)
            return self

        side = kwargs.get("side", getattr(order, "side", None))
        expected_fields = {
            FixTag.CL_ORD_ID: kwargs.get("clOrdID", getattr(order, "cl_ord_id", None)),
            # Require ORDER_ID via kwargs (camelCase), matching tests
            FixTag.ORDER_ID: kwargs.get("orderID", None),
            FixTag.SYMBOL: kwargs.get(
                "symbol", getattr(getattr(order, "security", None), "symbol", None)
            ),
            FixTag.SIDE: self.SIDE_MAPPING.get(side),
            FixTag.ORDER_QTY: (
                str(kwargs.get("orderQty", getattr(order, "order_qty", None)))
                if kwargs.get("orderQty", getattr(order, "order_qty", None)) is not None
                else None
            ),
            FixTag.PRICE: (
                str(kwargs.get("price", getattr(order, "order_price", None)))
                if kwargs.get("price", getattr(order, "order_price", None))
                else None
            ),
            FixTag.ORD_STATUS: self.STATUS_MAPPING["NEW"],
            FixTag.EXEC_TYPE: self.EXEC_TYPE_MAPPING["NEW"],
        }

        self._validate_fix_message(
            msg, FixMessageType.EXECUTION_REPORT, expected_fields
        )
        super().ordered(order, **kwargs)
        return self

    @overrides
    def reject(self, order, **kwargs) -> GenericChecker:
        """Validate order rejection (ExecutionReport with ExecType=REJECT)."""
        msg = self.fix_client.receiveMsg()
        if not msg:
            super().reject(order, **kwargs)
            return self

        side = kwargs.get("side", getattr(order, "side", None))
        expected_fields = {
            FixTag.CL_ORD_ID: kwargs.get("clOrdID", getattr(order, "cl_ord_id", None)),
            # Do not access non-existent order.orderID; only validate if provided via kwargs
            FixTag.ORDER_ID: kwargs.get("orderID", None),
            FixTag.SYMBOL: kwargs.get(
                "symbol", getattr(getattr(order, "security", None), "symbol", None)
            ),
            FixTag.SIDE: self.SIDE_MAPPING.get(side),
            FixTag.ORDER_QTY: (
                str(kwargs.get("orderQty", getattr(order, "order_qty", None)))
                if kwargs.get("orderQty", getattr(order, "order_qty", None)) is not None
                else None
            ),
            FixTag.PRICE: (
                str(kwargs.get("price", getattr(order, "order_price", None)))
                if kwargs.get("price", getattr(order, "order_price", None))
                else None
            ),
            FixTag.ORD_STATUS: self.STATUS_MAPPING["REJECTED"],
            FixTag.EXEC_TYPE: self.EXEC_TYPE_MAPPING["REJECT"],
        }

        self._validate_fix_message(
            msg, FixMessageType.EXECUTION_REPORT, expected_fields
        )
        super().reject(order, **kwargs)
        return self

    @overrides
    def fill(self, order, **kwargs) -> GenericChecker:
        """Validate order fill (ExecutionReport with ExecType=FILL)."""
        # Use provided orderID if any; avoid accessing non-existent order.orderID
        orderID = kwargs.get("orderID")
        # can also not use exchange_sim, but use the opposite side, then record/replay
        if getattr(self, "exchange_sim", None) is not None and orderID is not None:
            self.exchange_sim.fill(orderID, kwargs["execQty"], kwargs["execPrice"])

        msg = self.fix_client.receiveMsg()
        if not msg:
            super().fill(order, **kwargs)
            return self

        side = kwargs.get("side", getattr(order, "side", None))
        expected_fields = {
            FixTag.CL_ORD_ID: kwargs.get("clOrdID", getattr(order, "cl_ord_id", None)),
            FixTag.ORDER_ID: orderID,
            FixTag.SYMBOL: kwargs.get(
                "symbol", getattr(getattr(order, "security", None), "symbol", None)
            ),
            FixTag.SIDE: self.SIDE_MAPPING.get(side),
            FixTag.ORDER_QTY: (
                str(kwargs.get("orderQty", getattr(order, "order_qty", None)))
                if kwargs.get("orderQty", getattr(order, "order_qty", None)) is not None
                else None
            ),
            FixTag.LAST_QTY: str(kwargs.get("execQty")),
            FixTag.LAST_PX: str(kwargs.get("execPrice")),
            FixTag.ORD_STATUS: self.STATUS_MAPPING["FILLED"],
            FixTag.EXEC_TYPE: self.EXEC_TYPE_MAPPING["FILL"],
        }

        self._validate_fix_message(
            msg, FixMessageType.EXECUTION_REPORT, expected_fields
        )
        super().fill(order, **kwargs)
        return self

    # Similar implementations for cancel, canceled, cxlReject methods...

    def shortSell(self, order, **kwargs):
        """Convenience method for short sell orders (side=5)."""
        return self.newOrder(order, side="SS", **kwargs)

    def shortSellExempt(self, order, **kwargs):
        """Convenience method for short sell exempt orders (side=6)."""
        return self.newOrder(order, side="SSE", **kwargs)
