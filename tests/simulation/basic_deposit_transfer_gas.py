

import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

""""
  Check gas costs for Deposits and Transfers
"""

def test_deposit_and_transfer(initialized_contract, user, real_vault, token, second_user, deposit_amount):
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Load up
  token.transfer(second_user, deposit_amount, {"from": user})

  ## Deposit
  token.approve(real_vault, deposit_amount, {"from": second_user})
  tx = real_vault.deposit(deposit_amount, {"from": second_user})

  assert tx.gas_used < 210_000 ## 204513 from  tests

  chain.sleep(1200) ## Accrue some time so contract has to do extra math
  chain.mine()

  tx_transfer = real_vault.transfer(user, deposit_amount, {"from": second_user})

  assert tx_transfer.gas_used < 82_000 ## 81160

