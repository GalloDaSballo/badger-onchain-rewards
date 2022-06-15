import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))


## Bulk claiming when there are duplicate tokens gives the user too many rewards
def test_bulk_claim_duplicate_tokens(initialized_contract, user, fake_vault, token):
  INITIAL_DEPOSIT = 1e18
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards to vault for EPOCH
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## User deposits into the vault
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

  ## Time passes and a new epoch starts
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Add rewards to vault for EPOCH + 1
  initialized_contract.addReward(EPOCH + 1, fake_vault, token, REWARD_AMOUNT, {"from": user})

  ## At this point, there should be REWARD_AMOUNT * 2 tokens in the contract, 
  ## half of this belongs to EPOCH and the other half belongs to EPOCH + 1
  assert token.balanceOf(initialized_contract) == REWARD_AMOUNT * 2

  ## User shouldn't be allowed to bulk claim with the same token, otherwise they can steal tokens
  with brownie.reverts():
    initialized_contract.claimBulkTokensOverMultipleEpochs(EPOCH, EPOCH, fake_vault, [token, token], user, {"from": user})