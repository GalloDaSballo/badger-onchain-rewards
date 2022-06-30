import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

"""
  Test rug
"""
def test_rug(initialized_contract, user, fake_vault, token, badger_registry):
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Rug the reward
  balanceBefore = token.balanceOf(badger_registry.address)
  initialized_contract.rug(token, {"from": badger_registry})
  balanceAfter = token.balanceOf(badger_registry.address)
  
  ## Verify rug is successful
  assert balanceAfter - balanceBefore == REWARD_AMOUNT
  
"""
  Test rug renouncement
"""
def test_rug_renouncement(initialized_contract, user, fake_vault, token, badger_registry):
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Rug the reward which will fail due to renouncement
  initialized_contract.renounceRuggability({"from": badger_registry})
  with brownie.reverts():
       initialized_contract.rug(token, {"from": badger_registry})