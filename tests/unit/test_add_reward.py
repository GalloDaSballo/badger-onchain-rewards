import brownie
from brownie import *

AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

"""
  Checks that rewards are properly set via `addReward` and `addRewards`
"""

def test_basic_add_reward(initialized_contract, user, fake_vault, token):
  amount = 1e18
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(1, fake_vault, token, amount, {"from": user})

  assert initialized_contract.rewards(1, fake_vault, token) == amount
  assert initialized_contract.rewards(1, fake_vault, AddressZero) == 0 ## Only added to token index

  second_amount = 16e19

  initialized_contract.addReward(1, fake_vault, token, second_amount, {"from": user})

  assert initialized_contract.rewards(1, fake_vault, token) == amount + second_amount

def test_basic_add_multiple_rewards(initialized_contract, user, fake_vault, token):
  amount = 1e18
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addRewards([1], [fake_vault], [token], [amount], {"from": user})

  assert initialized_contract.rewards(1, fake_vault, token) == amount

  ## You can add more than once
  initialized_contract.addRewards([1, 2], [fake_vault, fake_vault], [token, token], [amount, amount], {"from": user})
  assert initialized_contract.rewards(1, fake_vault, token) == amount + amount ## We added one more
  assert initialized_contract.rewards(2, fake_vault, token) == amount


def test_must_have_balance_to_add(initialized_contract, user, fake_vault, wbtc):
  wbtc.approve(initialized_contract, MaxUint256, {"from": user})

  ## We have no wbtc, so this fails
  with brownie.reverts():
    initialized_contract.addReward(2, wbtc, fake_vault, 1000, {"from": user})
