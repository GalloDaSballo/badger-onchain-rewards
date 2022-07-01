import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

"""
  Test revert on utils
       _requireNoDuplicates()
"""
def test_duplicates(initialized_contract, user, fake_vault, token):
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
  
  ## Claim rewards over multiple epochs will revert due to given duplicate parameters
  duplicateArrays = [fake_vault.address, token.address, token.address]
  claimParams = [EPOCH, lastEPOCH, fake_vault.address, duplicateArrays]
  with brownie.reverts():
       claimTx = initialized_contract.claimBulkTokensOverMultipleEpochsOptimizedWithoutStorageNonEmitting(claimParams, {"from": user})
       
"""
  Test revert on validity checks against given epochId
       getUserNextEpochInfo()
       getVaultNextEpochInfo()
       claimRewardReference()
       claimReward()
       claimRewardNonEmitting()
       
"""       
def test_invalid_epochId(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e19
  EPOCH = initialized_contract.currentEpoch()
  invalidEPOCH = EPOCH + 100

  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## Wait the epoch to end
  secondsPerEpoch = initialized_contract.SECONDS_PER_EPOCH()  
  chain.sleep(secondsPerEpoch + 1)
  chain.mine()
  
  ## Followings will revert due to given epochId > currentEpoch()
  with brownie.reverts():
       initialized_contract.getUserNextEpochInfo(invalidEPOCH, fake_vault.address, user.address, 0)
  with brownie.reverts():
       initialized_contract.getVaultNextEpochInfo(invalidEPOCH, fake_vault.address, 0)
  with brownie.reverts():
       initialized_contract.claimRewardReference(invalidEPOCH, fake_vault.address, token.address, user.address, {'from': user})
  with brownie.reverts():
       initialized_contract.claimReward(invalidEPOCH, fake_vault.address, token.address, user.address, {'from': user})
  with brownie.reverts():
       initialized_contract.claimRewardNonEmitting(invalidEPOCH, fake_vault.address, token.address, user.address, {'from': user})
       
"""
  Test revert on epoch which already claimed thus can't be optimized 
       claimBulkTokensOverMultipleEpochsOptimizedWithoutStorage()
"""
def test_bulk_claim_over_already_claimed(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e19
  ## Multiple epochs to claim rewards
  EPOCH = initialized_contract.currentEpoch()
  nextEPOCH = EPOCH + 1
  lastEPOCH = EPOCH + 2
  invalidEPOCH = EPOCH + 100

  ## Add rewards for all epochs
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})
  initialized_contract.addReward(nextEPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})
  initialized_contract.addReward(lastEPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## Wait current epoch to end and claim rewards for this epoch
  advanceTime = initialized_contract.SECONDS_PER_EPOCH() + 1
  chain.sleep(advanceTime * 1 + 1000)
  chain.mine()
  initialized_contract.claimRewardReference(EPOCH, fake_vault.address, token.address, user.address, {'from': user}) 

  ## Withdraw from staking and wait all epochs to end  
  initialized_contract.notifyTransfer(user, AddressZero, INITIAL_DEPOSIT, {"from": fake_vault})
  chain.sleep(advanceTime * 2)
  chain.mine()
  
  ## Claim rewards over multiple epochs will revert due to epochStart > epochEnd
  claimParams = [lastEPOCH, EPOCH, fake_vault.address, [token.address]]
  with brownie.reverts():
       initialized_contract.claimBulkTokensOverMultipleEpochsOptimizedWithoutStorage(claimParams, {"from": user}) 
       
  ## Claim rewards over multiple epochs will revert due to epochEnd >= currentEpoch()
  claimParams = [EPOCH, invalidEPOCH, fake_vault.address, [token.address]]
  with brownie.reverts():
       initialized_contract.claimBulkTokensOverMultipleEpochsOptimizedWithoutStorage(claimParams, {"from": user}) 
       
  ## Claim rewards over multiple epochs will revert due to one of the given epochs has been claimed
  claimParams = [EPOCH, EPOCH, fake_vault.address, [token.address]]
  with brownie.reverts():
       initialized_contract.claimBulkTokensOverMultipleEpochsOptimizedWithoutStorage(claimParams, {"from": user})
       
  ## Claim rewards over rest epochs will be good
  balBefore = token.balanceOf(user.address)
  claimParams = [nextEPOCH, lastEPOCH, fake_vault.address, [token.address]]  
  claimTx = initialized_contract.claimBulkTokensOverMultipleEpochsOptimizedWithoutStorage(claimParams, {"from": user})
  balAfter = token.balanceOf(user.address)
  assert balAfter > balBefore ## should get some reward before withdrwal
  startAccrueTimestamp = initialized_contract.lastUserAccrueTimestamp(nextEPOCH, fake_vault.address, user.address)
  endAccrueTimestamp = initialized_contract.lastUserAccrueTimestamp(lastEPOCH, fake_vault.address, user.address)
  assert startAccrueTimestamp == endAccrueTimestamp and endAccrueTimestamp == chain[claimTx.block_number].timestamp
       
"""
  Test revert on epoch which already claimed thus can't be optimized 
       claimBulkTokensOverMultipleEpochsOptimizedWithoutStorageNonEmitting()
"""
def test_bulk_claim_non_emitting_over_already_claimed(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e19
  ## Multiple epochs to claim rewards
  EPOCH = initialized_contract.currentEpoch()
  nextEPOCH = EPOCH + 1
  lastEPOCH = EPOCH + 2
  invalidEPOCH = EPOCH + 100

  ## Add rewards for all epochs
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})
  initialized_contract.addReward(nextEPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})
  initialized_contract.addReward(lastEPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## Wait current epoch to end and claim rewards for this epoch
  advanceTime = initialized_contract.SECONDS_PER_EPOCH() + 1
  chain.sleep(advanceTime * 1 + 1000)
  chain.mine()
  initialized_contract.claimRewardReference(EPOCH, fake_vault.address, token.address, user.address, {'from': user}) 

  ## Withdraw from staking and wait all epochs to end  
  initialized_contract.notifyTransfer(user, AddressZero, INITIAL_DEPOSIT, {"from": fake_vault})
  chain.sleep(advanceTime * 2)
  chain.mine()
  
  ## Claim rewards over multiple epochs will revert due to epochStart > epochEnd
  claimParams = [lastEPOCH, EPOCH, fake_vault.address, [token.address]]
  with brownie.reverts():
       initialized_contract.claimBulkTokensOverMultipleEpochsOptimizedWithoutStorageNonEmitting(claimParams, {"from": user}) 
       
  ## Claim rewards over multiple epochs will revert due to epochEnd >= currentEpoch()
  claimParams = [EPOCH, invalidEPOCH, fake_vault.address, [token.address]]
  with brownie.reverts():
       initialized_contract.claimBulkTokensOverMultipleEpochsOptimizedWithoutStorageNonEmitting(claimParams, {"from": user}) 
       
  ## Claim rewards over multiple epochs will revert due to one of the given epochs has been claimed
  claimParams = [EPOCH, EPOCH, fake_vault.address, [token.address]]
  with brownie.reverts():
       initialized_contract.claimBulkTokensOverMultipleEpochsOptimizedWithoutStorageNonEmitting(claimParams, {"from": user})
       
  ## Claim rewards over rest epochs will be good
  balBefore = token.balanceOf(user.address)
  claimParams = [nextEPOCH, lastEPOCH, fake_vault.address, [token.address]]  
  claimTx = initialized_contract.claimBulkTokensOverMultipleEpochsOptimizedWithoutStorageNonEmitting(claimParams, {"from": user})
  balAfter = token.balanceOf(user.address)
  assert balAfter > balBefore ## should get some reward before withdrwal
  startAccrueTimestamp = initialized_contract.lastUserAccrueTimestamp(nextEPOCH, fake_vault.address, user.address)
  endAccrueTimestamp = initialized_contract.lastUserAccrueTimestamp(lastEPOCH, fake_vault.address, user.address)
  assert startAccrueTimestamp == endAccrueTimestamp and endAccrueTimestamp == chain[claimTx.block_number].timestamp
  
"""
  Test claimRewardNonEmitting revert on claimed-already
"""
def test_claim_non_emitting_revert(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})
  
  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()
  
  ## Second claim will revert due to this epoch has been claimed before
  initialized_contract.claimRewardReference(EPOCH, fake_vault.address, token.address, user.address, {"from": user})
  assert initialized_contract.pointsWithdrawn(EPOCH, fake_vault.address, user.address, token.address) > 0
  with brownie.reverts():
       initialized_contract.claimRewardNonEmitting(EPOCH, fake_vault.address, token.address, user.address, {"from": user})
       
