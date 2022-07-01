import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

"""
  Test getThisEpochBalance & getThisEpochTotalSupply
"""
def test_this_epoch_balance_totalsupply(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Only deposit so we get 100% of rewards
  balanceBefore = initialized_contract.getThisEpochBalance(EPOCH, fake_vault.address, user.address, 0)
  assert balanceBefore == 0
  tsBefore = initialized_contract.getThisEpochTotalSupply(EPOCH, fake_vault.address, 0)
  assert tsBefore == 0  
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()
  
  ## Verify balance & total supply
  balanceAfter = initialized_contract.getThisEpochBalance(EPOCH, fake_vault.address, user.address, 0)
  assert balanceAfter == INITIAL_DEPOSIT
  tsAfter = initialized_contract.getThisEpochTotalSupply(EPOCH, fake_vault.address, 0)
  assert tsAfter == INITIAL_DEPOSIT

"""
  Test getTotalSupplyAtEpoch
"""
def test_totalsupply_at_epoch(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()
  nextEPOCH = EPOCH + 1
  lastEPOCH = EPOCH + 2

  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})
  initialized_contract.addReward(nextEPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})
  initialized_contract.addReward(lastEPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Only deposit so we get 100% of rewards
  epochTime = initialized_contract.SECONDS_PER_EPOCH() + 1
  chain.sleep(epochTime * 2 + 1000)
  chain.mine()
  totalSupplyBefore = initialized_contract.getTotalSupplyAtEpoch(nextEPOCH, fake_vault.address)
  assert totalSupplyBefore[0] == 0 and totalSupplyBefore[1] == False

  ## Wait the epoch to end
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})
  
  ## Verify balance & total supply
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1000)
  chain.mine()
  totalSupplyAfter  = initialized_contract.getTotalSupplyAtEpoch(lastEPOCH, fake_vault.address)
  assert totalSupplyAfter[0] == INITIAL_DEPOSIT and totalSupplyBefore[1] == False

"""
  Test getUserTimeLeftToAccrueForEndedEpoch & getVaultTimeLeftToAccrueForEndedEpoch
"""
def test_time_left_to_accrue(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e19
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## Wait the epoch to end
  secondsPerEpoch = initialized_contract.SECONDS_PER_EPOCH()  
  print(secondsPerEpoch)
  chain.sleep(secondsPerEpoch + 1)
  chain.mine()
  
  ## Verify time left to accrue before claim
  timeLeftUser = initialized_contract.getUserTimeLeftToAccrueForEndedEpoch(EPOCH, fake_vault.address, user.address)
  timeLeftVault = initialized_contract.getVaultTimeLeftToAccrueForEndedEpoch(EPOCH, fake_vault.address)
  assert 0 < timeLeftVault and timeLeftVault < secondsPerEpoch and 0 < timeLeftUser and timeLeftUser < secondsPerEpoch
  
  ## Claim rewards with fully on-chain implementation means we got all rewards and there is no time to accrue
  initialized_contract.claimRewardReference(EPOCH, fake_vault.address, token.address, user.address, {'from': user})
  
  ## Verify time left to accrue after claim
  timeLeftUserAfter = initialized_contract.getUserTimeLeftToAccrueForEndedEpoch(EPOCH, fake_vault.address, user.address)
  timeLeftVaultAfter = initialized_contract.getVaultTimeLeftToAccrueForEndedEpoch(EPOCH, fake_vault.address)
  assert 0 == timeLeftVaultAfter and 0 == timeLeftUserAfter
  
  ## One more epoch and check again
  nextEPOCH = EPOCH + 1
  initialized_contract.addReward(nextEPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})
  chain.sleep(secondsPerEpoch + 1)
  chain.mine()
  timeLeftUserLast = initialized_contract.getUserTimeLeftToAccrueForEndedEpoch(nextEPOCH, fake_vault.address, user.address)
  timeLeftVaultLast = initialized_contract.getVaultTimeLeftToAccrueForEndedEpoch(nextEPOCH, fake_vault.address)
  assert secondsPerEpoch == timeLeftVaultLast and secondsPerEpoch == timeLeftUserLast
  