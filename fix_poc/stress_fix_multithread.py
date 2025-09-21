import argparse
import logging
import threading
import time
import uuid
from typing import Dict, Optional, List

import sys
from pathlib import Path

# Ensure repository root is on sys.path when running this file directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from common.fix_cli import FixClient
from common.fix_msg import NewOrderSingleMessage, Side, Field


def build_new_order_single(
    cl_ord_id: str,
    symbol: str,
    side: str,
    order_qty: int,
    price: Optional[float] = None,
) -> Dict[str, str]:
    """
    Build a NewOrderSingle using common.fix_msg and return a tag->value dict suitable
    for FixClient.send_message(). Header fields (8/49/56/34/52) and 10 are handled by FixClient.
    """
    nos = NewOrderSingleMessage()
    # Explicitly set message type into fields
    nos.set_field(Field.MSG_TYPE, "D")
    nos.set_cl_ord_id(cl_ord_id)
    nos.set_symbol(symbol)
    nos.set_side(Side.BUY if side == "1" else Side.SELL)
    # In fix_msg OrderQty setter expects float, we cast to int/str via set_field semantics
    nos.set_field(Field.ORDER_QTY, str(order_qty))
    if price is not None:
        nos.set_price(price)

    # Convert internal fields (int keys) to string keys
    return {str(tag): value for tag, value in nos.fields.items()}


def worker(
    worker_id: int,
    host: str,
    port: int,
    sender_comp_id: str,
    target_comp_id: str,
    messages: int,
    symbol: str,
    side: str,
    order_qty: int,
    price: Optional[float],
    rate_per_sec: float,
    heartbeat_interval: int,
    connect_timeout_sec: float = 10.0,
    results: Optional[List[Dict]] = None,
    measure_latency: bool = False,
    ack_timeout_s: float = 5.0,
    latencies_out: Optional[List[float]] = None,
    latency_sample_every: int = 1,
):
    logger = logging.getLogger(f"stress.worker.{worker_id}")

    client = FixClient(
        host=host,
        port=port,
        sender_comp_id=sender_comp_id,
        target_comp_id=target_comp_id,
        heartbeat_interval=heartbeat_interval,
    )

    start_ts = time.time()
    sent = 0
    first_send_ts = None
    last_send_ts = None
    latencies: List[float] = []

    try:
        client.connect()
        logger.info("connected")

        # pacing
        sleep_between = 0.0
        if rate_per_sec > 0:
            sleep_between = 1.0 / rate_per_sec

        for i in range(messages):
            # Unique ClOrdID per message
            cl_id = f"{sender_comp_id}-{worker_id}-{i}-{uuid.uuid4().hex[:8]}"
            nos = build_new_order_single(cl_id, symbol, side, order_qty, price)
            send_ts = time.time()
            client.send_message(nos)
            now = time.time()
            if first_send_ts is None:
                first_send_ts = now
            last_send_ts = now
            sent += 1

            should_sample = measure_latency and (latency_sample_every >= 1) and (
                (i % latency_sample_every) == 0
            )
            if should_sample:
                # Read until we find ExecReport with our ClOrdID or until timeout
                deadline = time.monotonic() + ack_timeout_s
                while time.monotonic() < deadline:
                    msg = client.receive_message(timeout=0.2)
                    if not msg:
                        continue
                    # Expect ExecutionReport (35=8) and ClOrdID match (11)
                    if msg.get("35") == "8" and msg.get("11") == cl_id:
                        latencies.append(time.time() - send_ts)
                        break
                # If not found, we skip recording latency for this message

            if sleep_between > 0:
                time.sleep(sleep_between)

        logger.info("completed sends: %s", messages)

    except Exception as e:
        logger.exception("worker %s error: %s", worker_id, e)
    finally:
        try:
            client.disconnect()
        except Exception:
            pass
        end_ts = time.time()
        elapsed = max(end_ts - start_ts, 1e-9)
        rate = sent / elapsed
        logger.info("disconnected")

        if results is not None:
            row = {
                "worker_id": worker_id,
                "sent": sent,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "elapsed_s": elapsed,
                "rate_msg_per_s": rate,
                "first_send_ts": first_send_ts,
                "last_send_ts": last_send_ts,
            }
            if latencies:
                import statistics as stats

                row.update(
                    {
                        "latency_count": len(latencies),
                        "latency_mean_ms": 1000.0 * (sum(latencies) / len(latencies)),
                        # per-thread percentiles may be noisy; compute anyway for reference
                        "latency_p50_ms": 1000.0 * float(pd.Series(latencies).quantile(0.5)),
                        "latency_p90_ms": 1000.0 * float(pd.Series(latencies).quantile(0.9)),
                        "latency_p99_ms": 1000.0 * float(pd.Series(latencies).quantile(0.99)),
                    }
                )
            results.append(row)

        if latencies_out is not None and latencies:
            latencies_out.extend(latencies)


