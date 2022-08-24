import brownie
from brownie import *
from helpers.utils import (
    approx,
)

AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2**256 - 1))

"""
  Tests for QSP-2
  Optimized functions will burn shares if user uses them with 1 epoch range (same epoch start and end)
  -> Post-FIX -> Test Passes because of overflow protection
"""


def test_can_get_rewards_for_zero_due_to_overflow(
    initialized_contract, deployer, fake_vault, token
):
    ## Before fix, no revert, rewards are set, but no tokens are transfered | After fix, reverts
    with brownie.reverts():
        initialized_contract.addBulkRewards(
            3, 4, fake_vault, token, [MaxUint256, 1], {"from": deployer}
        )
