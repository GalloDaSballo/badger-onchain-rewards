import brownie
from brownie import *

AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2**256 - 1))

"""
  Changing epoch allows to retrieve previous balances 
"""


def test_epoch_zero_doesnt_exist(rewards_contract, user, fake_vault):
    """
    Epoch 0 is meant to represent undefined
    And post deployment is not reacheable
    """
    assert rewards_contract.currentEpoch() > 0


def test_epoch_changes_balances_are_preserved(initialized_contract, user, fake_vault):
    """
    This test proves that balances are preserved across epochs
    """
    epoch = 1
    ## We start in epoch 1
    assert initialized_contract.currentEpoch() == epoch

    INITIAL_DEPOSIT = 1e18

    initialized_contract.notifyTransfer(
        AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault}
    )

    assert initialized_contract.shares(epoch, fake_vault, user) == INITIAL_DEPOSIT
    assert (
        initialized_contract.getBalanceAtEpoch(epoch, fake_vault, user)[0]
        == INITIAL_DEPOSIT
    )

    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    new_epoch = 2

    assert initialized_contract.currentEpoch() == new_epoch

    ## For this epoch it won't be there (as we don't look back to epoch 0)
    assert (
        initialized_contract.getBalanceAtEpoch(new_epoch, fake_vault, user)[0]
        == INITIAL_DEPOSIT
    )  ## Invariant is maintained

    ## Do it again to proove it's not a fluke
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    new_epoch = 3

    assert initialized_contract.currentEpoch() == new_epoch

    ## For this epoch it won't be there (as we don't look back to epoch 0)
    assert (
        initialized_contract.getBalanceAtEpoch(new_epoch, fake_vault, user)[0]
        == INITIAL_DEPOSIT
    )  ## Invariant is maintained


def test_epoch_changes_balances_are_preserved_after_tons_of_epochs(
    initialized_contract, user, fake_vault
):
    epoch = 1
    ## We start in epoch 1
    assert initialized_contract.currentEpoch() == epoch

    INITIAL_DEPOSIT = 1e18

    initialized_contract.notifyTransfer(
        AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault}
    )

    assert initialized_contract.shares(epoch, fake_vault, user) == INITIAL_DEPOSIT

    ## Wait 6 epochs
    for x in range(1, 6):
        chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
        chain.mine()

    ## See if we get the balance
    ## Old Epoch Balance is still there (no storage changes)
    assert initialized_contract.shares(epoch, fake_vault, user) == INITIAL_DEPOSIT

    current_epoch = initialized_contract.currentEpoch()
    ## New Current Epoch Balance is not there
    assert initialized_contract.shares(current_epoch, fake_vault, user) == 0

    ## Balance was correctly ported over
    assert (
        initialized_contract.getBalanceAtEpoch(current_epoch, fake_vault, user)[0]
        == INITIAL_DEPOSIT
    )


def test_epoch_changes_balances_are_preserved_and_change_properly_after_tons_of_epochs(
    initialized_contract, user, fake_vault
):
    epoch = 1
    ## We start in epoch 0
    assert initialized_contract.currentEpoch() == epoch

    INITIAL_DEPOSIT = 1e18

    initialized_contract.notifyTransfer(
        AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault}
    )

    assert initialized_contract.shares(epoch, fake_vault, user) == INITIAL_DEPOSIT

    ## Wait 6 epochs
    for x in range(1, 6):
        chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
        chain.mine()

    SECOND_DEPOSIT = 3e18

    initialized_contract.notifyTransfer(
        AddressZero, user, SECOND_DEPOSIT, {"from": fake_vault}
    )

    ## See if we get the balance
    ## Old Epoch Balance is still there (no storage changes)
    assert initialized_contract.shares(epoch, fake_vault, user) == INITIAL_DEPOSIT

    current_epoch = initialized_contract.currentEpoch()
    ## New Current Epoch Balance is already there, as `notifyTransfer` accrues and sets up shares automatically
    assert (
        initialized_contract.shares(current_epoch, fake_vault, user)
        == INITIAL_DEPOSIT + SECOND_DEPOSIT
    )

    ## Wait until end of epoch and do another transfer to check if time can break this property
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    THIRD_DEPOSIT = 6e18
    ## This transfer happens an epoch after
    initialized_contract.notifyTransfer(
        AddressZero, user, THIRD_DEPOSIT, {"from": fake_vault}
    )

    assert (
        initialized_contract.shares(current_epoch + 1, fake_vault, user)
        == INITIAL_DEPOSIT + SECOND_DEPOSIT + THIRD_DEPOSIT
    )
    assert (
        initialized_contract.shares(current_epoch, fake_vault, user)
        == INITIAL_DEPOSIT + SECOND_DEPOSIT
    )
