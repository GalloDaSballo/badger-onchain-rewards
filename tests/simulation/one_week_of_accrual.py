

import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

""""
  Simulate -> Depositing and claiming for one week
"""

## Benchmark basic one week test
def test_full_deposit_one_week_reference(initialized_contract, user, fake_vault, token):
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

  ## Claim rewards here
  tx = initialized_contract.claimRewardReference(EPOCH, fake_vault, token, user)

  ## Verify you got the entire amount
  assert token.balanceOf(user) == initial_reward_balance + REWARD_AMOUNT

  assert tx.gas_used <= 220_000 ## Run through simulation is 208661

## Benchmark Gas Optimized Basic one week test
def test_full_deposit_one_week(initialized_contract, user, fake_vault, token):
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

  ## Claim rewards here
  tx = initialized_contract.claimReward(EPOCH, fake_vault, token, user)

  ## Verify you got the entire amount
  assert token.balanceOf(user) == initial_reward_balance + REWARD_AMOUNT

  assert tx.gas_used <= 160_000 ## Run through simulation is 153449

## Benchmark Gas Optimized Basic one week test non emitting
def test_full_deposit_one_week_nonEmitting(initialized_contract, user, fake_vault, token):
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

  ## Claim rewards here
  tx = initialized_contract.claimRewardNonEmitting(EPOCH, fake_vault, token, user)

  ## Verify you got the entire amount
  assert token.balanceOf(user) == initial_reward_balance + REWARD_AMOUNT

  assert tx.gas_used <= 150_000 ## Run through simulation is 149563