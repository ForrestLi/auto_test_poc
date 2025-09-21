import pytest
from overrides import overrides

from common import fix_cli
from common.fix_utils import FIXClientChecker
from common.test_utils import Order

# Register assertion rewrite for multiple modules
# ems stands for the eletronic management systems e.g. algo execution & market access gateway systems
pytest.register_assert_rewrite(
    "ems_utils",
    "hamcrest_utils",
    "test_utils",
    "fix_cli",
    "fix_msg",
    "fix_utils",
)


class FIXChecker(FIXClientChecker):
    pass


@pytest.fixture
def checker(request, ems, securities, mxsim, fix_cli):
    """Provides default checker object."""
    return FIXChecker(
        ems=ems,
        securities=securities,
        mxsim=mxsim,
        client=request.config.getini("fix_cli"),
        fix_client=fix_cli,
    ).reset()
