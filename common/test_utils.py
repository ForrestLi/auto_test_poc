import itertools
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock

import pytest
from hamcrest import assert_that, none
from hamcrest.core.matcher import Matcher


def validate_timestamps(tslist: List[float]) -> None:
    """Assert that all timestamps in `tslist` are within 30 seconds from now."""
    # Implementation would go here
    pass


@dataclass
class Order:
    """
    Stores information about an order. Default attributes are `checker`, `orderStatus`,
    `side`, `security`, `orderQty`, `execQty`, (read-only) `openQty`, `orderPrice`,
    (optional) `clOrdID`, (optional) `orderID2` and (optional) `timeInForce`.
    The checker may add additional properties.

    For certain attributes a modifcation history is kept. These attributes are
    defined in ``self.checker._modifyAttributes``. For these attributes the oldest,
    non-acknowledged version is available as `old<name>` (for example `oldOrderQty`,
    `oldOrderPrice`, `oldClOrdID`), the previous version is available as `prev<name>`
    (for example `prevOrderQty`, `prevOrderPrice`, `prevClOrdID`).

    Usual usage:

    1. Send an order with your actual test client.
    2. Create the order instance with a given checker instance.
    3. Perform some actions with your actual test client.
    4. Call the corresponding method(s) to tell the checker what was supposed to
       happen.
    5. Call `verify`.

    .. note: All methods return the order object. So multiple calls can be
             chained together.

    .. warning: All methods and the constructor must be called with keyword
               arguments only. This ensures easy extensibilty.

               Checkers can be composed by multiple inheritance. Arguments
               are treated as a dictionary and simply passed from one class
               to the next. Constructors have to be called with named
               arguments for the same reason.

    Example::

        client.sendOrder(qty=10, price=100, symbol=..., ...)
        o = Order(checker, orderQty=10, orderPrice=100, security=..., ...).verify()
        client.sendModify(...)
        o.modify(...).modifed().verify()
        // using sim mxsim.fill(...) or using opposite side's order to fill it later
        o.fill(...).verify()
    """

    checker: Any
    security: Any = None
    side: str = None
    # Primary snake_case attributes
    order_qty: Optional[int] = None
    exec_qty: int = 0
    order_price: Optional[float] = None
    cl_ord_id: Optional[str] = None
    dest_cl_ord_id: Optional[str] = None
    order_id2: Optional[str] = None
    time_in_force: Optional[str] = None
    client_id: Optional[str] = None
    account_id: Optional[str] = None
    order_status: str = "new"
    # camelCase aliases (optional). If provided, will be mapped to snake_case in __post_init__
    orderQty: Optional[int] = None
    execQty: Optional[int] = None
    orderPrice: Optional[float] = None
    clOrdID: Optional[str] = None
    destClOrdID: Optional[str] = None
    orderID2: Optional[str] = None
    timeInForce: Optional[str] = None
    clientID: Optional[str] = None
    accountID: Optional[str] = None
    orderStatus: Optional[str] = None
    dk: bool = False

    # Modification history
    queue: List[Dict] = field(default_factory=lambda: [{}])
    _modify_attributes = {"order_qty", "order_price", "cl_ord_id", "time_in_force"}

    def __post_init__(self):
        # Map camelCase constructor parameters to snake_case if provided
        alias_map = {
            "orderQty": "order_qty",
            "execQty": "exec_qty",
            "orderPrice": "order_price",
            "clOrdID": "cl_ord_id",
            "destClOrdID": "dest_cl_ord_id",
            "orderID2": "order_id2",
            "timeInForce": "time_in_force",
            "clientID": "client_id",
            "accountID": "account_id",
            "orderStatus": "order_status",
        }
        for camel, snake in alias_map.items():
            camel_val = getattr(self, camel)
            if camel_val is not None and getattr(self, snake) in (None, 0, "new"):
                setattr(self, snake, camel_val)

        self.checker.orders.append(self)

    def __str__(self) -> str:
        if hasattr(self, "order_status"):
            side_str = (
                "sell"
                if self.side == "S"
                else "buy" if self.side == "B" else repr(self.side)
            )
            price_str = (
                f"at {self.order_price}" if self.order_price is not None else "market"
            )
            cl_ord_str = f" clOrdID={self.cl_ord_id}" if self.cl_ord_id else ""
            id2_str = f" orderID2={self.order_id2}" if self.order_id2 else ""
            return f"<{self.order_status} {side_str} {self.order_qty} {self.security.symbol} {price_str}{cl_ord_str}{id2_str}>"
        return "<new order>"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__})"

    def verify(self) -> "Order":
        """Verify by calling checker's verify method."""
        self.checker.verify()
        return self

    @property
    def open_qty(self) -> Optional[int]:
        if self.order_qty is None or self.exec_qty is None:
            return None
        return 0 if self.order_status == "closed" else self.order_qty - self.exec_qty

    def __getattr__(self, name: str) -> Any:
        if name.startswith(("old_", "prev_")):
            prefix, attr_name = name.split("_", 1)
            if attr_name not in self._modify_attributes:
                raise AttributeError(
                    f"{self.__class__.__name__} doesn't have modify queue attribute {attr_name!r}"
                )

            try:
                if prefix == "old":
                    return self.queue[0][attr_name]
                else:  # prev
                    return self.queue[-2][attr_name]
            except (IndexError, KeyError):
                raise AttributeError(
                    f"{self.__class__.__name__} doesn't have modify queue attribute {name!r} set"
                )

        elif name in self._modify_attributes:
            try:
                return self.queue[-1][name]
            except KeyError:
                raise AttributeError(
                    f"{self.__class__.__name__} doesn't have modify queue attribute {name!r} set"
                )

        raise AttributeError(f"{self.__class__.__name__} has no attribute {name!r}")

    def push_modify(self) -> None:
        """Push current state to modification queue."""
        self.queue.append(dict(self.queue[-1]))

    def pop_modify(self, restore: bool) -> None:
        """Pop state from modification queue."""
        old_old = self.queue.pop(0)
        if restore:
            for attr in set(old_old) | set(self.queue[0]):
                if attr not in old_old:
                    del self.queue[0][attr]
                elif (
                    attr in {"order_qty", "order_price"}
                    and old_old[attr] is not None
                    and attr in self.queue[0]
                    and self.queue[0][attr] is not None
                ):
                    # Adjust numeric values through whole history
                    diff = self.queue[0][attr] - old_old[attr]
                    for i in range(len(self.queue)):
                        self.queue[i][attr] -= diff
                else:
                    # Push other values to front of queue
                    self.queue[0][attr] = old_old[attr]

    # Order action methods
    def ordering(self, **kwargs) -> "Order":
        """Expect this order is pending."""
        self.checker.ordering(self, **kwargs)
        return self

    def ordered(self, **kwargs) -> "Order":
        """Expect this order was confirmed."""
        self.checker.ordered(self, **kwargs)
        return self

    def reject(self, **kwargs) -> "Order":
        """Expect this order was rejected."""
        self.checker.reject(self, **kwargs)
        return self

    def modify(self, **kwargs) -> "Order":
        """Expect an order modification was sent."""
        self.checker.modify(self, **kwargs)
        return self

    def modifying(self, **kwargs) -> "Order":
        """Expect an order modification is pending."""
        self.checker.modifying(self, **kwargs)
        return self

    def modified(self, **kwargs) -> "Order":
        """Expect an order modification was confirmed."""
        self.checker.modified(self, **kwargs)
        return self

    def mod_reject(self, **kwargs) -> "Order":
        """Expect an order modification was rejected."""
        self.checker.mod_reject(self, **kwargs)
        return self

    def cancel(self, **kwargs) -> "Order":
        """Expect an order cancellation was sent."""
        self.checker.cancel(self, **kwargs)
        return self

    def canceling(self, **kwargs) -> "Order":
        """Expect an order cancellation is pending."""
        self.checker.canceling(self, **kwargs)
        return self

    def canceled(self, **kwargs) -> "Order":
        """Expect an order cancellation was confirmed."""
        self.checker.canceled(self, **kwargs)
        return self

    def cxl_reject(self, **kwargs) -> "Order":
        """Expect an order cancellation was rejected."""
        self.checker.cxl_reject(self, **kwargs)
        return self

    def expire(self, **kwargs) -> "Order":
        """Expect an order expiration was sent."""
        self.checker.expire(self, **kwargs)
        return self

    def dfd(self, **kwargs) -> "Order":
        """Expect a 'done for day' was sent."""
        self.checker.dfd(self, **kwargs)
        return self

    def fill(self, **kwargs) -> "Order":
        """Expect this order was (possibly partially) filled."""
        self.checker.fill(self, **kwargs)
        return self

    def fill_repeat_ticks(self, **kwargs) -> "Order":
        """Expect multiple fills for this order."""
        ticks = kwargs.pop("ticks")
        exec_qty = kwargs.pop("exec_qty")
        d_exec_qty = kwargs.pop("d_exec_qty", 0.0)
        exec_price = kwargs.pop("exec_price")
        d_exec_price = kwargs.pop("d_exec_price", 0.0)

        # Adjust prices based on side
        if self.side == "B":
            exec_price -= d_exec_price * (ticks - 1)
        else:
            exec_price += d_exec_price * (ticks - 1)
            d_exec_price *= -1

        # Execute multiple fills
        for i in range(ticks):
            self.fill(
                exec_qty=exec_qty + i * d_exec_qty,
                exec_price=exec_price + i * d_exec_price,
                **kwargs,
            )
        return self

    def bust(self, **kwargs) -> "Order":
        """Expect an order execution was busted."""
        self.checker.bust(self, **kwargs)
        return self

    # Internal methods for state changes
    def _new_order(self, **kwargs) -> None:
        """Handle new order creation."""
        kwargs = self._normalize_kwargs(kwargs)
        self.dk = kwargs.get("dk", False)
        self.security = kwargs.get("security")
        self.side = kwargs.get("side")
        self.order_qty = kwargs.get("order_qty")
        self.exec_qty = 0 if not self.dk else None
        self.order_price = kwargs.get("order_price")
        self.cl_ord_id = kwargs.get("cl_ord_id")
        self.dest_cl_ord_id = kwargs.get("dest_cl_ord_id")
        self.order_id2 = kwargs.get("order_id2")
        self.time_in_force = kwargs.get("time_in_force")
        self.client_id = kwargs.get("client_id")
        self.account_id = kwargs.get("account_id")

    def _ordering(self, **kwargs) -> None:
        """Handle ordering state."""
        kwargs = self._normalize_kwargs(kwargs)
        for attr in [
            "order_qty",
            "order_price",
            "cl_ord_id",
            "dest_cl_ord_id",
            "order_id2",
            "time_in_force",
            "client_id",
            "account_id",
        ]:
            if attr in kwargs and kwargs[attr] is not None:
                setattr(self, attr, kwargs[attr])

    def _ordered(self, **kwargs) -> None:
        """Handle ordered state."""
        kwargs = self._normalize_kwargs(kwargs)
        self.order_status = "open"
        self._ordering(**kwargs)

    def _reject(self, **kwargs) -> None:
        """Handle reject state."""
        kwargs = self._normalize_kwargs(kwargs)
        self.order_status = "closed"

    def _modify(self, **kwargs) -> None:
        """Handle modify state."""
        kwargs = self._normalize_kwargs(kwargs)
        self.push_modify()

        if "order_qty" in kwargs and kwargs["order_qty"] is not None:
            self.order_qty = max(kwargs["order_qty"], 0)
        elif "d_order_qty" in kwargs and kwargs["d_order_qty"] is not None:
            self.order_qty += max(kwargs["d_order_qty"], -(self.open_qty or 0))

        if "order_price" in kwargs and kwargs["order_price"] is not None:
            self.order_price = kwargs["order_price"]
        elif "d_order_price" in kwargs and kwargs["d_order_price"] is not None:
            self.order_price += kwargs["d_order_price"]

        for attr in [
            "cl_ord_id",
            "dest_cl_ord_id",
            "time_in_force",
            "client_id",
            "account_id",
        ]:
            if attr in kwargs and kwargs[attr] is not None:
                setattr(self, attr, kwargs[attr])

    def _modifying(self, **kwargs) -> None:
        """Handle modifying state."""
        kwargs = self._normalize_kwargs(kwargs)
        self._ordering(**kwargs)

    def _modified(self, **kwargs) -> None:
        """Handle modified state."""
        kwargs = self._normalize_kwargs(kwargs)
        self.pop_modify(False)
        self._ordering(**kwargs)

        if self.open_qty <= 0:
            self.order_status = "closed"

    def _mod_reject(self, **kwargs) -> None:
        """Handle mod reject state."""
        kwargs = self._normalize_kwargs(kwargs)
        self.pop_modify(True)

    def _cancel(self, **kwargs) -> None:
        """Handle cancel state."""
        kwargs = self._normalize_kwargs(kwargs)
        self.push_modify()
        for attr in ["cl_ord_id", "dest_cl_ord_id", "client_id", "account_id"]:
            if attr in kwargs and kwargs[attr] is not None:
                setattr(self, attr, kwargs[attr])

    def _canceling(self, **kwargs) -> None:
        """Handle canceling state."""
        kwargs = self._normalize_kwargs(kwargs)
        self._ordering(**kwargs)

    def _canceled(self, **kwargs) -> None:
        """Handle canceled state."""
        kwargs = self._normalize_kwargs(kwargs)
        self.pop_modify(False)
        self._ordering(**kwargs)
        self.order_status = "closed"

    def _cxl_reject(self, **kwargs) -> None:
        """Handle cxl reject state."""
        kwargs = self._normalize_kwargs(kwargs)
        self.pop_modify(True)

    def _expire(self, **kwargs) -> None:
        """Handle expire state."""
        kwargs = self._normalize_kwargs(kwargs)
        self.order_status = "closed"
        for attr in ["client_id", "account_id"]:
            if attr in kwargs and kwargs[attr] is not None:
                setattr(self, attr, kwargs[attr])

    def _dfd(self, **kwargs) -> None:
        """Handle dfd state."""
        kwargs = self._normalize_kwargs(kwargs)
        self.order_status = "closed"
        for attr in ["client_id", "account_id"]:
            if attr in kwargs and kwargs[attr] is not None:
                setattr(self, attr, kwargs[attr])

    def _fill(self, **kwargs) -> None:
        """Handle fill state."""
        kwargs = self._normalize_kwargs(kwargs)
        self.exec_qty += kwargs["exec_qty"]
        # Handle modify/fill race condition
        if self.order_qty is not None and self.exec_qty is not None:
            self.order_qty = max(self.order_qty, self.exec_qty)

        if self.open_qty <= 0:
            self.order_status = "closed"

        for attr in ["client_id", "account_id"]:
            if attr in kwargs and kwargs[attr] is not None:
                setattr(self, attr, kwargs[attr])

    def _bust(self, **kwargs) -> None:
        """Handle bust state."""
        kwargs = self._normalize_kwargs(kwargs)
        self.exec_qty -= kwargs["exec_qty"]
        if self.open_qty > 0:
            self.order_status = "open"

        for attr in ["client_id", "account_id"]:
            if attr in kwargs and kwargs[attr] is not None:
                setattr(self, attr, kwargs[attr])

    # Helper: normalize incoming kwargs from camelCase to snake_case
    def _normalize_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        if not kwargs:
            return {}
        mapping = {
            "orderQty": "order_qty",
            "execQty": "exec_qty",
            "orderPrice": "order_price",
            "clOrdID": "cl_ord_id",
            "destClOrdID": "dest_cl_ord_id",
            "orderID2": "order_id2",
            "timeInForce": "time_in_force",
            "clientID": "client_id",
            "accountID": "account_id",
            "orderStatus": "order_status",
            "dOrderQty": "d_order_qty",
            "dOrderPrice": "d_order_price",
            "execPrice": "exec_price",
            "execID2": "exec_id2",
            "transactTime": "transact_time",
            "tradeDate": "trade_date",
        }
        out = dict(kwargs)
        for camel, snake in mapping.items():
            if camel in out and snake not in out:
                out[snake] = out[camel]
        return out

    # CamelCase method aliases to maintain backward compatibility
    def modReject(self, **kwargs) -> "Order":
        return self.mod_reject(**kwargs)

    def cxlReject(self, **kwargs) -> "Order":
        return self.cxl_reject(**kwargs)


