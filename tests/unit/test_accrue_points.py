import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

"""
  A set of tests checking various cases of accruing points over time
  These tests are effectively built on top of those that prove `getUserTimeLeftToAccrue`
"""

## One deposit, total supply is the one deposit
## Means that at end of epoch
## My points == total Points
def test_full_deposit_one_user(initialized_contract, user, fake_vault):
  INITIAL_DEPOSIT = 1e18

  EPOCH = 1

  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  epochData = initialized_contract.getEpochData(EPOCH)
  difference = epochData[1] - initialized_contract.lastUserAccrueTimestamp(EPOCH, fake_vault, user)
  vault_difference = epochData[1] - initialized_contract.lastAccruedTimestamp(EPOCH, fake_vault)

  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  assert initialized_contract.points(EPOCH, fake_vault, user) == 0 ## Have yet to accrue

  initialized_contract.accrueUser(EPOCH, fake_vault, user)
  initialized_contract.accrueVault(EPOCH, fake_vault)

  ## Points is going to be deposit * time per epoch
  EXPECTED_POINTS = difference * INITIAL_DEPOSIT
  EXPECTED_VAULT_POINTS = vault_difference * INITIAL_DEPOSIT

  ## NOTE: I've sometimes seen the test fail with zero, I believe this can happen if the evm clock doesn't move
  ## If you can predictably figure this out, reach out at alex@badger.finance
  assert approx(initialized_contract.points(EPOCH, fake_vault, user), EXPECTED_POINTS, 1)
  assert initialized_contract.totalPoints(EPOCH, fake_vault) == EXPECTED_VAULT_POINTS

  assert EXPECTED_POINTS == EXPECTED_VAULT_POINTS


## One deposit, total supply is the one deposit
## Means that at end of epoch
## My points == total Points
## If I do the same on epoch 2, I get the same points for epoch 2 as the system brings the totalSupply and epoch after the lookback
def test_full_deposit_one_user_two_epochs(initialized_contract, user, fake_vault):
  INITIAL_DEPOSIT = 1e18

  EPOCH = 1
  EPOCH_TWO = 2

  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  epochData = initialized_contract.getEpochData(EPOCH)
  difference = epochData[1] - initialized_contract.lastUserAccrueTimestamp(EPOCH, fake_vault, user)
  vault_difference = epochData[1] - initialized_contract.lastAccruedTimestamp(EPOCH, fake_vault)

  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  assert initialized_contract.points(EPOCH, fake_vault, user) == 0 ## Have yet to accrue

  initialized_contract.accrueUser(EPOCH, fake_vault, user)
  initialized_contract.accrueVault(EPOCH, fake_vault)

  ## Points is going to be deposit * time per epoch
  EXPECTED_POINTS = difference * INITIAL_DEPOSIT
  EXPECTED_VAULT_POINTS = vault_difference * INITIAL_DEPOSIT

  ## NOTE: I've sometimes seen the test fail with zero, I believe this can happen if the evm clock doesn't move
  ## If you can predictably figure this out, reach out at alex@badger.finance
  assert approx(initialized_contract.points(EPOCH, fake_vault, user), EXPECTED_POINTS, 1)
  assert initialized_contract.totalPoints(EPOCH, fake_vault) == EXPECTED_VAULT_POINTS

  assert EXPECTED_POINTS == EXPECTED_VAULT_POINTS

  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 100000)
  chain.mine()

  initialized_contract.accrueUser(EPOCH_TWO, fake_vault, user)
  initialized_contract.accrueVault(EPOCH_TWO, fake_vault)

  ## Because we never interacted for epoch 2, we expect exact full points
  EXPECTED_POINTS = INITIAL_DEPOSIT * initialized_contract.SECONDS_PER_EPOCH()
  EXPECTED_VAULT_POINTS = INITIAL_DEPOSIT * initialized_contract.SECONDS_PER_EPOCH()

  assert approx(initialized_contract.points(EPOCH_TWO, fake_vault, user), EXPECTED_POINTS, 1)
  assert initialized_contract.totalPoints(EPOCH_TWO, fake_vault) == EXPECTED_VAULT_POINTS

  assert EXPECTED_POINTS == EXPECTED_VAULT_POINTS


  ## Because we already accrue all the time left in the epoch
  assert initialized_contract.getVaultTimeLeftToAccrue(EPOCH_TWO, fake_vault) == 0

  ## Accruring again doesn't do anything
  initialized_contract.accrueUser(EPOCH_TWO, fake_vault, user)
  initialized_contract.accrueVault(EPOCH_TWO, fake_vault)

  assert approx(initialized_contract.points(EPOCH_TWO, fake_vault, user), EXPECTED_POINTS, 1)
  assert initialized_contract.totalPoints(EPOCH_TWO, fake_vault) == EXPECTED_VAULT_POINTS

  assert EXPECTED_POINTS == EXPECTED_VAULT_POINTS


## One deposit, total supply is the one deposit
## Means that at end of epoch
## My points == total Points
def test_revert_if_accrue_future(initialized_contract, user, fake_vault):
  epoch = initialized_contract.currentEpoch()

  with brownie.reverts():
    initialized_contract.accrueUser(epoch + 1, fake_vault, user) 
  
  with brownie.reverts(): 
    initialized_contract.accrueVault(epoch + 1, fake_vault)
    
  with brownie.reverts(): 
    initialized_contract.getVaultTimeLeftToAccrue(epoch + 1000, fake_vault)