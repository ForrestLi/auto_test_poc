import pytest

from common.test_utils import Order, GenericChecker
from fix_poc.conftest import FIXChecker


class Security:
    def __init__(self, symbol: str):
        self.symbol = symbol


@pytest.fixture
def checker():
    class DummyFixClient:
        def __init__(self):
            self.sent = []
            self.received = []

        def sendMsg(self, msg):
            self.sent.append(msg)

        def receiveMsg(self):
            return self.received.pop(0) if self.received else {}

    class DummyExchangeSim:
        def fill(self, order_id, qty, price):
            # no-op for unit test
            pass

    fix_client = DummyFixClient()
    return FIXChecker(fix_client=fix_client, exchange_sim=DummyExchangeSim())


@pytest.fixture
def security():
    return Security("BABA")


def test_order_constructor_maps_camel_case(checker, security):
    o = Order(
        checker,
        security=security,
        side="B",
        orderQty=100,
        orderPrice=101.25,
        clOrdID="ABC",
        timeInForce="DAY",
    ).verify()

    assert o.order_qty == 100
    assert o.order_price == 101.25
    assert o.cl_ord_id == "ABC"
    assert o.time_in_force == "DAY"
    assert o.order_status == "new"


def test_state_transitions_ordered_modified_canceled(checker, security):
    order_id = "ORD-STATE-1"
    # Enqueue ExecutionReport NEW ack with required ORDER_ID (37)
    checker.fix_client.received.append(
        {
            "35": "8",  # ExecutionReport
            "150": "0",  # ExecType=NEW
            "39": "0",  # OrdStatus=NEW
            "37": order_id,
            "55": security.symbol,
            "54": "2",  # Side=Sell
            "38": "100",
            "44": "10.0",
        }
    )

    o = (
        Order(checker, security=security, side="S", orderQty=100, orderPrice=10.0)
        .ordered(orderID=order_id)
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
    order_id = "ORD-FILL-1"
    # NEW ack for order acceptance
    checker.fix_client.received.append(
        {
            "35": "8",
            "150": "0",
            "39": "0",
            "37": order_id,
            "55": security.symbol,
            "54": "1",  # Side=Buy
            "38": "10",
            "44": "5.0",
        }
    )
    o = (
        Order(checker, security=security, side="B", orderQty=10, orderPrice=5.0)
        .ordered(orderID=order_id)
        .verify()
    )

    # Use camelCase args to ensure normalization works
    # Enqueue ER FILL ack for first partial fill
    checker.fix_client.received.append(
        {
            "35": "8",
            "150": "2",  # ExecType=FILL
            "39": "2",  # OrdStatus=FILLED (we treat as fill for unit test)
            "37": order_id,
            "32": "6",  # LastShares
            "31": "5.1",  # LastPx
            "55": security.symbol,
            "54": "1",
            "38": "10",
        }
    )
    o = o.fill(orderID=order_id, execQty=6, execPrice=5.1)
    assert o.exec_qty == 6
    assert o.open_qty == 4

    # Enqueue ER FILL ack for remaining fill
    checker.fix_client.received.append(
        {
            "35": "8",
            "150": "2",
            "39": "2",
            "37": order_id,
            "32": "4",
            "31": "5.2",
            "55": security.symbol,
            "54": "1",
            "38": "10",
        }
    )
    o = o.fill(orderID=order_id, execQty=4, execPrice=5.2)
    assert o.exec_qty == 10
    assert o.open_qty == 0
    assert o.order_status == "filled"


def test_d_modify_and_normalization(checker, security):
    order_id = "ORD-MOD-1"
    checker.fix_client.received.append(
        {
            "35": "8",
            "150": "0",
            "39": "0",
            "37": order_id,
            "55": security.symbol,
            "54": "2",
            "38": "100",
            "44": "10.0",
        }
    )
    o = (
        Order(checker, security=security, side="S", orderQty=100, orderPrice=10.0)
        .ordered(orderID=order_id)
        .verify()
    )

    # Decrease quantity using camelCase delta keys
    o = o.modify(dOrderQty=-10).modified()
    assert o.order_qty == 90

    # Increase price using camelCase delta key
    o = o.modify(dOrderPrice=0.5).modified()
    assert o.order_price == 10.5