class GenericChecker:
    """Base checker class for verifying order states."""

    # Attributes that can be modified and tracked
    _modify_attributes = {"order_qty", "order_price", "cl_ord_id", "time_in_force"}
    _modify_delta_attributes = {"order_qty", "order_price"}
    _fill_repeat_ticks_list_kwargs = {"exec_id2", "transact_time", "trade_date"}

    def __init__(self, **kwargs):
        self.orders: List[Order] = []
        self.order_hashes: Dict[str, Dict] = {}

    # CamelCase alias so subclasses can @overrides("newOrder") while the canonical
    # implementation remains snake_case new_order
    def newOrder(self, order: Order, **kwargs) -> "GenericChecker":
        return self.new_order(order, **kwargs)

    def find_order_by(self, attribute: str, value: Any) -> Optional[Order]:
        """Find an order by attribute value."""
        if attribute in self.order_hashes:
            return self.order_hashes[attribute].get(value, None)

        # Build hash if not already built
        hash_map = {}
        for order in self.orders:
            hash_map[getattr(order, attribute)] = order
        self.order_hashes[attribute] = hash_map
        return hash_map.get(value, None)

    def reset(self) -> "GenericChecker":
        """Reset checker state."""
        return self

    def verify(self) -> None:
        """Verify expected state."""
        self.reset()

    def callback(self, callback_type: str, order: Order, **kwargs) -> None:
        """Generic callback method for order events."""
        method_name = f"_{callback_type}"
        if hasattr(order, method_name):
            getattr(order, method_name)(**kwargs)

    def new_order(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle new order creation."""
        self.callback("new_order", order, **kwargs)
        return self

    def ordering(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle ordering state."""
        self.callback("ordering", order, **kwargs)
        return self

    def ordered(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle ordered state."""
        self.callback("ordered", order, **kwargs)
        return self

    def reject(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle reject state."""
        self.callback("reject", order, **kwargs)
        return self

    def modify(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle modify state."""
        self.callback("modify", order, **kwargs)
        return self

    def modifying(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle modifying state."""
        self.callback("modifying", order, **kwargs)
        return self

    def modified(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle modified state."""
        self.callback("modified", order, **kwargs)
        return self

    def mod_reject(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle mod reject state."""
        self.callback("mod_reject", order, **kwargs)
        return self

    def cancel(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle cancel state."""
        self.callback("cancel", order, **kwargs)
        return self

    def canceling(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle canceling state."""
        self.callback("canceling", order, **kwargs)
        return self

    def canceled(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle canceled state."""
        self.callback("canceled", order, **kwargs)
        return self

    def cxl_reject(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle cxl reject state."""
        self.callback("cxl_reject", order, **kwargs)
        return self

    def expire(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle expire state."""
        self.callback("expire", order, **kwargs)
        return self

    def dfd(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle dfd state."""
        self.callback("dfd", order, **kwargs)
        return self

    def fill(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle fill state."""
        self.callback("fill", order, **kwargs)
        return self

    def bust(self, order: Order, **kwargs) -> "GenericChecker":
        """Handle bust state."""
        self.callback("bust", order, **kwargs)
        return self


class LoggingChecker(GenericChecker):
    """Checker that logs all events for debugging."""

    def callback(self, callback_type: str, order: Order, **kwargs) -> None:
        """Log events before processing."""
        kwargs_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        print(f"{callback_type}(order={order}, {kwargs_str})")
        super().callback(callback_type, order, **kwargs)
