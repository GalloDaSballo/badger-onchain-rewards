from multiprocessing.pool import INIT
import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))


"""
  Weird tests to get 100% Coverage
"""

def test_zero_balance_epoch_two(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18

  advanceTime = initialized_contract.SECONDS_PER_EPOCH() + 1
  chain.sleep(advanceTime * 3)
  chain.mine()

  ## Check we have zero balance
  assert initialized_contract.getBalanceAtEpoch(2, fake_vault, user)[0] == 0
  ## Check we have zero totalSupply
  assert initialized_contract.getTotalSupplyAtEpoch(2, fake_vault)[0] == 0

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## Check we have zero balance for old epochs
  assert initialized_contract.getBalanceAtEpoch(2, fake_vault, user)[0] == 0
  ## Check we have zero totalSupply for old epochs
  assert initialized_contract.getTotalSupplyAtEpoch(2, fake_vault)[0] == 0

  ## Check that we have non-zero balance and totalSupply for current
  assert initialized_contract.getBalanceAtEpoch(initialized_contract.currentEpoch(), fake_vault, user)[0] == INITIAL_DEPOSIT
  assert initialized_contract.getTotalSupplyAtEpoch(initialized_contract.currentEpoch(), fake_vault)[0] == INITIAL_DEPOSIT
  
  ## Test revert case: require(epochId <= currentEpoch()); 
  with brownie.reverts():
       initialized_contract.getTotalSupplyAtEpoch(2000, fake_vault)


def test_add_reward_zero_add(initialized_contract, user, fake_vault, token):
  with brownie.reverts():
    initialized_contract.addReward(123, AddressZero, token, 10e18, {"from": user})
  
  with brownie.reverts():
    initialized_contract.addBulkRewardsLinearly(123, 124, AddressZero, token, 10e18, {"from": user})

  with brownie.reverts():
    initialized_contract.addBulkRewards(123, 123, AddressZero, token, [10e18], {"from": user})