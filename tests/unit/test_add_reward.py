import brownie
from brownie import *

AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2**256 - 1))

"""
  Checks that rewards are properly set via `addReward` and `addRewards`
"""


def test_basic_add_reward(initialized_contract, user, fake_vault, token):
    REWARD_AMOUNT = 1e18
    token.approve(initialized_contract, MaxUint256, {"from": user})
    initialized_contract.addReward(1, fake_vault, token, REWARD_AMOUNT, {"from": user})

    assert initialized_contract.rewards(1, fake_vault, token) == REWARD_AMOUNT
    assert (
        initialized_contract.rewards(1, fake_vault, AddressZero) == 0
    )  ## Only added to token index

    SECOND_REWARD_AMOUNT = 16e19

    initialized_contract.addReward(
        1, fake_vault, token, SECOND_REWARD_AMOUNT, {"from": user}
    )

    assert (
        initialized_contract.rewards(1, fake_vault, token)
        == REWARD_AMOUNT + SECOND_REWARD_AMOUNT
    )


def test_must_have_balance_to_add(initialized_contract, user, fake_vault, wbtc):
    wbtc.approve(initialized_contract, MaxUint256, {"from": user})

    ## We have no wbtc, so this fails
    with brownie.reverts():
        initialized_contract.addReward(2, wbtc, fake_vault, 1000, {"from": user})


def test_cant_add_rewards_in_the_past(initialized_contract, user, fake_vault, token):
    """
    Revert test for rewards in past epochs
    """
    REWARD_AMOUNT = 1e18
    token.approve(initialized_contract, MaxUint256, {"from": user})

    with brownie.reverts():
        initialized_contract.addReward(
            0, fake_vault, token, REWARD_AMOUNT, {"from": user}
        )

    ## Wait the epoch to end
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    with brownie.reverts():
        initialized_contract.addReward(
            1, fake_vault, token, REWARD_AMOUNT, {"from": user}
        )
