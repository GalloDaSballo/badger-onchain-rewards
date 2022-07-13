

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

  Rename the file to test_one_year_of_accrual to make this part of the testing suite
  I had to disable as I can't get tests to end when doing --gas and --coverage
"""

def test_full_deposit_claim_one_year_of_rewards_with_bulk_function_no_optimizations(initialized_contract, user, deployer, second_user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch() + 51

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = token.balanceOf(user)
  initial_reward_balance_second = token.balanceOf(second_user)

  token.approve(initialized_contract, MaxUint256, {"from": deployer})

  ## Only deposit so we get 50% of rewards per user
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})
  initialized_contract.notifyTransfer(AddressZero, second_user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## Wait 51 epochs
  for x in range(1, 52):
    initialized_contract.addReward(x, fake_vault, token, REWARD_AMOUNT, {"from": deployer})

    if(x > 1):
      ## Second User claims every week
      initialized_contract.claimRewardReference(x-1, fake_vault, token, second_user)

    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

  ## Wait out the last epoch so we can claim it
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## User 1 claims
  initialized_contract.claimBulkTokensOverMultipleEpochs(1, 51, fake_vault, [token], user, {"from": user})
  initialized_contract.claimRewardReference(51, fake_vault, token, second_user)

  ## Compare balances at end
  delta_one = token.balanceOf(user) - initial_reward_balance
  delta_two = token.balanceOf(second_user) - initial_reward_balance_second
  assert  delta_one -  delta_two < 1e18 ## Less than one token billionth of a token (due to Brownie and how it counts for time)


def test_full_deposit_autocompouding_vault(initialized_contract, user, deployer, second_user, real_vault):
  INITIAL_DEPOSIT = 1e18
  
  EPOCH = initialized_contract.currentEpoch() + 51

  total_bal = real_vault.balanceOf(user)

  ## Now each has 1/3
  real_vault.transfer(deployer, total_bal // 3 , {"from": user})
  real_vault.transfer(second_user, total_bal // 3, {"from": user})

  ## Dev will send rewards
  REWARD_AMOUNT = real_vault.balanceOf(deployer) // EPOCH

  INITIAL_DEPOSIT = REWARD_AMOUNT * 20 ## Assumes 200% APR

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = real_vault.balanceOf(user)
  initial_reward_balance_second = real_vault.balanceOf(second_user)

  real_vault.approve(initialized_contract, MaxUint256, {"from": deployer})

  ## Only deposit so we get 50% of rewards per user
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": real_vault})
  initialized_contract.notifyTransfer(AddressZero, second_user, INITIAL_DEPOSIT, {"from": real_vault})

  ## Wait 51 epochs
  for x in range(1, 52):
    initialized_contract.addReward(x, real_vault, real_vault, REWARD_AMOUNT, {"from": deployer})

    if(x > 1):
      ## Second User claims every week
      initialized_contract.claimRewardReference(x-1, real_vault, real_vault, second_user)

    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

  ## Wait out the last epoch so we can claim it
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## User 1 claims
  initialized_contract.claimBulkTokensOverMultipleEpochs(1, 51, real_vault, [real_vault], user, {"from": user})
  initialized_contract.claimRewardReference(51, real_vault, real_vault, second_user) ## Claim last epoch just to be sure

  ## Compare balances at end
  delta_one = real_vault.balanceOf(user) - initial_reward_balance
  delta_two = real_vault.balanceOf(second_user) - initial_reward_balance_second
  
  assert  delta_one -  delta_two < REWARD_AMOUNT ## Less than one week of claims