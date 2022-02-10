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
## Means that 
def test_full_deposit_one_user(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()


  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = token.balanceOf(user)

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(INITIAL_DEPOSIT, AddressZero, user, {"from": fake_vault})

  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Go next epoch else you can't claim
  initialized_contract.startNextEpoch()

  ## Claim rewards here
  initialized_contract.claimReward(EPOCH, fake_vault, user, token)

  ## Verify you got the entire amount
  assert token.balanceOf(user) == initial_reward_balance + REWARD_AMOUNT