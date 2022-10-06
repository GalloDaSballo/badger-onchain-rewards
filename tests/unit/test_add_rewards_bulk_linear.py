import brownie
from brownie import *

AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2**256 - 1))

"""
  Checks that rewards are properly set via `addBulkRewardsLinearly`
"""


def test_basic_add_reward_linear(initialized_contract, user, fake_vault, token):
    REWARD_AMOUNT = 1e18
    token.approve(initialized_contract, MaxUint256, {"from": user})
    ## Add reward for just epoch 1
    initialized_contract.addBulkRewardsLinearly(
        1, 1, fake_vault, token, REWARD_AMOUNT, {"from": user}
    )

    assert initialized_contract.rewards(1, fake_vault, token) == REWARD_AMOUNT
    assert (
        initialized_contract.rewards(1, fake_vault, AddressZero) == 0
    )  ## Only added to token index

    SECOND_REWARD_AMOUNT = 16e19

    initialized_contract.addBulkRewardsLinearly(
        1, 1, fake_vault, token, SECOND_REWARD_AMOUNT, {"from": user}
    )

    assert (
        initialized_contract.rewards(1, fake_vault, token)
        == REWARD_AMOUNT + SECOND_REWARD_AMOUNT
    )


def test_basic_add_multiple_rewards_linear(
    initialized_contract, user, fake_vault, token
):
    REWARD_AMOUNT = 1e18
    token.approve(initialized_contract, MaxUint256, {"from": user})
    initialized_contract.addBulkRewardsLinearly(
        1, 1, fake_vault, token, REWARD_AMOUNT, {"from": user}
    )

    assert initialized_contract.rewards(1, fake_vault, token) == REWARD_AMOUNT

    ## You can add more than once
    initialized_contract.addBulkRewardsLinearly(
        1, 2, fake_vault, token, REWARD_AMOUNT * 2, {"from": user}
    )
    assert (
        initialized_contract.rewards(1, fake_vault, token)
        == REWARD_AMOUNT + REWARD_AMOUNT
    )  ## We added one more
    assert initialized_contract.rewards(2, fake_vault, token) == REWARD_AMOUNT


def test_must_have_balance_to_add(initialized_contract, user, fake_vault, wbtc):
    wbtc.approve(initialized_contract, MaxUint256, {"from": user})

    ## We have no wbtc, so this fails
    with brownie.reverts():
        initialized_contract.addBulkRewardsLinearly(
            2, 2, wbtc, fake_vault, 1000, {"from": user}
        )


def test_cant_add_rewards_in_the_past(initialized_contract, user, fake_vault, token):
    """
    Revert test for rewards in past epochs
    """
    REWARD_AMOUNT = 1e18
    token.approve(initialized_contract, MaxUint256, {"from": user})

    with brownie.reverts("Cannot add to past"):
        initialized_contract.addBulkRewardsLinearly(
            0, 1, fake_vault, token, REWARD_AMOUNT, {"from": user}
        )

    ## Wait the epoch to end
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    with brownie.reverts("Cannot add to past"):
        initialized_contract.addBulkRewardsLinearly(
            1, 1, fake_vault, token, REWARD_AMOUNT, {"from": user}
        )

    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    with brownie.reverts("Cannot add to past"):
        initialized_contract.addBulkRewardsLinearly(
            1, 2, fake_vault, token, REWARD_AMOUNT, {"from": user}
        )


def test_revert_if_not_divisible(initialized_contract, user, fake_vault, token):
    """
    Revert test for rewards not divisible by number of epochs
    """
    REWARD_AMOUNT = 1
    token.approve(initialized_contract, MaxUint256, {"from": user})

    with brownie.reverts("must divide evenly"):
        initialized_contract.addBulkRewardsLinearly(
            1, 2, fake_vault, token, REWARD_AMOUNT, {"from": user}
        )

    ## But works if it's divisible
    initialized_contract.addBulkRewardsLinearly(
        1, 2, fake_vault, token, REWARD_AMOUNT * 2, {"from": user}
    )


def test_revert_if_wrong_epoch_math(initialized_contract, user, fake_vault, token):
    """
    Revert test for rewards in past epochs
    """
    REWARD_AMOUNT = 1
    token.approve(initialized_contract, MaxUint256, {"from": user})

    ## Revert because no-epochs
    with brownie.reverts(""):
        initialized_contract.addBulkRewardsLinearly(
            2, 1, fake_vault, token, REWARD_AMOUNT, {"from": user}
        )

    ## Revert due to underflow
    with brownie.reverts(""):
        initialized_contract.addBulkRewardsLinearly(
            3, 1, fake_vault, token, REWARD_AMOUNT, {"from": user}
        )


## TODO: Add like 50 epochs of rewards and see what happens
