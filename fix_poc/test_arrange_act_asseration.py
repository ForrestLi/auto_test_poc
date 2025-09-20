import pytest
from decimal import Decimal
import quickfix as fix


def test_new_order_single_cancel(fix_client, security):
    """Test new order single followed by cancel using Arrange-Act-Assert pattern."""
    # Arrange
    symbol = security.symbol
    side = fix.Side_BUY
    order_qty = 100
    price = Decimal("100.50")

    # Act - Send new order
    cl_ord_id = fix_client.send_new_order_single(
        symbol=symbol, side=side, order_qty=order_qty, price=price
    )

    # Assert - Verify order acknowledgment
    exec_report = fix_client.wait_for_execution_report(
        cl_ord_id, expected_status=fix.OrdStatus_NEW
    )

    assert exec_report is not None, "Order acknowledgment not received"
    assert exec_report.getField(fix.OrdStatus) == fix.OrdStatus_NEW
    assert exec_report.getField(fix.Symbol) == symbol
    assert Decimal(exec_report.getField(fix.OrderQty)) == order_qty

    # Act - Send cancel request
    cancel_cl_ord_id = f"CXL_{cl_ord_id}"
    fix_client.send_order_cancel_request(cancel_cl_ord_id, cl_ord_id)

    # Assert - Verify cancel acknowledgment
    cancel_report = fix_client.wait_for_execution_report(
        cl_ord_id, expected_status=fix.OrdStatus_CANCELED
    )

    assert cancel_report is not None, "Cancel acknowledgment not received"
    assert cancel_report.getField(fix.OrdStatus) == fix.OrdStatus_CANCELED


def test_order_modification(fix_client, security):
    """Test order modification using Arrange-Act-Assert pattern."""
    # Arrange
    symbol = security.symbol
    side = fix.Side_SELL
    initial_order_qty = 200
    initial_price = Decimal("99.75")
    modified_order_qty = 150
    modified_price = Decimal("100.00")

    # Act - Send initial order
    cl_ord_id = fix_client.send_new_order_single(
        symbol=symbol, side=side, order_qty=initial_order_qty, price=initial_price
    )

    # Assert - Verify initial order
    initial_report = fix_client.wait_for_execution_report(
        cl_ord_id, expected_status=fix.OrdStatus_NEW
    )

    assert initial_report is not None, "Initial order acknowledgment not received"

    # Act - Send modification
    modify_cl_ord_id = f"MOD_{cl_ord_id}"
    fix_client.send_order_cancel_replace_request(
        modify_cl_ord_id, cl_ord_id, order_qty=modified_order_qty, price=modified_price
    )

    # Assert - Verify modification
    modify_report = fix_client.wait_for_execution_report(
        cl_ord_id, expected_status=fix.OrdStatus_REPLACED
    )

    assert modify_report is not None, "Modification acknowledgment not received"
    assert Decimal(modify_report.getField(fix.OrderQty)) == modified_order_qty
    assert Decimal(modify_report.getField(fix.Price)) == modified_price


def test_order_rejection(fix_client, fix_simulator, security):
    """Test order rejection scenario using Arrange-Act-Assert pattern."""
    # Arrange - Configure simulator to reject orders
    fix_simulator.configure(reject_new_orders=True)

    # Act - Send order that should be rejected
    cl_ord_id = fix_client.send_new_order_single(
        symbol=security.symbol,
        side=fix.Side_BUY,
        order_qty=10000,  # Large quantity that should be rejected
        price=Decimal("50.00"),
    )

    # Assert - Verify rejection
    reject_report = fix_client.wait_for_execution_report(
        cl_ord_id, expected_status=fix.OrdStatus_REJECTED
    )

    assert reject_report is not None, "Rejection acknowledgment not received"
    assert reject_report.getField(fix.OrdStatus) == fix.OrdStatus_REJECTED


