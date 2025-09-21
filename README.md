This repository contains a proof-of-concept (PoC) for an automated testing framework designed for integration testing of 
electronic trading systems. The framework validates systems communicating via the FIX protocol or other binary protocols
(e.g., AHD).

The primary objective is to automate test scenarios based on priorities as agreed upon by all stakeholders.
e.g. Cover business critical, regulatory, most repeated smoke/regression suites ones first.

**Value Proposition:**
*   **Reliability & Repeatability:** Automates manual testing processes, ensuring consistent results.
*   **Modularity:** Clean dependency injection makes tests easy to write, understand, and maintain.
*   **Coverage:** Supports testing of complex, stateful workflows endemic to trading systems.
(order placement, cancel/replace, etc.).
*   **Foundation for Performance Testing:** Lays the groundwork for future latency measurement and load testing.

## Phase I: Foundation

### Objective
Establish a robust foundation for message-level integration testing of the trading stack, focusing on reliability 
and repeatability. 

### Technical Approach
The framework uses **pytest** as its core due to powerful features for organizing tests and managing dependencies 
cleanly through its fixture mechanism.

**Dependency Injection:** Dependencies (e.g., market simulators, securities data, risk limits data) are injected 
into test cases using `@pytest.fixture`. This promotes modular and maintainable code.

**Example AHD fixture (`conftest.py`):**
```
@pytest.fixture
def checker(request, ems, securities, mxsim, ahd_client):
    """Provides a pre-configured AHD protocol checker object."""
    return AHDChecker(
        rawPlugin='AHD',
        mxgw=ems,
        securities=securities,
        mxsim=mxsim,
        client=request.config.getini('ahd_client'),
        account=request.config.getini('ahd_account'),
        ahd_client=ahd_client
    ).reset()
```
(Please note Junit+Spring+Json+Weddriver ones are more suitable for GUI level testing, not for message level ones
https://github.com/ForrestLi/Web_Test_Studio_CrypyT)

Test Environment & Stubbing: 


System Topology:

[ FIX/Binary Client ] -> [ Trading System (SUT) ] -> [ Exchange Simulator ]

SUT (System Under Test): The trading system itself.

Exchange Simulator: Mimics exchange behavior. Can be replaced by a real Exchange Proxy in Phase II.

Stubs: Provide risk limits data and reference data to the SUT for deterministic testing.

Testing Methodology
The framework supports multiple patterns for structuring test logic:

1, Explicit Arrange-Act-Assert (AAA):
Ideal for complex, one-off test scenarios where clarity is paramount.

example FIX one
```
def test_new_order_single_acknowledgment(fix_client, security):
    # Arrange
    symbol = security.symbol
    side = fix.Side_BUY
    order_qty = 100
    price = Decimal('100.50')

    # Act
    cl_ord_id = fix_client.send_new_order_single(
        symbol=symbol, side=side, order_qty=order_qty, price=price
    )

    # Assert - Here can use a generic asseration wrapper function for generic ones later
    
    exec_report = fix_client.wait_for_execution_report(
        cl_ord_id, expected_status=fix.OrdStatus_NEW
    )
    assert exec_report is not None
    assert exec_report.getField(fix.OrdStatus) == fix.OrdStatus_NEW
    assert exec_report.getField(fix.Symbol) == symbol
```
2, Chained Calls for Simple Smoke/Regression Suites:
Provides a concise, readable syntax for common end-to-end workflows (e.g., New Order -> Cancel).

FIX example
```
def test_new_order_single_cancel(fix_checker, security):
    """Test new order single followed by cancel."""
    (FIXOrder(fix_checker,
              symbol=security.symbol,
              side=fix.Side_BUY,
              order_qty=100,
              price=Decimal('100.50'),
              ord_type=fix.OrdType_LIMIT)
     .new_order_single()
     .verify()
     .cancel()
     .verify())
```

Which to choose? Use AAA for unique, complex scenarios. Use chained calls for common, repetitive regression tests.

Phase II: Proposed Future Enhancements

*   Cover More Scenarios: Expand coverage to complex, hard-to-test-manually scenarios 
(e.g., session management, unconfirmed scenarios).

*   Implement Latency Measurement: Integrate performance profiling using multithreading/asyncio for synthetic load and 
custom drop copy passthrough tags for granular analysis. (Need further discussion with Dev/Devops team for specific
method, can also use internal binary logs, PCAP analysis or third party vendor solutions)

*   Build a Recording/Replay Proxy: Develop a proxy to record and replay real exchange responses between the EMS and venues,
reducing simulator dependency and increasing test realism. 
(Note: Requires re-recording if exchange specifications change.)

*   CI/CD Integration: Fully integrate the automated test suite into a continuous integration and delivery pipeline to 
enforce quality gates throughout the development lifecycle.
