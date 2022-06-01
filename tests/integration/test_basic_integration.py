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


"""
  Test deposit with a real vault
"""
def test_full_deposit_one_user(initialized_contract, user, real_vault, token):
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, real_vault, token, REWARD_AMOUNT, {"from": user})

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = token.balanceOf(user)

  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Go next epoch else you can't claim
  initialized_contract.startNextEpoch()

  ## Claim rewards here
  initialized_contract.claimReward(EPOCH, real_vault, token, user)

  ## Verify you got the entire amount
  assert token.balanceOf(user) == initial_reward_balance + REWARD_AMOUNT



"""
  What happens if we emit the vault as the reward token?
"""
def test_basic_with_vault_emitted(initialized_contract, user, real_vault, token, deployer):
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards as form of vault token here
  token.approve(real_vault, MaxUint256, {"from": deployer})
  real_vault.deposit(REWARD_AMOUNT, {"from": deployer})
  real_vault.approve(initialized_contract, MaxUint256, {"from": deployer})
  initialized_contract.addReward(EPOCH, real_vault, real_vault, REWARD_AMOUNT, {"from": deployer})

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = real_vault.balanceOf(user)
  initial_deployer_balance = real_vault.balanceOf(deployer)

  assert initial_deployer_balance == 0 ## 0 cause we sent all as reward

  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Go next epoch else you can't claim
  initialized_contract.startNextEpoch()

  ## Claim rewards here
  initialized_contract.claimReward(EPOCH, real_vault, real_vault, user)
  initialized_contract.claimReward(EPOCH, real_vault, real_vault, deployer)

  ## Verify that all rewards were distributed (minus 1 approx due to rounding)
  assert approx(real_vault.balanceOf(user) + real_vault.balanceOf(deployer), initial_reward_balance + REWARD_AMOUNT, 1)