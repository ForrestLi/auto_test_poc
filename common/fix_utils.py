from typing import Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

import overrides

from common.test_utils import GenericChecker
from fix_msg import MsgType as FixMessageType, Field as FixTag


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
        self.fix_client = kwargs["fix_client"]
        self.exchange_sim = kwargs["exchange_sim"]
        self.expected_seq_num = 1

    def _extract_field(self, msg: Dict[str, str], tag: str, default: Any = None) -> Any:
        """Extract a field from a FIX message."""
        return msg.get(tag, default)

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
    def newOrder(self, order, **kwargs):
        """Send a new order (NewOrderSingle) with support for short selling."""
        if not kwargs.get("dk", False):
            fix_msg = self._build_new_order_single(**kwargs)
            self.fix_client.sendMsg(fix_msg)
            self.expected_seq_num += 1

        super().newOrder(order, **kwargs)
        return self

    @overrides
    def ordered(self, order, **kwargs):
        """Validate order acceptance (ExecutionReport with ExecType=NEW)."""
        msg = self.fix_client.receiveMsg()

        side = kwargs.get("side", order.side)
        expected_fields = {
            FixTag.CL_ORD_ID: kwargs.get("clOrdID", order.clOrdID),
            FixTag.ORDER_ID: kwargs.get("orderID", order.orderID),
            FixTag.SYMBOL: kwargs.get("symbol", order.symbol),
            FixTag.SIDE: self.SIDE_MAPPING.get(side),
            FixTag.ORDER_QTY: str(kwargs.get("orderQty", order.orderQty)),
            FixTag.PRICE: (
                str(kwargs.get("price", order.price))
                if kwargs.get("price", order.price)
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
    def reject(self, order, **kwargs):
        """Validate order rejection (ExecutionReport with ExecType=REJECT)."""
        msg = self.fix_client.receiveMsg()

        side = kwargs.get("side", order.side)
        expected_fields = {
            FixTag.CL_ORD_ID: kwargs.get("clOrdID", order.clOrdID),
            FixTag.ORDER_ID: kwargs.get("orderID", order.orderID),
            FixTag.SYMBOL: kwargs.get("symbol", order.symbol),
            FixTag.SIDE: self.SIDE_MAPPING.get(side),
            FixTag.ORDER_QTY: str(kwargs.get("orderQty", order.orderQty)),
            FixTag.PRICE: (
                str(kwargs.get("price", order.price))
                if kwargs.get("price", order.price)
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
    def fill(self, order, **kwargs):
        """Validate order fill (ExecutionReport with ExecType=FILL)."""
        orderID = kwargs.get("orderID", order.orderID)
        # can also not use exchange_sim, but use the opposite side, then record/replay
        self.exchange_sim.fill(orderID, kwargs["execQty"], kwargs["execPrice"])

        msg = self.fix_client.receiveMsg()

        side = kwargs.get("side", order.side)
        expected_fields = {
            FixTag.CL_ORD_ID: kwargs.get("clOrdID", order.clOrdID),
            FixTag.ORDER_ID: orderID,
            FixTag.SYMBOL: kwargs.get("symbol", order.symbol),
            FixTag.SIDE: self.SIDE_MAPPING.get(side),
            FixTag.ORDER_QTY: str(kwargs.get("orderQty", order.orderQty)),
            FixTag.LAST_SHARES: str(kwargs.get("execQty")),
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
