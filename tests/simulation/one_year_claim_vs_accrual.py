import brownie
from brownie import *
from helpers.utils import (
    approx,
)


AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2**256 - 1))

""""
  Simulate -> Depositing for one year
  -> Claiming rewards for one epoch after one year of inactivity
  -> Claiming rewards for all 52 epochs after one year of inactivity

  These tests should have been already implicitly done via the rest of the testing suite
  But this way we can estimate gas

  Rename the file to test_one_year_of_accrual to make this part of the testing suite
  I had to disable as I can't get tests to end when doing --gas and --coverage
"""


def test_full_deposit_claim_one_year_of_rewards_with_bulk_function_no_optimizations(
    initialized_contract, user, deployer, second_user, fake_vault, token
):
    INITIAL_DEPOSIT = 1e18
    REWARD_AMOUNT = 1e20
    EPOCH = initialized_contract.currentEpoch() + 51

    ## Because user has the tokens too, we check the balance here
    initial_reward_balance = token.balanceOf(user)
    initial_reward_balance_second = token.balanceOf(second_user)

    token.approve(initialized_contract, MaxUint256, {"from": deployer})

    ## Only deposit so we get 50% of rewards per user
    initialized_contract.notifyTransfer(
        AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault}
    )
    initialized_contract.notifyTransfer(
        AddressZero, second_user, INITIAL_DEPOSIT, {"from": fake_vault}
    )

    ## Wait 51 epochs
    for x in range(1, 52):
        initialized_contract.addReward(
            x, fake_vault, token, REWARD_AMOUNT, {"from": deployer}
        )

        if x > 1:
            ## Second User claims every week
            initialized_contract.claimRewardReferenceEmitting(
                x - 1, fake_vault, token, second_user
            )

        chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
        chain.mine()

    ## Wait out the last epoch so we can claim it
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    ## User 1 claims
    initialized_contract.claimBulkTokensOverMultipleEpochs(
        1, 51, fake_vault, [token], user, {"from": user}
    )
    initialized_contract.claimRewardReferenceEmitting(
        51, fake_vault, token, second_user
    )

    ## Compare balances at end
    delta_one = token.balanceOf(user) - initial_reward_balance
    delta_two = token.balanceOf(second_user) - initial_reward_balance_second
    assert (
        delta_one - delta_two < 1e18
    )  ## Less than one token billionth of a token (due to Brownie and how it counts for time)


def test_full_deposit_autocompouding_vault(
    initialized_contract, user, deployer, second_user, real_vault, token
):
    EPOCH = initialized_contract.currentEpoch() + 51

    total_bal = real_vault.balanceOf(user)

    ## Now each has 1/2
    real_vault.transfer(second_user, total_bal // 2, {"from": user})

    ## Dev will send rewards
    REWARD_AMOUNT = token.balanceOf(deployer) // EPOCH

    print("REWARD_AMOUNT")
    print(REWARD_AMOUNT)

    assert REWARD_AMOUNT > 0

    ## Because user has the tokens too, we check the balance here
    initial_reward_balance = real_vault.balanceOf(user)
    initial_reward_balance_second = real_vault.balanceOf(second_user)

    print("initial_reward_balance")
    print(initial_reward_balance)

    print("initial_reward_balance_second")
    print(initial_reward_balance_second)

    assert initial_reward_balance > 0
    assert initial_reward_balance_second > 0

    token.approve(real_vault, MaxUint256, {"from": deployer})
    real_vault.approve(initialized_contract, MaxUint256, {"from": deployer})

    ## Wait 51 epochs
    for x in range(1, 52):
        real_vault.deposit(REWARD_AMOUNT, {"from": deployer})
        initialized_contract.addReward(
            x, real_vault, real_vault, REWARD_AMOUNT, {"from": deployer}
        )

        if x > 1:
            ## Second User claims every week
            initialized_contract.claimRewardReferenceEmitting(
                x - 1, real_vault, real_vault, second_user
            )

            print("real_vault.balanceOf(user)")
            print(real_vault.balanceOf(user))

            print("real_vault.balanceOf(second_user)")
            print(real_vault.balanceOf(second_user))

        chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
        chain.mine()

    ## Wait out the last epoch so we can claim it
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    ## User 1 claims
    initialized_contract.tear([1, 51, real_vault, [real_vault]], {"from": user})
    initialized_contract.claimRewardReferenceEmitting(
        51, real_vault, real_vault, second_user
    )  ## Claim last epoch just to be sure

    ## Compare balances at end
    delta_one = real_vault.balanceOf(user) - initial_reward_balance
    delta_two = real_vault.balanceOf(second_user) - initial_reward_balance_second

    print("delta_one")
    print(delta_one)

    print("delta_two")
    print(delta_two)

    ## Around 6 times worse if you use these functions
    assert (
        delta_two / abs(delta_one - delta_two) < 3
    )  ## Two does get more tokens but they are less than 3 times the amt 1 gets
    assert abs(delta_one - delta_two) < REWARD_AMOUNT  ## Less than one week of claims
