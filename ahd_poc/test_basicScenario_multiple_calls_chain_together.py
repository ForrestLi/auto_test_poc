import pytest
from common.test_utils import Order


def test_newCancel(checker, security, price):
    """Test order creation and cancellation."""
    (
        Order(checker, security=security, side="S", orderQty=100, orderPrice=price)
        .ordered()
        .verify()
        .cancel()
        .canceled()
        .verify()
    )


def test_newModifyModifyCancel(checker, security, price):
    """Test order with multiple modifications and cancellation."""
    (
        Order(checker, security=security, side="S", orderQty=100, orderPrice=price)
        .ordered()
        .verify()
        .modify(orderPrice=price + 1)
        .modified()
        .verify()
        .modify(dOrderQty=-1)
        .modified()
        .verify()
        .cancel()
        .canceled()
        .verify()
    )


def test_newReject(checker, mxsim, security, price):
    """Test order rejection."""
    mxsim.zcmd("cf --reject=1")
    (
        Order(checker, security=security, side="S", orderQty=100, orderPrice=price)
        .reject()
        .verify()
    )


def test_newModifyFill(checker, mxsim, security, price):
    """Test complex order workflow with modifications and fills."""
    # Order with modifications
    order = (
        Order(checker, security=security, side="S", orderQty=100, orderPrice=price)
        .ordered()
        .verify()
        .modify(orderPrice=price + 1)
        .modified()
        .verify()
        .modify(dOrderQty=-1)
        .modified()
        .verify()
    )

    # Partial fill and cancellation
    (order.fill(execPrice=price + 1, execQty=50).verify().cancel().canceled().verify())

    # Test reject scenarios
    mxsim.zcmd("cf --reject=1")
    (
        Order(checker, security=security, side="S", orderQty=100, orderPrice=price)
        .reject()
        .verify()
    )

    # Test modification and cancellation rejection
    mxsim.zcmd("cf --reject=0 --modReject=1 --cxlReject=1")
    order = (
        Order(checker, security=security, side="S", orderQty=100, orderPrice=price)
        .ordered()
        .verify()
    )

    (order.modify(dOrderQty=-1).modReject().verify().cancel().cxlReject().verify())
