import brownie
from brownie import *
from helpers.utils import (
    approx,
)

AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2**256 - 1))

"""
  Tests for QSP-5

  - Overflowing Total Supply cannot happen
  - Overflowing of points cannot happen
"""


def test_cannot_overflow_total_supply(
    initialized_contract, deployer, user, fake_vault, token
):
    initialized_contract.notifyTransfer(
        AddressZero, user, MaxUint256, {"from": fake_vault}
    )

    ## Adding above total supply will overflow
    with brownie.reverts():
        initialized_contract.notifyTransfer(AddressZero, user, 1, {"from": fake_vault})


def test_cannot_overflow_points(
    initialized_contract, deployer, user, fake_vault, token
):

    EPOCH = initialized_contract.currentEpoch()

    ## Deposit max
    initialized_contract.notifyTransfer(
        AddressZero, user, MaxUint256, {"from": fake_vault}
    )

    chain.sleep(2)
    ## Will revert after 1 second has elapsed
    with brownie.reverts():
        initialized_contract.accrueVault(EPOCH, fake_vault, {"from": user})

    ## Any accrual of Vault must revert
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    ## Will also revert at end of epoch because seconds are > 1
    with brownie.reverts():
        initialized_contract.accrueVault(EPOCH, fake_vault, {"from": user})

    ## Additionally any function for claiming rewards should also revert as while the revert above prevents the storage to be changed
    ## The other functions that minimize storage usage are not going

    with brownie.reverts():
        initialized_contract.claimRewardReferenceEmitting(
            EPOCH, fake_vault, token, user, {"from": user}
        )

    with brownie.reverts():
        initialized_contract.claimRewardEmitting(
            EPOCH, fake_vault, token, user, {"from": user}
        )

    with brownie.reverts():
        initialized_contract.claimBulkTokensOverMultipleEpochs(
            EPOCH, EPOCH, fake_vault, [token], user, {"from": user}
        )

    with brownie.reverts():
        initialized_contract.reap([EPOCH, EPOCH, fake_vault, [token]], {"from": user})

    with brownie.reverts():
        initialized_contract.tear([EPOCH, EPOCH, fake_vault, [token]], {"from": user})
