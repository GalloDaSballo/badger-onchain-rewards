import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

"""
  A set of tests checking various cases of accruing points over time
  NOTE: Before doing this, go test `getUserTimeLeftToAccrue`
"""


## One deposit, total supply is the one deposit
## Means that after a withdrawal
## My points == total Points
def full_deposit_one_user(initialized_contract, user, fake_vault):
  INITIAL_DEPOSIT = 1e18

  initialized_contract.notifyTransfer(INITIAL_DEPOSIT, AddressZero, user, {"from": fake_vault})






## One deposit, total supply is the one deposit
## Means that at end of epoch
## My points == total Points
def test_full_deposit_one_user(initialized_contract, user, fake_vault):
  INITIAL_DEPOSIT = 1e18

  EPOCH = 1

  initialized_contract.notifyTransfer(INITIAL_DEPOSIT, AddressZero, user, {"from": fake_vault})

  epochData = initialized_contract.epochs(EPOCH)
  difference = epochData[1] - initialized_contract.lastUserAccrueTimestamp(EPOCH, fake_vault, user)

  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  assert initialized_contract.points(EPOCH, fake_vault, user) == 0 ## Have yet to accrue

  initialized_contract.accrueUser(EPOCH, fake_vault, user)
  initialized_contract.accrueVault(EPOCH, fake_vault)

  ## Points is going to be deposit * time per epoch
  EXPECTED_POINTS = difference * INITIAL_DEPOSIT

  assert approx(initialized_contract.points(EPOCH, fake_vault, user), EXPECTED_POINTS, 1)
  assert initialized_contract.totalPoints(EPOCH, fake_vault) == EXPECTED_POINTS