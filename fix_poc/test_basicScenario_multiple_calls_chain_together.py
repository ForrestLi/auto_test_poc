import pytest
from decimal import Decimal
from common.test_utils import Order
import quickfix as fix


def test_new_order_single_cancel(fix_checker, security):
    """Test new order single followed by cancel."""
    (
        Order(
            fix_checker,
            symbol=security.symbol,
            side=fix.Side_BUY,
            order_qty=100,
            price=Decimal("100.50"),
            ord_type=fix.OrdType_LIMIT,
        )
        .new_order_single()
        .verify()
        .cancel()
        .verify()
    )


def test_order_modification(fix_checker, security):
    """Test order modification."""
    order = (
        Order(
            fix_checker,
            symbol=security.symbol,
            side=fix.Side_SELL,
            order_qty=200,
            price=Decimal("99.75"),
            ord_type=fix.OrdType_LIMIT,
        )
        .new_order_single()
        .verify()
    )

    (order.modify(order_qty=150, price=Decimal("100.00")).verify())


def test_mass_cancel(fix_checker, security, fix_simulator):
    """Test mass cancel order."""
    # Setup multiple orders
    orders = []
    for i in range(3):
        order = (
            Order(
                fix_checker,
                symbol=security.symbol,
                side=fix.Side_BUY,
                order_qty=100 + i * 50,
                price=Decimal("100.00") - Decimal(str(i * 0.5)),
                ord_type=fix.OrdType_LIMIT,
            )
            .new_order_single()
            .verify()
        )
        orders.append(order)

    # Send mass cancel
    fix_simulator.mass_cancel(
        security.symbol, fix.MassCancelRequestType_CANCEL_ALL_ORDERS
    )

    # Verify all orders are canceled
    for order in orders:
        order.verify_canceled()


def test_order_rejection(fix_checker, fix_simulator, security):
    """Test order rejection scenario."""
    # Configure simulator to reject orders
    fix_simulator.configure(reject_new_orders=True)

    (
        Order(
            fix_checker,
            symbol=security.symbol,
            side=fix.Side_BUY,
            order_qty=1000,  # Large quantity that might be rejected
            price=Decimal("50.00"),
            ord_type=fix.OrdType_LIMIT,
        )
        .new_order_single()
        .verify_rejected(fix.OrdStatus_REJECTED)
    )


def test_partial_fill(fix_checker, security):
    """Test partial order fill."""
    order = (
        Order(
            fix_checker,
            symbol=security.symbol,
            side=fix.Side_BUY,
            order_qty=1000,
            price=Decimal("101.25"),
            ord_type=fix.OrdType_LIMIT,
        )
        .new_order_single()
        .verify()
    )

    # Simulate partial fill
    order.partial_fill(500, Decimal("101.25"))

    # Verify partial fill
    order.verify_partial_fill()

    # Cancel remaining quantity
    order.cancel().verify()
