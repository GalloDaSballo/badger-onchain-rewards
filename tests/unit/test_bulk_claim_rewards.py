import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

## TODO: Test claimBulkTokensOverMultipleEpochs
## Make sure: Old balances are zero and can't be changed
## Latest balance is untouched, ideally ported over if need be

## TO CHANGE
## You can claim for someone else
## All points and math is preserved


## TODO
"""
  _basic
  Optimized Claim works - DONE
  Can claim for yourself - DONE

  _permissions
  Cannot claim for someone else -> DONE
  Cannot claim if accrued epoch -> DONE
  Cannot claim if epoch not ended - > DONE

  Proof: If you claim, you get the same exact amount as if you did it via multiple claims

  _basic
  Security: If you claim, everything goes to zero except the lastAccrueTimestamp, which makes balance always be 0

  Security: If you claim from 2 to 3, you can't use balance of epoch1 to reaccrue and get more rewards -> TODO
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

  ## Go next epoch else you can't claim
  initialized_contract.startNextEpoch()

  ## Claim rewards via the bulk function
  ## Btw, you can claim on someone elses behalf
  tx = initialized_contract.claimBulkTokensOverMultipleEpochs(EPOCH, EPOCH, fake_vault, [token], user, {"from": second_user})


  ## Points are non-zero (they are calculated and pre served)
  points = initialized_contract.points(EPOCH, fake_vault, user)
  assert points > 0

  ## WithdrawPoints are same as points, we always withdraw all
  assert initialized_contract.pointsWithdrawn(EPOCH, fake_vault, user, token) == points

  ## Shares (would be zero if we claimed more than one epoch)
  ## But because we claimed for only one shares are preserved
  assert initialized_contract.shares(EPOCH, fake_vault, user) == INITIAL_DEPOSIT

  ## Vault total Points are non-zero
  assert initialized_contract.totalPoints(EPOCH, fake_vault) > 0
  ## And vault total Supply are non-zero
  assert initialized_contract.totalSupply(EPOCH, fake_vault) > 0

  ## Verify you got the entire reward amount
  assert token.balanceOf(user) == initial_reward_balance + REWARD_AMOUNT

  ## SECURITY STUFF ##
  ## Verify accrue lastUserAccrueTimestamp is non-zero
  assert initialized_contract.lastUserAccrueTimestamp(EPOCH, fake_vault, user) != 0

  ## Verify balance at epoch for user is zero | NOPE: Because shares is non-zero balance is also non-zero
  assert initialized_contract.getBalanceAtEpoch(EPOCH, fake_vault, user)[0] == INITIAL_DEPOSIT
  ## TODO: Does balance being non-zero breaks invariants??

  ## Verify that timeLeftToAccrue is zero as well    
  assert initialized_contract.getUserTimeLeftToAccrue(EPOCH, fake_vault, user) == 0

  
  ## Security check
  ## Accruing points again gives them nothing
  points_before = initialized_contract.points(EPOCH, fake_vault, user)

  initialized_contract.accrueUser(EPOCH, fake_vault, user)

  assert initialized_contract.points(EPOCH, fake_vault, user) == points_before ## No increase


def test_claimBulkTokensOverMultipleEpochs_permissions(initialized_contract, user, fake_vault, token, second_user):
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

  """
    You can claim for someone else
  """
  tx = initialized_contract.claimBulkTokensOverMultipleEpochs(EPOCH, EPOCH, fake_vault, [token], user, {"from": second_user})


  assert token.balanceOf(user) > initial_reward_balance ## They get the tokens
  assert token.balanceOf(second_user) == 0 ## You get nothing

  
  CURRENT_EPOCH = initialized_contract.currentEpoch()

  """
      Cannot claim if epoch not ended
  """
  with brownie.reverts("dev: Can't claim if not expired"):
    initialized_contract.claimBulkTokensOverMultipleEpochs(EPOCH, CURRENT_EPOCH, fake_vault, [token], user, {"from": user})


  """
      Cannot claim if withdrew some reward epoch
  """

  initialized_contract.addReward(CURRENT_EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})


  ## End epoch
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Go next epoch else you can't claim
  initialized_contract.startNextEpoch()

  ## Claim token here
  initialized_contract.claimReward(CURRENT_EPOCH, fake_vault, token, user, {"from": user})

  ## Which will set `pointsWithdrawn` to non-zero causing revert on the check
  with brownie.reverts("dev: You already accrued during the epoch, cannot optimize"):
    initialized_contract.claimBulkTokensOverMultipleEpochs(CURRENT_EPOCH, CURRENT_EPOCH, fake_vault, [token], user, {"from": user})



def test_claimBulkTokensOverMultipleEpochs_cannot_use_old_balance(initialized_contract, user, fake_vault, token, second_user):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})
  initialized_contract.addReward(2, fake_vault, token, REWARD_AMOUNT, {"from": user})
  initialized_contract.addReward(3, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## User didn't deposited, they have 0 points
  assert initialized_contract.points(EPOCH, fake_vault, user) == 0

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = token.balanceOf(user)

  ## Only deposit so we get 100% of rewards
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})
  initialized_contract.notifyTransfer(AddressZero, second_user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## User depoisted, but never accrued, points is still zero
  assert initialized_contract.points(EPOCH, fake_vault, user) == 0

  ## Wait the epoch to end 1
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Go next epoch else you can't claim
  initialized_contract.startNextEpoch()

  ## Wait the epoch to end 2
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Go next epoch else you can't claim
  initialized_contract.startNextEpoch()

  
  ## Wait the epoch to end 3
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()


  ## Go next epoch else you can't claim
  initialized_contract.startNextEpoch()

  ## Second user withdraws at beginning of epoch 4
  initialized_contract.notifyTransfer(second_user, AddressZero, INITIAL_DEPOSIT, {"from": fake_vault})

  ## We're in epoch 4
  assert initialized_contract.currentEpoch() == 4
  
  ## Claim rewards for 2 and 3 for both users
  initialized_contract.claimBulkTokensOverMultipleEpochs(2, 3, fake_vault, [token], user, {"from": user})
  initialized_contract.claimBulkTokensOverMultipleEpochs(2, 3, fake_vault, [token], second_user, {"from": second_user})

  """
    User 1 flow
  """
  ## We never withdrawn, expect balance at 4 to be same as balance as 1 for User 1
  assert initialized_contract.getBalanceAtEpoch(4, fake_vault, user)[0] == initialized_contract.getBalanceAtEpoch(1, fake_vault, user)[0]

  ## Because not optimized, balances are preserved
  assert initialized_contract.getBalanceAtEpoch(2, fake_vault, user)[0] == INITIAL_DEPOSIT
  ## Balance at 3 is not zero because we preserve the last epochs balance for future lookups
  assert initialized_contract.getBalanceAtEpoch(3, fake_vault, user)[0] == INITIAL_DEPOSIT

  ## Balance at 1 is original deposit
  initialized_contract.getBalanceAtEpoch(1, fake_vault, user)[0] == INITIAL_DEPOSIT

  """
    User 2 flow
  """

  ## They withdrew, expect balance at 4 to be zero
  assert initialized_contract.getBalanceAtEpoch(4, fake_vault, second_user)[0] == 0

  ## Because not optimized, balance at 2 is INITIAL_DEPOSIT
  assert initialized_contract.getBalanceAtEpoch(2, fake_vault, second_user)[0] == INITIAL_DEPOSIT
  ## same
  assert initialized_contract.getBalanceAtEpoch(3, fake_vault, second_user)[0] == INITIAL_DEPOSIT

  ## Balance at 1 is original deposit
  initialized_contract.getBalanceAtEpoch(1, fake_vault, second_user)[0] == INITIAL_DEPOSIT