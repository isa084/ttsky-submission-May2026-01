"""Top-level cocotb test aggregator.

Import feature-specific verification modules so their @cocotb.test()
decorated tests are registered under the single `test` module referenced
by the Tiny Tapeout Makefile.
"""

from verification.test_reset_behavior import *  # noqa: F401,F403
from verification.test_direct_overrides import *  # noqa: F401,F403
from verification.test_failsafe_mode import *  # noqa: F401,F403
from verification.test_integration_flows import *  # noqa: F401,F403
from verification.test_interface_contract import *  # noqa: F401,F403
from verification.test_sweep_mode import *  # noqa: F401,F403
from verification.test_uart_commands import *  # noqa: F401,F403
