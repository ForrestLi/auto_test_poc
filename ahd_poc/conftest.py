import pytest
from overrides import overrides
from common.ahd_utils import AHDClientChecker

# Register assertion rewrite for multiple modules
# ems stands for the eletronic management systems e.g. algo execution & market access gateway systems
pytest.register_assert_rewrite(
    "ems_utils",
    "hamcrest_utils",
    "remote_utils",
    "test_utils",
    "latency_utils",
    "ahd_client",
    "ahd_msg",
    "ahd_utils",
)


class AHDRawClOrdIDAdjustedClientChecker(AHDClientChecker):
    @overrides
    def expectedInternalProcessing(self, kwargs, order):
        return kwargs.get("destClOrdID", order.destClOrdID if order else None)

    @overrides
    def kwargsFromNewOrder(self, kwargs, msg):
        kwargs["destClOrdID"] = msg.InternalProcessing
        if "clOrdID" not in kwargs:
            order_common = msg[self.ahd_client.ahd_msg.OrderCommonO]
            kwargs["clOrdID"] = (
                f"{order_common.VirtualServerNo}" f"{order_common.OrderEntrySeqNo:08d}"
            )


class AHDChecker(AHDRawClOrdIDAdjustedClientChecker):
    pass


@pytest.fixture
def checker(request, ems, securities, mxsim, ahd_client):
    """Provides default checker object."""
    return AHDChecker(
        ems=ems,
        securities=securities,
        mxsim=mxsim,
        client=request.config.getini("ahd_client"),
        account=request.config.getini("ahd_account"),
        ahd_client=ahd_client,
    ).reset()
