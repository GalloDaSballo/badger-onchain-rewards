import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

"""
  Test claimRewardNonEmitting
"""
def test_claim_non_emitting(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Only deposit so we get 100% of rewards
  userPointsWithdrawn = initialized_contract.pointsWithdrawn(EPOCH, fake_vault.address, user.address, token.address)
  rewardsTotal = initialized_contract.rewards(EPOCH, fake_vault.address, token.address)
  assert rewardsTotal == REWARD_AMOUNT and userPointsWithdrawn == 0
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})
  
  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()
  
  ## Claim rewards
  balBefore = token.balanceOf(user.address)
  userBalanceAtEpochId = initialized_contract.getBalanceAtEpoch(EPOCH, fake_vault.address, user.address)[0]
  assert userBalanceAtEpochId == INITIAL_DEPOSIT
  userInfo = initialized_contract.getUserNextEpochInfo(EPOCH, fake_vault.address, user.address, userBalanceAtEpochId)
  userEpochTotalPoints = userInfo[2]
  userTimeToAccure = userInfo[1]
  initialized_contract.claimRewardNonEmitting(EPOCH, fake_vault.address, token.address, user.address, {"from": user})
  
  ## Dummy claim from Zero address 
  dummyClaim = initialized_contract.claimRewardNonEmitting(EPOCH, fake_vault.address, token.address, AddressZero, {"from": user})
  assert len(dummyClaim.events) == 0
  
  ## Verify all rewards for the epoch has been claimed  
  balAfter = token.balanceOf(user.address)
  assert balAfter - balBefore == REWARD_AMOUNT  
  userPointsWithdrawn = initialized_contract.pointsWithdrawn(EPOCH, fake_vault.address, user.address, token.address)
  assert userEpochTotalPoints == userPointsWithdrawn and userPointsWithdrawn == userTimeToAccure * userBalanceAtEpochId

"""
  Test claimBulkTokensOverMultipleEpochsOptimizedWithoutStorageNonEmitting
"""
def test_bulk_claim_non_emitting(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e19
  ## Multiple epochs to claim rewards
  EPOCH = initialized_contract.currentEpoch()
  nextEPOCH = EPOCH + 1
  lastEPOCH = EPOCH + 2

  ## Add rewards for next two epochs
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(nextEPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})
  initialized_contract.addReward(lastEPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## Wait the all epochs to end
  advanceTime = initialized_contract.SECONDS_PER_EPOCH() + 1
  chain.sleep(advanceTime * 3)
  chain.mine()
  
  ## Claim rewards over multiple epochs
  balBefore = token.balanceOf(user.address)
  claimParams = [EPOCH, lastEPOCH, fake_vault.address, [token.address]]
  claimTx = initialized_contract.claimBulkTokensOverMultipleEpochsOptimizedWithoutStorageNonEmitting(claimParams, {"from": user})
  
  ## Verify all rewards for multiple epochs have been claimed  
  balAfter = token.balanceOf(user.address)
  assert balAfter - balBefore == REWARD_AMOUNT * 2
  startAccrueTimestamp = initialized_contract.lastUserAccrueTimestamp(EPOCH, fake_vault.address, user.address)
  endAccrueTimestamp = initialized_contract.lastUserAccrueTimestamp(lastEPOCH, fake_vault.address, user.address)
  assert startAccrueTimestamp == endAccrueTimestamp and endAccrueTimestamp == chain[claimTx.block_number].timestamp
  shareLast = initialized_contract.shares(lastEPOCH, fake_vault.address, user.address)
  assert shareLast == INITIAL_DEPOSIT
  pointsLast = initialized_contract.points(lastEPOCH, fake_vault.address, user.address)
  assert pointsLast == 0

"""
  Test claimBulkTokensOverMultipleEpochsOptimizedWithoutStorage
"""
def test_bulk_claim(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e19
  ## Multiple epochs to claim rewards
  EPOCH = initialized_contract.currentEpoch()
  nextEPOCH = EPOCH + 1
  lastEPOCH = EPOCH + 2

  ## Add rewards for next two epochs
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(nextEPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})
  initialized_contract.addReward(lastEPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## Wait the all epochs to end
  advanceTime = initialized_contract.SECONDS_PER_EPOCH() + 1
  chain.sleep(advanceTime * 3)
  chain.mine()
  
  ## Claim rewards over multiple epochs
  balBefore = token.balanceOf(user.address)
  claimParams = [EPOCH, lastEPOCH, fake_vault.address, [token.address]]
  claimTx = initialized_contract.claimBulkTokensOverMultipleEpochsOptimizedWithoutStorage(claimParams, {"from": user})
  
  ## Verify all rewards for multiple epochs have been claimed  
  balAfter = token.balanceOf(user.address)
  assert balAfter - balBefore == REWARD_AMOUNT * 2
  startAccrueTimestamp = initialized_contract.lastUserAccrueTimestamp(EPOCH, fake_vault.address, user.address)
  endAccrueTimestamp = initialized_contract.lastUserAccrueTimestamp(lastEPOCH, fake_vault.address, user.address)
  assert startAccrueTimestamp == endAccrueTimestamp and endAccrueTimestamp == chain[claimTx.block_number].timestamp
  shareLast = initialized_contract.shares(lastEPOCH, fake_vault.address, user.address)
  assert shareLast == INITIAL_DEPOSIT
  pointsLast = initialized_contract.points(lastEPOCH, fake_vault.address, user.address)
  assert pointsLast == 0