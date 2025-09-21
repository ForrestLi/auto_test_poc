This repository contains a proof-of-concept (PoC) for an automated testing framework designed for integration testing of 
electronic trading systems. The framework validates systems communicating via the FIX protocol or other binary protocols
(e.g. AHD).

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
        ems=ems,
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
Provides a concise, readable syntax for common end-to-end workflows (e.g., New Order -> Modify Price -> Cancel).

FIX example
```
def test_new_order_single_cancel(fix_checker, security):
    """Test new order single followed by cancel."""
    (Order(checker, security=security, side="S", orderQty=100, orderPrice=10.0)
        .ordered(orderID=order_id)
        .verify()
        .modify(orderPrice=11.0)
        .modified()
        .verify()
        .cancel()
        .canceled()
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

Talk is easy, time to show some basic implementations.

## Project Structure

This repository is organized to separate reusable protocol utilities from sample PoC code and unit tests. A quick tour:

- `common/`
  - Core, protocol-agnostic testing utilities and data structures.
  - `test_utils.py`: Defines the base `Order` model and `GenericChecker`, including camelCase and snake_case 
  compatibility for arguments and method aliases for backward compatibility.
  - `fix_msg.py`: Minimal FIX message builders/parsers for core messages 
  (e.g., `NewOrderSingle`, `ExecutionReport`).
  - `fix_cli.py`: 
  A simple FIX client wrapper that can connect, logon, send messages, and receive responses.
  - `fix_utils.py`: `FIXClientChecker` that validates outgoing FIX messages and incoming execution reports. 
  Accepts `exchange_sim` (or in short `mxsim`) for simulated fills.
  - `ahd_msg.py`, `ahd_cli.py`, `ahd_utils.py`: Analogous utilities for an AHD-style binary protocol (PoC level).

- `test/`
  - Self-contained unit tests that do not require external systems.
  - `test_order_and_checker.py`: Validates `Order` behavior 
  (constructor aliases, state transitions, fills, delta modify semantics).
  - `test_fix_client_checker.py`: Validates `FIXClientChecker` initialization.

- `fix_poc/`
  - PoC and tools for FIX-based testing and performance experiments.
  - `stress_fix_multithread.py`: Multithreaded stress sender using `common.fix_cli.FixClient`.
    - Options include threads, messages per thread, per-thread rate limiting, pandas-based per-thread summaries, 
    - CSV export, and optional latency measurement via `ExecutionReport` 
    - matching with sampling (`--latency-sample-every`).
  - `stress_fix_asyncio.py`: 
     AsyncIO variant with connection-level concurrency and the same metrics/sampling options.
  - `fix_server_asyncio.py`: 
    Simple asyncio FIX 4.4 test server wrote for this POC that accepts Logon, Heartbeat/TestRequest, 
    and responds to NewOrderSingle with `ExecutionReport` NEW; with `--auto-fill`, 
    it immediately sends a FILLED report as well.

- `ahd_poc/`
  - Placeholder PoC scaffolding for AHD protocol experiments. Some examples may rely on external simulators/services.

- Project metadata
  - `pyproject.toml`: Poetry configuration and dependencies. 
  - `pytest.ini`: Limits test discovery to the `test/` directory
  - `conftest.py` (repo root): Ensures the project root is importable when running tests.

### Running Unit Tests

From the repository root, run:

```bash
pytest -q
```

or with more debugging info

```bash
pytest -v
```


Only the `test/` directory is collected by default. PoC tools in `fix_poc/` and `ahd_poc/` 
are not part of the unit test run.

### Running FIX Stress Tools (PoC)

- Multithreaded:

```bash
python .\fix_poc\stress_fix_multithread.py --host 127.0.0.1 --port 9876 \
 --sender CLIENT1 --target SERVER \
 --threads 8 --messages-per-thread 2000 --rate 200 \
 --symbol AAPL --side 1 --qty 100 --price 100.25 --heartbeat 30 \
 --measure-latency --ack-timeout 5 --latency-sample-every 10 \
 --csv mt_run.csv --tag mt-sample
```

- AsyncIO-based:

```bash
python .\fix_poc\stress_fix_asyncio.py --host 127.0.0.1 --port 9876 \
 --sender CLIENT1 --target SERVER \
 --concurrency 16 --messages-per-conn 2000 --rate 200 \
 --symbol AAPL --side 1 --qty 100 --price 100.25 --heartbeat 30 \
 --measure-latency --ack-timeout 5 --latency-sample-every 10 \
 --csv aio_run.csv --tag aio-sample
```

### Running the Local FIX Test Server (PoC)

To test clients locally without a venue, start the simple asyncio FIX server:

```bash
python .\fix_poc\fix_server_asyncio.py --host 127.0.0.1 --port 9876 --comp-id SERVER --auto-fill --log-level INFO
```

Then point the stress tools at `--target SERVER` and the same host/port as above.

Both tools compute per-thread/per-connection send-rate statistics and can optionally measure end-to-end ack latencies 
by matching `ExecutionReport` (35=8) with `ClOrdID` (11). 
Sampling reduces overhead while providing representative latency percentiles.