def test_partial_fill(fix_client, fix_simulator, security):
    import pytest
    from decimal import Decimal
    import quickfix as fix

    def test_new_order_single_cancel(fix_client, security):
        """Test new order single followed by cancel using Arrange-Act-Assert pattern."""
        # Arrange
        symbol = security.symbol
        side = fix.Side_BUY
        order_qty = 100
        price = Decimal("100.50")

        # Act - Send new order
        cl_ord_id = fix_client.send_new_order_single(
            symbol=symbol, side=side, order_qty=order_qty, price=price
        )

        # Assert - Verify order acknowledgment
        exec_report = fix_client.wait_for_execution_report(
            cl_ord_id, expected_status=fix.OrdStatus_NEW
        )

        assert exec_report is not None, "Order acknowledgment not received"
        assert exec_report.getField(fix.OrdStatus) == fix.OrdStatus_NEW
        assert exec_report.getField(fix.Symbol) == symbol
        assert Decimal(exec_report.getField(fix.OrderQty)) == order_qty

        # Act - Send cancel request
        cancel_cl_ord_id = f"CXL_{cl_ord_id}"
        fix_client.send_order_cancel_request(cancel_cl_ord_id, cl_ord_id)

        # Assert - Verify cancel acknowledgment
        cancel_report = fix_client.wait_for_execution_report(
            cl_ord_id, expected_status=fix.OrdStatus_CANCELED
        )

        assert cancel_report is not None, "Cancel acknowledgment not received"
        assert cancel_report.getField(fix.OrdStatus) == fix.OrdStatus_CANCELED

    def test_order_modification(fix_client, security):
        """Test order modification using Arrange-Act-Assert pattern."""
        # Arrange
        symbol = security.symbol
        side = fix.Side_SELL
        initial_order_qty = 200
        initial_price = Decimal("99.75")
        modified_order_qty = 150
        modified_price = Decimal("100.00")

        # Act - Send initial order
        cl_ord_id = fix_client.send_new_order_single(
            symbol=symbol, side=side, order_qty=initial_order_qty, price=initial_price
        )

        # Assert - Verify initial order
        initial_report = fix_client.wait_for_execution_report(
            cl_ord_id, expected_status=fix.OrdStatus_NEW
        )

        assert initial_report is not None, "Initial order acknowledgment not received"

        # Act - Send modification
        modify_cl_ord_id = f"MOD_{cl_ord_id}"
        fix_client.send_order_cancel_replace_request(
            modify_cl_ord_id,
            cl_ord_id,
            order_qty=modified_order_qty,
            price=modified_price,
        )

        # Assert - Verify modification
        modify_report = fix_client.wait_for_execution_report(
            cl_ord_id, expected_status=fix.OrdStatus_REPLACED
        )

        assert modify_report is not None, "Modification acknowledgment not received"
        assert Decimal(modify_report.getField(fix.OrderQty)) == modified_order_qty
        assert Decimal(modify_report.getField(fix.Price)) == modified_price

    def test_order_rejection(fix_client, mx_sim, security):
        """Test order rejection scenario using Arrange-Act-Assert pattern."""
        # Arrange - Configure MX simulator to reject orders
        mx_sim.zcmd("cf --reject=1")  # MX simulator command to configure rejection

        # Act - Send order that should be rejected
        cl_ord_id = fix_client.send_new_order_single(
            symbol=security.symbol,
            side=fix.Side_BUY,
            order_qty=10000,  # Large quantity that should be rejected
            price=Decimal("50.00"),
        )

        # Assert - Verify rejection
        reject_report = fix_client.wait_for_execution_report(
            cl_ord_id, expected_status=fix.OrdStatus_REJECTED
        )

        assert reject_report is not None, "Rejection acknowledgment not received"
        assert reject_report.getField(fix.OrdStatus) == fix.OrdStatus_REJECTED

    def test_partial_fill(fix_client, mx_sim, security):
        """Test partial order fill using Arrange-Act-Assert pattern."""
        # Arrange
        symbol = security.symbol
        side = fix.Side_BUY
        order_qty = 1000
        price = Decimal("101.25")
        fill_qty = 500

        # Configure MX simulator to send partial fills
        mx_sim.zcmd(f"cf --partial_fill={fill_qty}")

        # Act - Send order
        cl_ord_id = fix_client.send_new_order_single(
            symbol=symbol, side=side, order_qty=order_qty, price=price
        )

        # Assert - Verify partial fill
        fill_report = fix_client.wait_for_execution_report(
            cl_ord_id, expected_status=fix.OrdStatus_PARTIALLY_FILLED
        )

        assert fill_report is not None, "Fill report not received"
        assert fill_report.getField(fix.OrdStatus) == fix.OrdStatus_PARTIALLY_FILLED
        assert Decimal(fill_report.getField(fix.CumQty)) == fill_qty
        assert Decimal(fill_report.getField(fix.LeavesQty)) == order_qty - fill_qty

    def test_mass_cancel(fix_client, mx_sim, security):
        """Test mass cancel order using Arrange-Act-Assert pattern."""
        # Arrange - Create multiple orders
        orders = []
        for i in range(3):
            cl_ord_id = fix_client.send_new_order_single(
                symbol=security.symbol,
                side=fix.Side_BUY,
                order_qty=100 + i * 50,
                price=Decimal("100.00") - Decimal(str(i * 0.5)),
            )
            orders.append(cl_ord_id)

        # Verify all orders are active
        for cl_ord_id in orders:
            report = fix_client.wait_for_execution_report(
                cl_ord_id, expected_status=fix.OrdStatus_NEW
            )
            assert report is not None, f"Order {cl_ord_id} not acknowledged"

        # Act - Send mass cancel using MX simulator
        mx_sim.zcmd(f"mass_cancel {security.symbol} ALL")

        # Assert - Verify all orders are canceled
        for cl_ord_id in orders:
            cancel_report = fix_client.wait_for_execution_report(
                cl_ord_id, expected_status=fix.OrdStatus_CANCELED
            )
            assert cancel_report is not None, f"Order {cl_ord_id} not canceled"

    def test_modify_reject_and_cancel_reject(fix_client, mx_sim, security):
        """Test modify reject and cancel reject scenarios using Arrange-Act-Assert pattern."""
        # Arrange - Configure MX simulator to reject modifications and cancels
        mx_sim.zcmd("cf --reject=0 --modReject=1 --cxlReject=1")

        # Act - Send order
        cl_ord_id = fix_client.send_new_order_single(
            symbol=security.symbol,
            side=fix.Side_SELL,
            order_qty=100,
            price=Decimal("100.00"),
        )

        # Assert - Verify order is accepted
        order_report = fix_client.wait_for_execution_report(
            cl_ord_id, expected_status=fix.OrdStatus_NEW
        )
        assert order_report is not None, "Order not accepted"

        # Act - Try to modify order (should be rejected)
        modify_cl_ord_id = f"MOD_{cl_ord_id}"
        fix_client.send_order_cancel_replace_request(
            modify_cl_ord_id, cl_ord_id, order_qty=90
        )

        # Assert - Verify modification was rejected
        mod_reject_report = fix_client.wait_for_execution_report(
            cl_ord_id, expected_status=fix.OrdStatus_REJECTED
        )
        assert mod_reject_report is not None, "Modification rejection not received"

        # Act - Try to cancel order (should be rejected)
        cancel_cl_ord_id = f"CXL_{cl_ord_id}"
        fix_client.send_order_cancel_request(cancel_cl_ord_id, cl_ord_id)

        # Assert - Verify cancellation was rejected
        cancel_reject_report = fix_client.wait_for_execution_report(
            cl_ord_id, expected_status=fix.OrdStatus_REJECTED
        )
        assert cancel_reject_report is not None, "Cancellation rejection not received"


def test_mass_cancel(fix_client, fix_simulator, security):
    """Test mass cancel order using Arrange-Act-Assert pattern."""
    # Arrange - Create multiple orders
    orders = []
    for i in range(3):
        cl_ord_id = fix_client.send_new_order_single(
            symbol=security.symbol,
            side=fix.Side_BUY,
            order_qty=100 + i * 50,
            price=Decimal("100.00") - Decimal(str(i * 0.5)),
        )
        orders.append(cl_ord_id)

    # Verify all orders are active
    for cl_ord_id in orders:
        report = fix_client.wait_for_execution_report(
            cl_ord_id, expected_status=fix.OrdStatus_NEW
        )
        assert report is not None, f"Order {cl_ord_id} not acknowledged"

    # Act - Send mass cancel
    fix_simulator.mass_cancel(
        security.symbol, fix.MassCancelRequestType_CANCEL_ALL_ORDERS
    )

    # Assert - Verify all orders are canceled
    for cl_ord_id in orders:
        cancel_report = fix_client.wait_for_execution_report(
            cl_ord_id, expected_status=fix.OrdStatus_CANCELED
        )
        assert cancel_report is not None, f"Order {cl_ord_id} not canceled"
