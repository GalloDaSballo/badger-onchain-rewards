import brownie
from brownie import *

AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

"""
  Checks that rewards are properly set via `addReward` and `addRewards`
"""

def test_basic_add_reward(initialized_contract, user, fake_vault, token):
  REWARD_AMOUNT = 1e18
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(1, fake_vault, token, REWARD_AMOUNT, {"from": user})

  assert initialized_contract.rewards(1, fake_vault, token) == REWARD_AMOUNT
  assert initialized_contract.rewards(1, fake_vault, AddressZero) == 0 ## Only added to token index

  SECOND_REWARD_AMOUNT = 16e19

  initialized_contract.addReward(1, fake_vault, token, SECOND_REWARD_AMOUNT, {"from": user})

  assert initialized_contract.rewards(1, fake_vault, token) == REWARD_AMOUNT + SECOND_REWARD_AMOUNT

def test_basic_add_multiple_rewards(initialized_contract, user, fake_vault, token):
  REWARD_AMOUNT = 1e18
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addRewards([1], [fake_vault], [token], [REWARD_AMOUNT], {"from": user})

  assert initialized_contract.rewards(1, fake_vault, token) == REWARD_AMOUNT

  ## You can add more than once
  initialized_contract.addRewards([1, 2], [fake_vault, fake_vault], [token, token], [REWARD_AMOUNT, REWARD_AMOUNT], {"from": user})
  assert initialized_contract.rewards(1, fake_vault, token) == REWARD_AMOUNT + REWARD_AMOUNT ## We added one more
  assert initialized_contract.rewards(2, fake_vault, token) == REWARD_AMOUNT


def test_must_have_balance_to_add(initialized_contract, user, fake_vault, wbtc):
  wbtc.approve(initialized_contract, MaxUint256, {"from": user})

  ## We have no wbtc, so this fails
  with brownie.reverts():
    initialized_contract.addReward(2, wbtc, fake_vault, 1000, {"from": user})


def test_cant_add_rewards_in_the_past(initialized_contract, user, fake_vault, token):
  """
    Revert test for rewards in past epochs
  """
  REWARD_AMOUNT = 1e18
  token.approve(initialized_contract, MaxUint256, {"from": user})

  with brownie.reverts():
    initialized_contract.addReward(0, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  with brownie.reverts():
    initialized_contract.addReward(1, fake_vault, token, REWARD_AMOUNT, {"from": user})


def test_add_rewards_reverts_on_length_mismatch(initialized_contract, user, fake_vault, token):
  """
    Revert test for mistmatch length rewards
  """
  REWARD_AMOUNT = 1e18
  token.approve(initialized_contract, MaxUint256, {"from": user})

  ## 2 epochs, 1 rest
  with brownie.reverts("dev: length mismatch"):
    initialized_contract.addRewards([0, 0], [fake_vault], [token], [REWARD_AMOUNT], {"from": user})

  ## 2 vaults, 1 rest
  with brownie.reverts("dev: length mismatch"):
    initialized_contract.addRewards([0], [fake_vault], [token, token], [REWARD_AMOUNT], {"from": user})
  
  ## 2 tokens 1 rest
  with brownie.reverts("dev: length mismatch"):
    initialized_contract.addRewards([0], [fake_vault, fake_vault], [token], [REWARD_AMOUNT], {"from": user})
  
  ## 2 rewards 1 rest
  with brownie.reverts("dev: length mismatch"):
    initialized_contract.addRewards([0], [fake_vault], [token], [REWARD_AMOUNT, REWARD_AMOUNT], {"from": user})
