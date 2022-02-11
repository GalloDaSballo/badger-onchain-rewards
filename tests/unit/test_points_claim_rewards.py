import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

## TODO
"""
  Claim
  Claim and get nothing
  Claim after x time and get x time
  Ensure that points and pointsUsed increases properly
"""

## One deposit, total supply is the one deposit
## Means that 
def test_basic_claim_twice_points_check(initialized_contract, user, fake_vault, token):
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

  ## Go next epoch else you can't claim
  initialized_contract.startNextEpoch()

  ## Claim rewards here
  initialized_contract.claimReward(EPOCH, fake_vault, user, token)

  ## Claim rewards accrues, which calculates points ## See `test_accrue_points for proofs`
  points_balance_after_accrue = initialized_contract.points(EPOCH, fake_vault, user)
  assert points_balance_after_accrue > 0

  ## Verify you got the entire amount
  assert token.balanceOf(user) == initial_reward_balance + REWARD_AMOUNT

  ## Custom part
  ## If you claim twice, for same epoch, you get nothing the second time
  initialized_contract.claimReward(EPOCH, fake_vault, user, token)

  ## Your points are the same
  assert points_balance_after_accrue == initialized_contract.points(EPOCH, fake_vault, user)
  
  ## And you're getting nothing because your pointsWithdrawn are the same as your total points
  assert initialized_contract.pointsWithdrawn(EPOCH, fake_vault, user, token) ==  initialized_contract.points(EPOCH, fake_vault, user)

  ## Same as before
  assert token.balanceOf(user) == initial_reward_balance + REWARD_AMOUNT

  ## You can still claimReward for a different token as the `pointsWithdrawn` are zero
  assert initialized_contract.pointsWithdrawn(EPOCH, fake_vault, user, fake_vault) == 0 ## Using fake_vault as token just to demo


def test_claim_in_bulk_works_just_like_normal(initialized_contract, user, fake_vault, token):
    INITIAL_DEPOSIT = 1e18
    REWARD_AMOUNT = 1e20
    EPOCH = initialized_contract.currentEpoch()

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

    ## Claim rewards here
    initialized_contract.claimRewards([EPOCH], [fake_vault], [user], [token])

    ## Claim rewards accrues, which calculates points ## See `test_accrue_points for proofs`
    points_balance_after_accrue = initialized_contract.points(EPOCH, fake_vault, user)
    assert points_balance_after_accrue > 0

    ## Verify you got the entire amount
    assert token.balanceOf(user) == initial_reward_balance + REWARD_AMOUNT

def test_you_cant_claim_if_epoch_isnt_over(initialized_contract, user, fake_vault, token):
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  with brownie.reverts("dev: !can only claim ended epochs"):
    initialized_contract.claimReward(EPOCH, fake_vault, user, token)


def test_revert_cases_for_claimRewards(initialized_contract, user, fake_vault, token):
  EPOCH = initialized_contract.currentEpoch()
  ## 2 Epochs, 1 rest
  with brownie.reverts("Length mismatch"):
    initialized_contract.claimRewards([EPOCH, EPOCH], [fake_vault], [user], [token])
  ## 2 Vaults, 1 rest
  with brownie.reverts("Length mismatch"):
    initialized_contract.claimRewards([EPOCH], [fake_vault, fake_vault], [user], [token])
  ## 2 Users, 1 rest
  with brownie.reverts("Length mismatch"):
    initialized_contract.claimRewards([EPOCH], [fake_vault], [user, user], [token])
  ## 2 tokens, 1 rest
  with brownie.reverts("Length mismatch"):
    initialized_contract.claimRewards([EPOCH], [fake_vault], [user], [token, token])