"""
  Test claimReward revert on claimed-already
"""
def test_claim_revert(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})
  
  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()
  
  ## Second claim will revert due to this epoch has been claimed before
  initialized_contract.claimRewardReference(EPOCH, fake_vault.address, token.address, user.address, {"from": user})
  assert initialized_contract.pointsWithdrawn(EPOCH, fake_vault.address, user.address, token.address) > 0
  with brownie.reverts():
       initialized_contract.claimReward(EPOCH, fake_vault.address, token.address, user.address, {"from": user})
       
"""
  Test revert on fee-on-transfer token rewards addition  
       addBulkRewardsLinearly()
       addBulkRewards()
"""
def test_bulk_rewards(initialized_contract, user, fake_vault, fee_on_transfer_token):
  REWARD_AMOUNT = 1e19
  ## Multiple epochs to claim rewards
  EPOCH = initialized_contract.currentEpoch()
  nextEPOCH = EPOCH + 1
  lastEPOCH = EPOCH + 2

  ## Add rewards for all epochs will revert due to fee-on-transfer token not supported 
  fee_on_transfer_token.approve(initialized_contract, MaxUint256, {"from": user})
  fee_on_transfer_token.mint(user.address, REWARD_AMOUNT * 100, {"from": user})
  assert fee_on_transfer_token.balanceOf(user.address) == REWARD_AMOUNT * 100
  
  with brownie.reverts():
       initialized_contract.addBulkRewardsLinearly(EPOCH, lastEPOCH, fake_vault.address, fee_on_transfer_token.address, REWARD_AMOUNT * 3, {"from": user})  
  with brownie.reverts():
       initialized_contract.addBulkRewards(EPOCH, lastEPOCH, fake_vault.address, fee_on_transfer_token.address, [REWARD_AMOUNT, REWARD_AMOUNT, REWARD_AMOUNT], {"from": user})   

  ## Revert because of totalEpochs = 0
  with brownie.reverts():
     initialized_contract.addBulkRewardsLinearly(EPOCH, EPOCH - 1, fake_vault.address, fee_on_transfer_token.address, REWARD_AMOUNT * 3, {"from": user})  
  with brownie.reverts():
     initialized_contract.addBulkRewards(EPOCH, EPOCH - 1, fake_vault.address, fee_on_transfer_token.address, [REWARD_AMOUNT, REWARD_AMOUNT, REWARD_AMOUNT], {"from": user})  

  ## Add rewards for all epochs will revert due to given rewards array mismacth with given [start, end] length  
  with brownie.reverts():
       initialized_contract.addBulkRewards(EPOCH, lastEPOCH, fake_vault.address, fee_on_transfer_token.address, [REWARD_AMOUNT], {"from": user})  
       
       
       