import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

"""
  TODO:
  getClaimableBulkRewards
  returns value that is equivalent to all claim functions
"""

## One deposit, total supply is the one deposit
## Means that 
def test_claimBulkTokensOverMultipleEpochs_basic(initialized_contract, user, fake_vault, token, second_user):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## User didn't deposited, they have 0 points
  assert initialized_contract.points(EPOCH, fake_vault, user) == 0

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = token.balanceOf(user)

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## User depoisted, but never accrued, points is still zero
  assert initialized_contract.points(EPOCH, fake_vault, user) == 0

  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## TODO :Get quote of rewards claimable
  claimParams = [EPOCH, EPOCH, fake_vault.address, [token.address]]
  quote = initialized_contract.getClaimableBulkRewards(claimParams, user)
  calculated_amount = quote[0]

  ## Claim rewards via the bulk function
  ## Btw, you can claim on someone elses behalf
  tx = initialized_contract.claimBulkTokensOverMultipleEpochs(EPOCH, EPOCH, fake_vault, [token], user, {"from": second_user})

  ## Verify you got the entire reward amount
  assert token.balanceOf(user) == initial_reward_balance + REWARD_AMOUNT

  assert calculated_amount == REWARD_AMOUNT


## One deposit, total supply is the one deposit
## Means that 
def test_claimBulkTokensOverMultipleEpochsOptimized_basic(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## User didn't deposited, they have 0 points
  assert initialized_contract.points(EPOCH, fake_vault, user) == 0

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = token.balanceOf(user)

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## User depoisted, but never accrued, points is still zero
  assert initialized_contract.points(EPOCH, fake_vault, user) == 0

  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## TODO :Get quote of rewards claimable
  claimParams = [EPOCH, EPOCH, fake_vault.address, [token.address]]
  quote = initialized_contract.getClaimableBulkRewards(claimParams, user)
  calculated_amount = quote[0]

  ## Claim rewards via the bulk function
  ## Btw only you can claim for yourself
  tx = initialized_contract.claimBulkTokensOverMultipleEpochsOptimizedWithoutStorage([EPOCH, EPOCH, fake_vault, [token]], {"from": user})

  ## Verify you got the entire reward amount
  assert token.balanceOf(user) == initial_reward_balance + REWARD_AMOUNT

  assert calculated_amount == REWARD_AMOUNT