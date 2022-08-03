import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))


## Make sure: Old balances are zero and can't be changed
## Latest balance is untouched, ideally ported over if need be

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

  Security: If you claim from 2 to 3, you can't use balance of epoch1 to reaccrue and get more rewards -> DONE
"""

## One deposit, total supply is the one deposit
## Means that 
def test_claimBulkTokensOverMultipleEpochsOptimizedWithoutStorageNonEmitting_basic(initialized_contract, user, fake_vault, token):
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

  ## Claim rewards via the bulk function
  ## Btw only you can claim for yourself
  tx = initialized_contract.tear([EPOCH, EPOCH, fake_vault, [token]], {"from": user})


  ## Because we use the optimized
  ## Points are zero
  assert initialized_contract.points(EPOCH, fake_vault, user) == 0

  ## Shares (would be zero if we claimed more than one epoch)
  ## But because we claimed for only one shares are preserved
  assert initialized_contract.shares(EPOCH, fake_vault, user) == INITIAL_DEPOSIT

  ## Vault total Points are non-zero
  ## if we accrue vault, which we can as change is non-destructive to vault data
  initialized_contract.accrueVault(EPOCH, fake_vault)
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
  initialized_contract.accrueUser(EPOCH, fake_vault, user)

  assert initialized_contract.points(EPOCH, fake_vault, user) == 0

def test_claimBulkTokensOverMultipleEpochsOptimizedWithoutStorageNonEmitting_cannotClaimForOthers(initialized_contract, user, fake_vault, token, second_user):
  INITIAL_DEPOSIT = 1e18
  INITIAL_SECOND_USER_DEPOSIT = INITIAL_DEPOSIT // 3
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

  """
    Cannot claim for someone else
  """
  tx = initialized_contract.tear([EPOCH, EPOCH, fake_vault, [token]], {"from": second_user})

  ## They got nothing
  assert token.balanceOf(user) == initial_reward_balance ## They didn't get the tokens
  assert token.balanceOf(second_user) == 0 ## They also got nothing



def test_claimBulkTokensOverMultipleEpochsOptimizedWithoutStorageNonEmitting_permissions(initialized_contract, user, fake_vault, token, second_user):
  INITIAL_DEPOSIT = 1e18
  INITIAL_SECOND_USER_DEPOSIT = INITIAL_DEPOSIT // 3
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
  initialized_contract.notifyTransfer(AddressZero, second_user, INITIAL_SECOND_USER_DEPOSIT, {"from": fake_vault})

  ## User depoisted, but never accrued, points is still zero
  assert initialized_contract.points(EPOCH, fake_vault, user) == 0

  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  """
    Cannot claim for someone else
  """
  tx = initialized_contract.tear([EPOCH, EPOCH, fake_vault, [token]], {"from": second_user})

  ## They got nothing
  assert token.balanceOf(user) == initial_reward_balance ## They didn't get the tokens
  assert token.balanceOf(second_user) > 0 ## They did

  
  CURRENT_EPOCH = initialized_contract.currentEpoch()

  """
      Cannot claim if epoch not ended
  """
  with brownie.reverts("only ended epochs"):
    initialized_contract.tear([EPOCH, CURRENT_EPOCH, fake_vault, [token]], {"from": user})


  """
      Cannot claim if withdrew some reward epoch
  """

  initialized_contract.addReward(CURRENT_EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})


  ## End epoch
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Claim token here
  initialized_contract.claimRewardEmitting(CURRENT_EPOCH, fake_vault, token, user, {"from": user})

  ## Which will set `pointsWithdrawn` to non-zero causing revert on the check
  with brownie.reverts("already claimed"):
    initialized_contract.tear([CURRENT_EPOCH, CURRENT_EPOCH, fake_vault, [token]], {"from": user})



def test_claimBulkTokensOverMultipleEpochsOptimizedWithoutStorageNonEmitting_cannot_use_old_balance(initialized_contract, user, fake_vault, token, second_user):
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

  ## Wait the epoch to end 2
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()
  
  ## Wait the epoch to end 3
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Second user withdraws at beginning of epoch 4
  initialized_contract.notifyTransfer(second_user, AddressZero, INITIAL_DEPOSIT, {"from": fake_vault})

  ## We're in epoch 4
  assert initialized_contract.currentEpoch() == 4
  
  ## Claim rewards for 2 and 3 for both users
  initialized_contract.tear([2, 3, fake_vault, [token]], {"from": user})
  initialized_contract.tear([2, 3, fake_vault, [token]], {"from": second_user})

  """
    User 1 flow
  """
  ## We never withdrawn, expect balance at 4 to be same as balance as 1 for User 1
  assert initialized_contract.getBalanceAtEpoch(4, fake_vault, user)[0] == initialized_contract.getBalanceAtEpoch(1, fake_vault, user)[0]

  ## Because we used the optimized, balance at 2 and 3 is now zero
  assert initialized_contract.getBalanceAtEpoch(2, fake_vault, user)[0] == 0
  ## Balance at 3 is not zero because we preserve the last epochs balance for future lookups
  assert initialized_contract.getBalanceAtEpoch(3, fake_vault, user)[0] == INITIAL_DEPOSIT

  ## Balance at 1 is original deposit
  initialized_contract.getBalanceAtEpoch(1, fake_vault, user)[0] == INITIAL_DEPOSIT

  """
    User 2 flow
  """

  ## They withdrew, expect balance at 4 to be zero
  assert initialized_contract.getBalanceAtEpoch(4, fake_vault, second_user)[0] == 0

  ## Because of optimized, balance at 2 is zero
  assert initialized_contract.getBalanceAtEpoch(2, fake_vault, second_user)[0] == 0
  ## Balance at 3 is not zero because we preserve the last epochs balance for future lookups
  assert initialized_contract.getBalanceAtEpoch(3, fake_vault, second_user)[0] == INITIAL_DEPOSIT

  ## Balance at 1 is original deposit
  initialized_contract.getBalanceAtEpoch(1, fake_vault, second_user)[0] == INITIAL_DEPOSIT

## Claim points with no deposit
def test_bulk_claim_no_points(initialized_contract, user, fake_vault, token, second_user):
  initial_bal = token.balanceOf(second_user)

  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## With no points you get no rewards
  initialized_contract.tear([1, 1, fake_vault, [token]], {"from": user})

  ## No tokens received
  assert initial_bal == token.balanceOf(second_user)

def test_bulk_claim_revert(initialized_contract, user, fake_vault, token, second_user):
  ## Revert is epoch_start > epoch_end
  with brownie.reverts():
    initialized_contract.tear([1, 0, fake_vault, [token]], {"from": user})
  

  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Revert if claiming same token
  with brownie.reverts():
    initialized_contract.tear([1, 1, fake_vault, [token, token]], {"from": user})
