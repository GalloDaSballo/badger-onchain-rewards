import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

"""
 Set of tests that compare
 `claimRewardReference`
 with
 `claimReward`

 Showing the equivalence of them

 - Same token claimed amount
 - Same point from `points` (storage) vs `getUserNextEpochInfo`
"""

"""
  TODO:
  Same for totalPoints vs `getTotalSupplyAtEpoch`
"""

def test_equivalence_points_reference_and_getUserNextEpochInfo(initialized_contract, user, fake_vault, token):

  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()


  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = token.balanceOf(user)

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Snapshot so we can revert
  chain.snapshot()

  ## Claim rewards here
  tx = initialized_contract.claimRewardReference(EPOCH, fake_vault, token, user)

  final_balance_reference = token.balanceOf(user)
  expected_final_balance = initial_reward_balance + REWARD_AMOUNT

  ## Verify you got the entire amount
  assert final_balance_reference == expected_final_balance
  
  
  final_points_reference = initialized_contract.points(EPOCH, fake_vault, user)
  final_total_points_reference = initialized_contract.totalPoints(EPOCH, fake_vault)

  ## Check balances at end are same
  chain.revert()

  tx = initialized_contract.claimRewardReference(EPOCH, fake_vault, token, user)

  assert token.balanceOf(user) == expected_final_balance
  assert token.balanceOf(user) == final_balance_reference

  ## Compare final_points_reference with points from estimation function
  balance = initialized_contract.getBalanceAtEpoch(EPOCH, fake_vault, user)[0]
  total_supply = initialized_contract.getTotalSupplyAtEpoch(EPOCH, fake_vault)[0]

  expected = initialized_contract.getUserNextEpochInfo(EPOCH, fake_vault, user, balance)
  expected_points = expected[2]

  expected_vault = initialized_contract.getVaultNextEpochInfo(EPOCH, fake_vault, balance)
  expected_total_points = expected_vault[2]

  ## Math is equivalent
  assert expected_points == final_points_reference
  assert final_total_points_reference == expected_total_points



