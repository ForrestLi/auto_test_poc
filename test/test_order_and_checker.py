import pytest

from common.test_utils import Order, GenericChecker


class Security:
    def __init__(self, symbol: str):
        self.symbol = symbol


@pytest.fixture
def checker():
    return GenericChecker()


@pytest.fixture
def security():
    return Security("AAPL")


def test_order_constructor_maps_camel_case(checker, security):
    o = Order(
        checker,
        security=security,
        side="B",
        orderQty=100,
        orderPrice=101.25,
        clOrdID="ABC",
        timeInForce="DAY",
    )

    assert o.order_qty == 100
    assert o.order_price == 101.25
    assert o.cl_ord_id == "ABC"
    assert o.time_in_force == "DAY"
    assert o.order_status == "new"


def test_state_transitions_ordered_modified_canceled(checker, security):
    o = (
        Order(checker, security=security, side="S", orderQty=100, orderPrice=10.0)
        .ordered()
        .verify()
        .modify(orderPrice=11.0)
        .modified()
        .verify()
        .cancel()
        .canceled()
        .verify()
    )

    assert o.order_status == "cancelled"
    assert o.order_price == 11.0


def test_fill_and_open_qty(checker, security):
    o = (
        Order(checker, security=security, side="B", orderQty=10, orderPrice=5.0)
        .ordered()
        .verify()
    )

    # Use camelCase args to ensure normalization works
    o = o.fill(execQty=6, execPrice=5.1)
    assert o.exec_qty == 6
    assert o.open_qty == 4

    o = o.fill(execQty=4, execPrice=5.2)
    assert o.exec_qty == 10
    assert o.open_qty == 0
    assert o.order_status == "filled"


def test_d_modify_and_normalization(checker, security):
    o = (
        Order(checker, security=security, side="S", orderQty=100, orderPrice=10.0)
        .ordered()
        .verify()
    )

    # Decrease quantity using camelCase delta keys
    o = o.modify(dOrderQty=-10).modified()
    assert o.order_qty == 90

    # Increase price using camelCase delta key
    o = o.modify(dOrderPrice=0.5).modified()
    assert o.order_price == 10.5
