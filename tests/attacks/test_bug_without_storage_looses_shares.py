import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

"""
  Tests for QSP-2
  Optimized functions will burn shares if user uses them with 1 epoch range (same epoch start and end)
  -> TODO: Pre-Fix -> Test fails
  -> Post-FIX -> Test Passes and shares are tracked properly
"""

