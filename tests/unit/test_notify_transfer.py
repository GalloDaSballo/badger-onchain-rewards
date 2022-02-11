import brownie
from brownie import *
from helpers.utils import (
    approx,
)
AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

"""
  TODO: 
  Deposit
  Withdraw
  Transfer
"""


def test_a_deposit_increases_user_balance_and_total_supply(initialized_contract, user, fake_vault, token):
  EPOCH = 1
  INITIAL_DEPOSIT = 1e18
  SECOND_AMOUNT = 3e18

  initialized_contract.notifyTransfer(INITIAL_DEPOSIT, AddressZero, user, {"from": fake_vault})

  assert initialized_contract.shares(EPOCH, fake_vault, user) == INITIAL_DEPOSIT
  assert initialized_contract.totalSupply(EPOCH, fake_vault) == INITIAL_DEPOSIT

  initialized_contract.notifyTransfer(SECOND_AMOUNT, AddressZero, user, {"from": fake_vault})

  assert initialized_contract.shares(EPOCH, fake_vault, user) == INITIAL_DEPOSIT + SECOND_AMOUNT
  assert initialized_contract.totalSupply(EPOCH, fake_vault) == INITIAL_DEPOSIT + SECOND_AMOUNT




def test_a_transfer_reduces_user_balance_increases_recipient_balance_total_supply_unchanged(initialized_contract, user, second_user, fake_vault, token):
  EPOCH = 1
  INITIAL_DEPOSIT = 1e18
  SECOND_AMOUNT = 3e18
  THIRD_AMOUNT = 6e18

  ## User mints
  initialized_contract.notifyTransfer(INITIAL_DEPOSIT, AddressZero, user, {"from": fake_vault})

  ## User transferred to `second_user`
  initialized_contract.notifyTransfer(INITIAL_DEPOSIT, user, second_user, {"from": fake_vault})

  assert initialized_contract.shares(EPOCH, fake_vault, user) == 0
  assert initialized_contract.shares(EPOCH, fake_vault, second_user) == INITIAL_DEPOSIT
  assert initialized_contract.totalSupply(EPOCH, fake_vault) == INITIAL_DEPOSIT

  ## Second User Mints
  initialized_contract.notifyTransfer(SECOND_AMOUNT, AddressZero, second_user, {"from": fake_vault})

  assert initialized_contract.shares(EPOCH, fake_vault, second_user) == INITIAL_DEPOSIT + SECOND_AMOUNT
  assert initialized_contract.totalSupply(EPOCH, fake_vault) == INITIAL_DEPOSIT + SECOND_AMOUNT

  ## First user mints
  initialized_contract.notifyTransfer(THIRD_AMOUNT, AddressZero, user, {"from": fake_vault})

  assert initialized_contract.shares(EPOCH, fake_vault, user) == THIRD_AMOUNT
  assert initialized_contract.shares(EPOCH, fake_vault, second_user) == INITIAL_DEPOSIT + SECOND_AMOUNT
  assert initialized_contract.totalSupply(EPOCH, fake_vault) == INITIAL_DEPOSIT + SECOND_AMOUNT + THIRD_AMOUNT

  ## Transfer half to user two
  initialized_contract.notifyTransfer(THIRD_AMOUNT / 2, user, second_user, {"from": fake_vault})

  ## totalSupply didn't change
  assert initialized_contract.totalSupply(EPOCH, fake_vault) == INITIAL_DEPOSIT + SECOND_AMOUNT + THIRD_AMOUNT
  ## Shares did
  assert initialized_contract.shares(EPOCH, fake_vault, user) == THIRD_AMOUNT / 2
  assert initialized_contract.shares(EPOCH, fake_vault, second_user) == INITIAL_DEPOSIT + SECOND_AMOUNT + THIRD_AMOUNT / 2


