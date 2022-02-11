import brownie
from brownie import *

AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

"""
  This file tests 
  `getUserTimeLeftToAccrue`
  and `getVaultTimeLeftToAccrue`
"""

def test_deposit_time_is_last_accrue_time(initialized_contract, user, fake_vault):
  """
    Proof that tx.timestamp is same internally as well, important as the following math is based on time
  """
  INITIAL_DEPOSIT = 1e18
  EPOCH = 1

  deposit_tx = initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})
  time_of_deposit = deposit_tx.timestamp

  assert initialized_contract.lastUserAccrueTimestamp(EPOCH, fake_vault, user) == time_of_deposit



  

def test_if_wait_one_epoch_should_accrue_one_epoch(initialized_contract, user, fake_vault):
  """
    Deposit
    Wait for end of epoch
    Time to accrue is epoh_end - time_of_deposit
  """
  INITIAL_DEPOSIT = 1e18

  EPOCH = 1

  deposit_tx = initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})
  time_of_deposit = deposit_tx.timestamp
  assert initialized_contract.getUserTimeLeftToAccrue(EPOCH, fake_vault, user) == chain.time() - time_of_deposit ## Accrue happens at deposit


  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 10000)
  chain.mine()
  epoch = initialized_contract.epochs(EPOCH)
  epoh_end = epoch[1]

  ## Time left to accrue should be from last accrue to end of epoch
  assert initialized_contract.getUserTimeLeftToAccrue(EPOCH, fake_vault, user) == epoh_end - time_of_deposit ## Accrue happens at deposit


def test_if_accrue_at_end_of_epoch_time_left_is_zero(initialized_contract, user, fake_vault):
  """
    If we accrue at EoEpoch then time left will be zero
  """
  INITIAL_DEPOSIT = 1e18

  EPOCH = 1

  ## Deposit
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## Wait
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 10000)
  chain.mine()

  ## Accrue (resets time of last accrue to current time)
  accrue_tx = initialized_contract.accrueUser(EPOCH, fake_vault, user)
  assert initialized_contract.lastUserAccrueTimestamp(EPOCH, fake_vault, user) == accrue_tx.timestamp

  assert initialized_contract.getUserTimeLeftToAccrue(EPOCH, fake_vault, user) == 0


def test_if_wait_some_time_in_one_epoch(initialized_contract, user, fake_vault):
  """
    Deposit, wait some (less than epoch time)
    Time is going to be chain.time() - time_of_deposit
  """
  INITIAL_DEPOSIT = 1e18

  EPOCH = 1

  deposit_tx = initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})
  time_of_deposit = deposit_tx.timestamp
  assert initialized_contract.getUserTimeLeftToAccrue(EPOCH, fake_vault, user) == 0 ## Note: brownie is weird, sometimes this can be 1 second


  chain.sleep(10000)
  chain.mine()
  epoch = initialized_contract.epochs(EPOCH)

  ## Time left to accrue should be from last accrue to end of epoch
  assert initialized_contract.getUserTimeLeftToAccrue(EPOCH, fake_vault, user) == chain.time() - time_of_deposit ## Accrue happens at deposit


def test_if_wait_one_more_epoch(initialized_contract, user, fake_vault):
  """
    Same as test_if_wait_one_epoch_should_accrue_one_epoch, but we will do the calculations one epoch after
  """

  INITIAL_DEPOSIT = 1e18

  EPOCH = 1

  deposit_tx = initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})
  time_of_deposit = deposit_tx.timestamp
  assert initialized_contract.getUserTimeLeftToAccrue(EPOCH, fake_vault, user) == 0 ## Note: brownie is weird, sometimes this can be 1 second

  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 10000)
  chain.mine()
  epoch = initialized_contract.epochs(EPOCH)
  epoch_end = epoch[1]

  ## Time left to accrue should be from last accrue to end of epoch
  assert initialized_contract.getUserTimeLeftToAccrue(EPOCH, fake_vault, user) == epoch_end - time_of_deposit ## Accrue happens at deposit

  initialized_contract.startNextEpoch()

  ## Didn't change despite more time having passed
  assert initialized_contract.getUserTimeLeftToAccrue(EPOCH, fake_vault, user) == epoch_end - time_of_deposit ## Accrue happens at deposit

  ## For Epoch 2, it just started

  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 10000)
  chain.mine()
  epoch = initialized_contract.epochs(EPOCH)
  epoch_end = epoch[1]

  ## Still hasn't changed
  assert initialized_contract.getUserTimeLeftToAccrue(EPOCH, fake_vault, user) == epoch_end - time_of_deposit ## Accrue happens at deposit

  ## We're at epoch 3, we've never done anything in epoch 3, prove that getUserTimeLeftToAccrue is the entire epoch duration
  epoch_two = initialized_contract.epochs(2)
  epoch_two_start = epoch_two[0]
  epoch_two_end = epoch_two[1]
  assert initialized_contract.getUserTimeLeftToAccrue(2, fake_vault, user) == epoch_two_end - epoch_two_start ## Accrue happens at deposit