def main():
    parser = argparse.ArgumentParser(
        description="Multithreaded FIX stress sender using common.fix_cli.FixClient",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Connection / Session
    parser.add_argument("--host", required=True, help="FIX server host")
    parser.add_argument("--port", type=int, required=True, help="FIX server port")
    parser.add_argument("--sender", required=True, help="SenderCompID (49)")
    parser.add_argument("--target", required=True, help="TargetCompID (56)")
    parser.add_argument("--heartbeat", type=int, default=30, help="HeartBtInt (108)")

    # Load shape
    parser.add_argument("--threads", type=int, default=4, help="Number of sender threads")
    parser.add_argument(
        "--messages-per-thread",
        type=int,
        default=100,
        help="Number of messages each thread should send",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=50.0,
        help="Target send rate per thread (messages/second). Use 0 for max speed",
    )

    # Order fields
    parser.add_argument("--symbol", default="AAPL", help="Symbol (55)")
    parser.add_argument(
        "--side",
        choices=["1", "2"],
        default="1",
        help="Side: 1=Buy, 2=Sell (54)",
    )
    parser.add_argument("--qty", type=int, default=100, help="OrderQty (38)")
    parser.add_argument("--price", type=float, default=None, help="Price (44), optional")

    # Logging
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="Optional path to write per-thread statistics as CSV",
    )
    parser.add_argument(
        "--tag",
        default=None,
        help="Optional tag to include in CSV summary for traceability",
    )
    parser.add_argument(
        "--measure-latency",
        action="store_true",
        help="Measure ack latency by waiting for ExecutionReport per message",
    )
    parser.add_argument(
        "--ack-timeout",
        type=float,
        default=5.0,
        help="Timeout in seconds to wait for an ExecutionReport per message when measuring latency",
    )
    parser.add_argument(
        "--latency-sample-every",
        type=int,
        default=1,
        help="Measure latency for 1 in N orders per thread (e.g., 10 measures ~10%%)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    )

    threads: List[threading.Thread] = []
    results: List[Dict] = []
    latencies_all: List[float] = []
    start_ts = time.time()

    for t in range(args.threads):
        th = threading.Thread(
            target=worker,
            kwargs=dict(
                worker_id=t,
                host=args.host,
                port=args.port,
                sender_comp_id=args.sender,
                target_comp_id=args.target,
                messages=args.messages_per_thread,
                symbol=args.symbol,
                side=args.side,
                order_qty=args.qty,
                price=args.price,
                rate_per_sec=args.rate,
                heartbeat_interval=args.heartbeat,
                results=results,
                measure_latency=args.measure_latency,
                ack_timeout_s=args.ack_timeout,
                latencies_out=latencies_all,
                latency_sample_every=max(1, args.latency_sample_every),
            ),
            daemon=True,
            name=f"stress-worker-{t}",
        )
        th.start()
        threads.append(th)

    for th in threads:
        th.join()

    elapsed = time.time() - start_ts
    total_msgs = args.threads * args.messages_per_thread
    overall_rate = total_msgs / elapsed if elapsed > 0 else float("inf")

    # Build pandas DataFrame and print summary
    df = pd.DataFrame(results)
    if not df.empty:
        df_sorted = df.sort_values("worker_id")
        summary = df_sorted[["sent", "elapsed_s", "rate_msg_per_s"]].describe()
        logging.getLogger("stress").info(
            "\nPer-thread stats (first 10 rows):\n%s\n\nSummary describe():\n%s",
            df_sorted.head(10).to_string(index=False),
            summary.to_string(),
        )
        # Percentiles of per-thread rates
        rates = df_sorted["rate_msg_per_s"].values
        rate_p50 = float(pd.Series(rates).quantile(0.5))
        rate_p90 = float(pd.Series(rates).quantile(0.9))
        rate_p99 = float(pd.Series(rates).quantile(0.99))
        logging.getLogger("stress").info(
            "Per-thread rate percentiles msg/s: p50=%.2f p90=%.2f p99=%.2f",
            rate_p50,
            rate_p90,
            rate_p99,
        )
        # Overall latency percentiles (if measured)
        if latencies_all:
            ser = pd.Series(latencies_all) * 1000.0
            lp50 = float(ser.quantile(0.5))
            lp90 = float(ser.quantile(0.9))
            lp99 = float(ser.quantile(0.99))
            lavg = float(ser.mean())
            logging.getLogger("stress").info(
                "Ack latency ms: mean=%.2f p50=%.2f p90=%.2f p99=%.2f (samples=%d)",
                lavg,
                lp50,
                lp90,
                lp99,
                len(latencies_all),
            )
    else:
        logging.getLogger("stress").warning("No per-thread results collected")

    logging.getLogger("stress").info(
        "completed: threads=%s total_msgs=%s elapsed=%.3fs overall_rate=%.2f msg/s",
        args.threads,
        total_msgs,
        elapsed,
        overall_rate,
    )

    if args.csv:
        # Add run-level metadata columns
        df["threads"] = args.threads
        df["messages_per_thread"] = args.messages_per_thread
        df["symbol"] = args.symbol
        df["side"] = args.side
        df["qty"] = args.qty
        df["price"] = args.price
        df["target"] = args.target
        df["sender"] = args.sender
        df["heartbeat"] = args.heartbeat
        df["tag"] = args.tag
        df["run_elapsed_s"] = elapsed
        df["run_overall_rate_msg_per_s"] = overall_rate
        # If latency measured, add overall percentiles for convenience
        if latencies_all:
            ser = pd.Series(latencies_all) * 1000.0
            df["lat_overall_mean_ms"] = float(ser.mean())
            df["lat_overall_p50_ms"] = float(ser.quantile(0.5))
            df["lat_overall_p90_ms"] = float(ser.quantile(0.9))
            df["lat_overall_p99_ms"] = float(ser.quantile(0.99))

        df.to_csv(args.csv, index=False)
        logging.getLogger("stress").info("wrote CSV: %s (rows=%d)", args.csv, len(df))


if __name__ == "__main__":
    main()
