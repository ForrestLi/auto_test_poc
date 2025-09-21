import argparse
import asyncio
import logging
import time
import uuid
from typing import Dict, Optional, List, Tuple

import sys
from pathlib import Path
import contextlib

# Ensure repository root is on sys.path when running this file directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from common.fix_msg import NewOrderSingleMessage, Side, Field

SOH = "\x01"
SOH_b = b"\x01"


def build_new_order_single(
    cl_ord_id: str,
    symbol: str,
    side: str,
    order_qty: int,
    price: Optional[float] = None,
) -> Dict[str, str]:
    """Build a NewOrderSingle using common.fix_msg and return tag->value dict."""
    nos = NewOrderSingleMessage()
    nos.set_field(Field.MSG_TYPE, "D")
    nos.set_cl_ord_id(cl_ord_id)
    nos.set_symbol(symbol)
    nos.set_side(Side.BUY if side == "1" else Side.SELL)
    nos.set_field(Field.ORDER_QTY, str(order_qty))
    if price is not None:
        nos.set_price(price)
    return {str(tag): value for tag, value in nos.fields.items()}


class AsyncFixClient:
    def __init__(
        self,
        host: str,
        port: int,
        sender_comp_id: str,
        target_comp_id: str,
        heartbeat_interval: int = 30,
        begin_string: str = "FIX.4.4",
    ) -> None:
        self.host = host
        self.port = port
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.heartbeat_interval = heartbeat_interval
        self.begin_string = begin_string

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._recv_task: Optional[asyncio.Task] = None
        self._in_queue: asyncio.Queue[str] = asyncio.Queue()
        self._stop = asyncio.Event()
        self._out_seq = 1

    async def connect(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
        self._stop.clear()
        self._recv_task = asyncio.create_task(self._recv_loop(), name="fix-recv-loop")
        await self.logon()

    async def disconnect(self) -> None:
        self._stop.set()
        if self._recv_task:
            self._recv_task.cancel()
            with contextlib.suppress(Exception):
                await self._recv_task
        if self._writer:
            with contextlib.suppress(Exception):
                self._writer.close()
                await self._writer.wait_closed()
        self._reader = None
        self._writer = None

    async def logon(self) -> None:
        msg = {
            "35": "A",  # Logon
            "98": "0",  # EncryptMethod=None
            "108": str(self.heartbeat_interval),  # HeartBtInt
        }
        await self.send_message(msg)

    async def send_message(self, msg: Dict[str, str]) -> None:
        # add header defaults
        if "8" not in msg:
            msg["8"] = self.begin_string
        if "49" not in msg:
            msg["49"] = self.sender_comp_id
        if "56" not in msg:
            msg["56"] = self.target_comp_id
        if "34" not in msg:
            msg["34"] = str(self._out_seq)
            self._out_seq += 1
        if "52" not in msg:
            msg["52"] = time.strftime("%Y%m%d-%H:%M:%S", time.gmtime())

        fix_str = self._dict_to_fix(msg)
        if not self._writer:
            raise RuntimeError("Not connected")
        self._writer.write(fix_str.encode("ascii"))
        await self._writer.drain()

    async def receive_message(self, timeout: Optional[float] = None) -> Optional[Dict[str, str]]:
        try:
            raw = await asyncio.wait_for(self._in_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
        return self._fix_to_dict(raw)

    async def _recv_loop(self) -> None:
        buffer = b""
        try:
            assert self._reader is not None
            while not self._stop.is_set():
                chunk = await self._reader.read(4096)
                if not chunk:
                    break
                buffer += chunk
                # extract complete messages by scanning for 10=xxx<SOH>
                msgs, buffer = self._extract_complete_messages(buffer)
                for raw in msgs:
                    await self._in_queue.put(raw)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.getLogger("fix-async").error("recv loop error: %s", e)

    @staticmethod
    def _extract_complete_messages(buffer: bytes) -> Tuple[List[str], bytes]:
        messages: List[str] = []
        start = 0
        while True:
            idx = buffer.find(b"10=", start)
            if idx == -1:
                break
            end = buffer.find(SOH_b, idx)
            if end == -1:
                break
            # end now at end of checksum field; include SOH
            msg_bytes = buffer[: end + 1]
            # naive validation: ensure begins with 8=
            if not msg_bytes.startswith(b"8="):
                # drop up to checksum and continue
                buffer = buffer[end + 1 :]
                start = 0
                continue
            messages.append(msg_bytes.decode("ascii", errors="ignore"))
            buffer = buffer[end + 1 :]
            start = 0
        return messages, buffer

    @staticmethod
    def _dict_to_fix(message: Dict[str, str]) -> str:
        # Remove BodyLength and CheckSum if present
        message.pop("9", None)
        message.pop("10", None)
        # Sort tags except 8/9/10 special handling
        pairs = [(int(k), v) for k, v in message.items() if k not in {"8", "9", "10"}]
        pairs.sort(key=lambda x: x[0])
        parts = [f"8={message['8']}"] + [f"{k}={v}" for k, v in pairs]
        body = SOH.join(parts) + SOH
        body_length = len(body)
        fix_msg = f"8={message['8']}" + SOH + f"9={body_length}" + SOH + SOH.join(parts[1:]) + SOH
        checksum = sum(fix_msg.encode("ascii")) % 256
        fix_msg += f"10={checksum:03d}" + SOH
        return fix_msg

    @staticmethod
    def _fix_to_dict(fix_str: str) -> Dict[str, str]:
        if fix_str.endswith(SOH):
            fix_str = fix_str[:-1]
        d: Dict[str, str] = {}
        for kv in fix_str.split(SOH):
            if "=" in kv:
                k, v = kv.split("=", 1)
                d[k] = v
        return d


async def worker(
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
    results: List[Dict],
    measure_latency: bool,
    ack_timeout_s: float,
    latency_sample_every: int,
) -> None:
    logger = logging.getLogger(f"stress.async.worker.{worker_id}")
    client = AsyncFixClient(
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
        await client.connect()
        logger.info("connected")

        sleep_between = 0.0 if rate_per_sec <= 0 else 1.0 / rate_per_sec

        for i in range(messages):
            cl_id = f"{sender_comp_id}-{worker_id}-{i}-{uuid.uuid4().hex[:8]}"
            nos = build_new_order_single(cl_id, symbol, side, order_qty, price)
            send_ts = time.time()
            await client.send_message(nos)
            now = time.time()
            if first_send_ts is None:
                first_send_ts = now
            last_send_ts = now
            sent += 1

            should_sample = measure_latency and (latency_sample_every >= 1) and (
                (i % latency_sample_every) == 0
            )
            if should_sample:
                deadline = asyncio.get_event_loop().time() + ack_timeout_s
                while True:
                    timeout = max(0.0, deadline - asyncio.get_event_loop().time())
                    if timeout <= 0:
                        break
                    msg = await client.receive_message(timeout=min(0.2, timeout))
                    if not msg:
                        continue
                    if msg.get("35") == "8" and msg.get("11") == cl_id:
                        latencies.append(time.time() - send_ts)
                        break

            if sleep_between > 0:
                await asyncio.sleep(sleep_between)

        logger.info("completed sends: %s", messages)

    except Exception as e:
        logger.exception("worker %s error: %s", worker_id, e)
    finally:
        with contextlib.suppress(Exception):
            await client.disconnect()
        end_ts = time.time()
        elapsed = max(end_ts - start_ts, 1e-9)
        rate = sent / elapsed
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
            ser = pd.Series(latencies)
            row.update(
                {
                    "latency_count": int(ser.size),
                    "latency_mean_ms": float(ser.mean() * 1000.0),
                    "latency_p50_ms": float(ser.quantile(0.5) * 1000.0),
                    "latency_p90_ms": float(ser.quantile(0.9) * 1000.0),
                    "latency_p99_ms": float(ser.quantile(0.99) * 1000.0),
                }
            )
        results.append(row)


async def amain(args) -> None:
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    )

    results: List[Dict] = []
    tasks: List[asyncio.Task] = []
    start_ts = time.time()

    for w in range(args.concurrency):
        t = asyncio.create_task(
            worker(
                worker_id=w,
                host=args.host,
                port=args.port,
                sender_comp_id=args.sender,
                target_comp_id=args.target,
                messages=args.messages_per_conn,
                symbol=args.symbol,
                side=args.side,
                order_qty=args.qty,
                price=args.price,
                rate_per_sec=args.rate,
                heartbeat_interval=args.heartbeat,
                results=results,
                measure_latency=args.measure_latency,
                ack_timeout_s=args.ack_timeout,
                latency_sample_every=max(1, args.latency_sample_every),
            )
        )
        tasks.append(t)

    await asyncio.gather(*tasks)

    elapsed = time.time() - start_ts
    total_msgs = args.concurrency * args.messages_per_conn
    overall_rate = total_msgs / elapsed if elapsed > 0 else float("inf")

    df = pd.DataFrame(results)
    if not df.empty:
        df_sorted = df.sort_values("worker_id")
        summary = df_sorted[["sent", "elapsed_s", "rate_msg_per_s"]].describe()
        logging.getLogger("stress.async").info(
            "\nPer-conn stats (first 10 rows):\n%s\n\nSummary describe():\n%s",
            df_sorted.head(10).to_string(index=False),
            summary.to_string(),
        )
        rates = df_sorted["rate_msg_per_s"].values
        rate_p50 = float(pd.Series(rates).quantile(0.5))
        rate_p90 = float(pd.Series(rates).quantile(0.9))
        rate_p99 = float(pd.Series(rates).quantile(0.99))
        logging.getLogger("stress.async").info(
            "Per-conn rate percentiles msg/s: p50=%.2f p90=%.2f p99=%.2f",
            rate_p50,
            rate_p90,
            rate_p99,
        )
        lat_cols = [c for c in df.columns if c.startswith("latency_")]
        if lat_cols:
            all_lat = []
            for _, r in df.iterrows():
                # we only persisted aggregate per-conn stats; so compute overall from values if available
                pass
            # note: for a full combined percentile across all samples, we would need raw samples; to minimize memory
            # we provide per-conn p50/p90/p99 above. If you want global percentiles of raw samples, we can add a
            # --latency-save-samples option to persist them.
    else:
        logging.getLogger("stress.async").warning("No per-conn results collected")

    logging.getLogger("stress.async").info(
        "completed: concurrency=%s total_msgs=%s elapsed=%.3fs overall_rate=%.2f msg/s",
        args.concurrency,
        total_msgs,
        elapsed,
        overall_rate,
    )

    if args.csv:
        df["concurrency"] = args.concurrency
        df["messages_per_conn"] = args.messages_per_conn
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
        df.to_csv(args.csv, index=False)
        logging.getLogger("stress.async").info("wrote CSV: %s (rows=%d)", args.csv, len(df))


def main():
    parser = argparse.ArgumentParser(
        description="AsyncIO FIX stress/latency sender (per-connection concurrency)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", required=True, help="FIX server host")
    parser.add_argument("--port", type=int, required=True, help="FIX server port")
    parser.add_argument("--sender", required=True, help="SenderCompID (49)")
    parser.add_argument("--target", required=True, help="TargetCompID (56)")
    parser.add_argument("--heartbeat", type=int, default=30, help="HeartBtInt (108)")

    parser.add_argument("--concurrency", type=int, default=8, help="Number of parallel FIX connections")
    parser.add_argument("--messages-per-conn", type=int, default=1000, help="Messages per connection")
    parser.add_argument("--rate", type=float, default=100.0, help="Target send rate per connection (msg/s). 0 for max speed")

    parser.add_argument("--symbol", default="AAPL", help="Symbol (55)")
    parser.add_argument("--side", choices=["1", "2"], default="1", help="Side (54): 1=Buy, 2=Sell")
    parser.add_argument("--qty", type=int, default=100, help="OrderQty (38)")
    parser.add_argument("--price", type=float, default=None, help="Price (44), optional")

    parser.add_argument("--measure-latency", action="store_true", help="Measure ack latency by waiting for ExecutionReport per order")
    parser.add_argument("--ack-timeout", type=float, default=5.0, help="Timeout in seconds to wait for an ExecutionReport per message")
    parser.add_argument("--latency-sample-every", type=int, default=1, help="Measure latency for 1 in N orders per connection")

    parser.add_argument("--csv", default=None, help="Optional path to write per-connection statistics as CSV")
    parser.add_argument("--tag", default=None, help="Optional tag to include in CSV for traceability")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Logging level")

    args = parser.parse_args()
    asyncio.run(amain(args))


if __name__ == "__main__":
    import contextlib
    main()