def test_a_withdrawal_reduces_user_balance_and_total_supply(initialized_contract, user, fake_vault, token):
  EPOCH = 1
  INITIAL_DEPOSIT = 1e18
  SECOND_AMOUNT = 3e18
  THIRD_AMOUNT = 6e18

  ## User mints
  initialized_contract.notifyTransfer(INITIAL_DEPOSIT, AddressZero, user, {"from": fake_vault})

  assert initialized_contract.shares(EPOCH, fake_vault, user) == INITIAL_DEPOSIT
  assert initialized_contract.totalSupply(EPOCH, fake_vault) == INITIAL_DEPOSIT

  ## Mint second amount
  initialized_contract.notifyTransfer(SECOND_AMOUNT, AddressZero, user, {"from": fake_vault})

  assert initialized_contract.shares(EPOCH, fake_vault, user) == INITIAL_DEPOSIT + SECOND_AMOUNT
  assert initialized_contract.totalSupply(EPOCH, fake_vault) == INITIAL_DEPOSIT + SECOND_AMOUNT

  ## Burn second amount
  initialized_contract.notifyTransfer(SECOND_AMOUNT, user, AddressZero, {"from": fake_vault})
  
  ## Second amount has been detracted
  assert initialized_contract.shares(EPOCH, fake_vault, user) == INITIAL_DEPOSIT
  assert initialized_contract.totalSupply(EPOCH, fake_vault) == INITIAL_DEPOSIT

  ## Burn First amount 
  initialized_contract.notifyTransfer(INITIAL_DEPOSIT, user, AddressZero, {"from": fake_vault})

  ## Total supply and deposits are zero
  assert initialized_contract.shares(EPOCH, fake_vault, user) == 0
  assert initialized_contract.totalSupply(EPOCH, fake_vault) == 0


def test_deposit_reverts():
  """
    I don't believe there's a way to make deposit revert by themselves
    If you can figure it out, reach out to alex@badger.finance
  """

  assert True

def test_withdrawal_reverts(initialized_contract, user, fake_vault, token):
  """
    I don't believe there's a way to make deposit revert by themselves
    If you can figure it out, reach out to alex@badger.finance
  """
  INITIAL_DEPOSIT = 1e18
  SECOND_AMOUNT = 3e18

  ## Revert if you withdraw when you got nothing
  with brownie.reverts():
    initialized_contract.notifyTransfer(INITIAL_DEPOSIT, user, AddressZero, {"from": fake_vault})
  
  ## Revert if after a deposit you withdraw too much
  ## Depoit INIITAL
  initialized_contract.notifyTransfer(INITIAL_DEPOSIT, AddressZero, user, {"from": fake_vault})
  ## Withdraw SECOND (too much)
  with brownie.reverts():
    initialized_contract.notifyTransfer(SECOND_AMOUNT, user, AddressZero, {"from": fake_vault})

  
def test_transfer_reverts(initialized_contract, user, fake_vault, second_user, token):

  """
    I don't believe there's a way to make deposit revert by themselves
    If you can figure it out, reach out to alex@badger.finance
  """
  
  INITIAL_DEPOSIT = 1e18
  SECOND_AMOUNT = 3e18

  ## Revert if you transfer without depositing first
  with brownie.reverts():
    initialized_contract.notifyTransfer(INITIAL_DEPOSIT, user, second_user, {"from": fake_vault})

  ## Revert if after a deposit you transfer too much
  ## Depoit INIITAL
  initialized_contract.notifyTransfer(INITIAL_DEPOSIT, AddressZero, user, {"from": fake_vault})
  ## Withdraw SECOND (too much)
  with brownie.reverts():
    initialized_contract.notifyTransfer(SECOND_AMOUNT, user, second_user, {"from": fake_vault})

  ## Revert if after a withdrawal, you transfer too much
  initialized_contract.notifyTransfer(INITIAL_DEPOSIT, user, AddressZero, {"from": fake_vault})

  ## Both too much or exact will revert as we withdrew
  with brownie.reverts():
    initialized_contract.notifyTransfer(SECOND_AMOUNT, user, second_user, {"from": fake_vault})
  with brownie.reverts():
    initialized_contract.notifyTransfer(INITIAL_DEPOSIT, user, second_user, {"from": fake_vault})

