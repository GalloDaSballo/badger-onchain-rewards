import brownie
from brownie import *
from helpers.utils import (
    approx,
)

AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2**256 - 1))

"""
  A set of exploits based on:
  https://docs.google.com/document/d/1bO2XfwQ60wQWePihgJu6UsukimI5ygTmC1rBTMGGNp0/edit#
  NOTE: The attacks where available at commit: fb02070c919dd19f7f3ba5e2b2cfe9b4e394c1aa
  These tests now verify the proper patching of them
"""


## Deposit -> Accrue epoch in future moves the balance to it and breaks the system
def test_accrue_future_balance_out_of_whack(
    initialized_contract, user, fake_vault, token
):
    INITIAL_DEPOSIT = 1e18
    REWARD_AMOUNT = 1e20
    EPOCH = initialized_contract.currentEpoch()

    ## Because user has the tokens too, we check the balance here
    initial_reward_balance = token.balanceOf(user)

    ## Only deposit so we get 100% of rewards
    initialized_contract.notifyTransfer(
        AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault}
    )

    ## Accrue next epoch
    ## Fixed to revert
    with brownie.reverts():
        initialized_contract.accrueUser(EPOCH + 1, fake_vault, user)

    ## Then withdraw
    initialized_contract.notifyTransfer(
        user, AddressZero, INITIAL_DEPOSIT, {"from": fake_vault}
    )

    ## Current epoch balance is 0
    assert initialized_contract.getBalanceAtEpoch(EPOCH, fake_vault, user)[0] == 0

    ## Future epoch baalnce is INITIAL_DEPOSIT ## fixed because can't accrue future
    with brownie.reverts():
        assert (
            initialized_contract.getBalanceAtEpoch(EPOCH + 1, fake_vault, user)[0] == 0
        )

    ## Go next epoch
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    ## Deposit only: INITIAL_DEPOSIT
    initialized_contract.notifyTransfer(
        AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault}
    )

    ## See that you have the correct balance
    assert (
        initialized_contract.getBalanceAtEpoch(EPOCH + 1, fake_vault, user)[0]
        == INITIAL_DEPOSIT
    )


## Deposit -> Accrue epoch in future moves the balance to it and breaks the system
def test_accrue_future_breaks_time_left_to_accrue(
    initialized_contract, user, fake_vault, token
):
    INITIAL_DEPOSIT = 1e18
    REWARD_AMOUNT = 1e20
    EPOCH = initialized_contract.currentEpoch()

    ## Because user has the tokens too, we check the balance here
    initial_reward_balance = token.balanceOf(user)

    ## Only deposit so we get 100% of rewards
    initialized_contract.notifyTransfer(
        AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault}
    )

    ## Accrue next epoch
    ## Fixed to revert
    with brownie.reverts():
        initialized_contract.accrueUser(EPOCH + 1, fake_vault, user)

    ## Then withdraw
    initialized_contract.notifyTransfer(
        user, AddressZero, INITIAL_DEPOSIT, {"from": fake_vault}
    )

    ## Current epoch balance is 0
    assert initialized_contract.getBalanceAtEpoch(EPOCH, fake_vault, user)[0] == 0

    ## Future epoch baalnce is INITIAL_DEPOSIT | Reverts
    with brownie.reverts():
        assert (
            initialized_contract.getBalanceAtEpoch(EPOCH + 1, fake_vault, user)[0] == 0
        )

    ## Go next epoch
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    ## Sleep more so we have a full epoch to accrue
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    ## See that you have twice the balance
    assert (
        initialized_contract.getUserTimeLeftToAccrue(EPOCH + 1, fake_vault, user)
        == initialized_contract.SECONDS_PER_EPOCH()
    )
