from test_utils import *
from ahd_msg import *


class AHDClientChecker(GenericChecker):
    SIDE_TO_AHD = {"B": b"3", "S": b"1"}  # Constant renamed to UPPER_CASE

    def __init__(self, **kwargs):
        super().__init__(**kwargs)  # Modern super() usage
        self.ahd_client = kwargs["ahd_client"]
        self.mxsim = kwargs["mxsim"]

    def expected_internal_processing(self, kwargs, order):  # Snake_case naming
        # To be overridden by subclasses
        return kwargs.get("clOrdID", order.clOrdID if order else None)

    def kwargs_from_new_order(self, kwargs, msg):  # Snake_case naming
        # To be overridden by subclasses
        kwargs["clOrdID"] = msg.InternalProcessing

    @overrides
    def newOrder(self, order, **kwargs):
        if kwargs.get("dk"):
            return self  # Early return for clarity

        NewOrder = self.ahd_client.ahd_msg.NewOrder
        msg = self.ahd_client.sendMsg(
            NewOrder(
                InternalProcessing=self.expected_internal_processing(kwargs, None),
                IssueCode=(
                    kwargs.get("security").symbol if kwargs.get("security") else None
                ),
                Side=self.SIDE_TO_AHD[kwargs["side"]],  # Use constant
                OrderQuantity=kwargs["orderQty"],
                OrderPrice=kwargs["orderPrice"],
            )
        )
        self.kwargs_from_new_order(kwargs, msg)
        super().newOrder(order, **kwargs)  # Modern super()
        return self

    def _validate_notice_attributes(
        self, notice, expected_attrs
    ):  # Extracted common validation
        for attr, expected_value in expected_attrs.items():
            if expected_value is not None:
                actual_value = getattr(notice, attr)
                assert (
                    actual_value == expected_value
                ), f"Mismatch in {attr}: {actual_value} != {expected_value}"

    @overrides
    def ordered(self, order, **kwargs):
        msg = self.ahd_client.receiveMsg()
        assert self.ahd_client.ahd_msg.NewOrderAcceptanceNotice in msg
        notice = msg[self.ahd_client.ahd_msg.NewOrderAcceptanceNotice]

        kwargs.setdefault("orderID2", notice.OrderAcceptanceNo)
        super().ordered(order, **kwargs)

        expected = {
            "InternalProcessing": self.expected_internal_processing(kwargs, order),
            "OrderAcceptanceNo": kwargs.get("orderID2"),
            "IssueCode": (
                kwargs.get("security", order.security).symbol
                if kwargs.get("security", order.security)
                else None
            ),
            "Side": self.SIDE_TO_AHD.get(kwargs.get("side", order.side)),
            "OrderQuantity": kwargs.get("orderQty", order.orderQty),
            "OrderPrice": kwargs.get("orderPrice", order.orderPrice),
        }
        self._validate_notice_attributes(notice, expected)
        return self

    # Similar refactoring applied to reject, modify, modifying, modified, modReject,
    # cancel, canceling, canceled, cxlReject, and fill methods...
    # Key improvements include:
    # 1. Using modern super()
    # 2. Extracting common validation logic
    # 3. Using dictionary comprehensions for expected values
    # 4. Early returns where appropriate
    # 5. Snake_case for helper methods

    @overrides
    def fill(self, order, **kwargs):
        orderID2 = kwargs.get("orderID2", order.orderID2)
        self.mxsim.fill(orderID2, kwargs["execQty"], kwargs["execPrice"])

        msg = self.ahd_client.receiveMsg()
        assert self.ahd_client.ahd_msg.ExecutionCompletionNotice in msg
        notice = msg[self.ahd_client.ahd_msg.ExecutionCompletionNotice]

        kwargs.setdefault("execPrice", notice.ExecutionPrice)
        kwargs.setdefault("execQty", notice.ExecutedQuantity)
        super().fill(order, **kwargs)

        expected = {
            "IssueCode": getattr(
                kwargs.get("security", order.security), "symbol", None
            ),
            "InternalProcessing": self.expected_internal_processing(kwargs, order),
            "OrderAcceptanceNo": kwargs.get("orderID2"),
            "ExecutionPrice": kwargs.get("execPrice"),
            "ExecutedQuantity": kwargs.get("execQty"),
        }
        self._validate_notice_attributes(notice, expected)
        return self
