

import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

""""
  Simulate -> Depositing for one year
  -> Claiming rewards for one epoch after one year of inactivity
  -> Claiming rewards for all 52 epochs after one year of inactivity

  These tests should have been already implicitly done via the rest of the testing suite
  But this way we can estimate gas
"""


## One deposit, total supply is the one deposit
## Means that 
def test_full_deposit_one_year(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch() + 51


  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = token.balanceOf(user)

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Go next epoch else you can't claim
  initialized_contract.startNextEpoch()

  ## Wait 51 epochs
  for x in range(1, 52):
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()
    initialized_contract.startNextEpoch({"from": user})

  ## Claim rewards here
  tx = initialized_contract.claimReward(EPOCH, fake_vault, user, token)

  ## Verify you got the entire amount
  assert token.balanceOf(user) == initial_reward_balance + REWARD_AMOUNT

  assert tx.gas_used <= 300_000 ## Run through simulation is 255651


def test_full_deposit_claim_one_year_of_rewards(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch() + 51


  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = token.balanceOf(user)

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  epochs_to_claim = []
  vaults_to_claim = []
  users_to_claim = []
  tokens_to_claim = []

  ## Wait 51 epochs
  for x in range(1, 52):
    initialized_contract.addReward(x, fake_vault, token, REWARD_AMOUNT, {"from": user})
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()
    initialized_contract.startNextEpoch({"from": user})

    epochs_to_claim.append(x)
    vaults_to_claim.append(fake_vault)
    users_to_claim.append(user)
    tokens_to_claim.append(token)


  ## Claim rewards here
  tx = initialized_contract.claimRewards(epochs_to_claim, vaults_to_claim, users_to_claim, tokens_to_claim)

  ## Verify you got the entire amount
  assert token.balanceOf(user) == initial_reward_balance ## First reward is still inside for another epoch

  assert tx.gas_used <= 5_207_667 ## Run through simulation

def test_full_deposit_claim_one_year_of_rewards_with_optimization(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch() + 51

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = token.balanceOf(user)

  token.approve(initialized_contract, MaxUint256, {"from": user})

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## Wait 51 epochs
  for x in range(1, 52):
    initialized_contract.addReward(x, fake_vault, token, REWARD_AMOUNT, {"from": user})
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()
    initialized_contract.startNextEpoch({"from": user})

  ## Wait out the last epoch so we can claim it
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()
  initialized_contract.startNextEpoch({"from": user})

  ## Claim rewards here
  tx = initialized_contract.claimBulkTokensOverMultipleEpochsOptimized(1, 52, fake_vault, [token], {"from": user})

  ## Verify you got the entire amount
  assert token.balanceOf(user) == initial_reward_balance ## First reward is still inside for another epoch

  assert tx.gas_used <= 1_500_000 ## 1483973 Run through simulation