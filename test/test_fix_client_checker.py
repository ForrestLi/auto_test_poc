import pytest
from types import SimpleNamespace

from common.fix_utils import FIXClientChecker


class DummyFixClient:
    def __init__(self):
        self.sent = []
        self.received = []

    def sendMsg(self, msg):
        self.sent.append(msg)

    def receiveMsg(self):
        return self.received.pop(0) if self.received else {}


class DummyExchangeSim:
    def __init__(self):
        self.fills = []

    def fill(self, order_id, qty, price):
        self.fills.append((order_id, qty, price))


@pytest.fixture
def fix_client():
    return DummyFixClient()


@pytest.fixture
def exchange_sim():
    return DummyExchangeSim()


def test_init_with_exchange_sim(fix_client, exchange_sim):
    checker = FIXClientChecker(fix_client=fix_client, exchange_sim=exchange_sim)
    assert checker.fix_client is fix_client
    assert checker.exchange_sim is exchange_sim


def test_init_with_mxsim_legacy_key(fix_client, exchange_sim):
    checker = FIXClientChecker(fix_client=fix_client, mxsim=exchange_sim)
    assert checker.exchange_sim is exchange_sim
