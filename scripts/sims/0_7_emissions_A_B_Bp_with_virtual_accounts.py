from random import seed
from random import random

"""
  Visualization:
    https://miro.com/app/board/uXjVPfL1y3I=/
  
  Given TokenA -> RewardB -> RewardC

  General Case 2) Random Many to Many some are self-emitting (question is, do we need extra math or not?)

  e.g. (Full)
  From A -> B -> C
         -> B from B -> C from B from B
                   C -> C from C
                   C -> C from C from B from B

This Simulates A -> B -> B'
Where B and B' are not all for the depositors of A

  Token A can be Self-emitting or not (shouldn't matter) - TotalPoints
  (TODO: Math to prove self-emitting is reduceable to this case)

  
  NOTE: Working on B first to reach POC

  Token B self emits, is also emitted by Vault D and some people hold token B
  - VAULT_B_REWARDS_TO_A
  - VAULT_B_SELF_EMISSIONS
  - VAULT_B_EMISSIONS_TO_OTHER ## Emissions of B for another random vault (Vault D)

  Fix calculation to:
    - Give back "less rewards" directly to direct claimers <- Back to 04 math which is the correct one
    
    Future Rewards Backwards Claims
    - NEW: 
      Reward Positions will claim their rewards when claimed and distribute to users
        Effectively a Reward is a "Virtual Account" meaning just like any user it's accruing rewards
        Because of this, when claiming, we need to claim the rewards that this "Virtual Position" has accrued
        Doing this allows us to never correct the divisor to unfair / overly fair levels, at the cost of computational complexity
        NOTE: At this time  I believe this to be the mathematically correct solution

  - Add non-random version which will help with debugging


  Handle Virtual Accounts along with B -> B' to simulate the "smart contract" claims

  TODO: ADD C

  Token C self emits, is also emitted by Vault E and some people hold token C
  - VAULT_C_EMISSIONS_TO_B
  - VAULT_C_SELF_EMISSIONS
  - VAULT_C_EMISSIONS_TO_OTHER ## Emissions of C for another random vault (Vault E)
  - VAULT_C_HODLERS ## Users with direct deposits to C
"""

## Should we use randomness or use just the values provided?
DETERMINISTIC = False

## NOTE: a 1 epoch test MUST always pass
## because the issue of Future Rewards Backwards Claims is not relevant (there is no epoch of unclaimable rewards)
EPOCHS_RANGE = 0  ## Set to 0 to test specific epoch amounts
EPOCHS_MIN = 2

SHARES_DECIMALS = 18
RANGE = 10_000  ## Shares can be from 1 to 10k with SHARES_DECIMALS
MIN_SHARES = 1_000  ## Min shares per user
SECONDS_PER_EPOCH = 604800


### B VARS ###
MIN_VAULT_B_REWARDS_TO_A = (
    500  ## The "true" "base" yield from B -> A (without adding self-emissions)
)
VAULT_B_REWARDS_TO_A = 100_000  ## 100 k ETH example

## B'
VAULT_B_MIN_SELF_EMISSION = 500
VAULT_B_SELF_EMISSIONS = (
    1_000_000  ## 100M ETH example - Exacerbates issue with B -> B Claim
)

## Additional B Rewards (We call them D to separate)
VAULT_B_MIN_REWARDS_TO_OTHER = 500
VAULT_B_REWARDS_TO_OTHER = 100_000  ## Inflates total supply but is not added to rewards

## NOTE: Unused
## NOTE: See Math to prove we don't need as long as we have `VAULT_B_REWARDS_TO_OTHER`
# VAULT_B_HODLERS = 0


### C VARS - TODO ###
MIN_VAULT_C_EMISSIONS_TO_B = 1_000  ## 10 k ETH example
VAULT_C_EMISSIONS_TO_B = 100_000  ## 100 k ETH example

VAULT_C_SELF_EMISSIONS = 100_000  ## 100k ETH example
VAULT_C_EMISSIONS_TO_OTHER = (
    1_000_000  ## Inflates total supply but is not added to rewards
)
VAULT_C_HODLERS = 1_000_000  ## Inflates total supply and dilutes all emissions from C


USERS_RANGE = 0
USERS_MIN = 2000


## How many simulations to run?
ROUNDS = 1_000 if not DETERMINISTIC else 1

## Should the print_if_if print_if stuff?
SHOULD_PRINT = ROUNDS == 1


def print_if(v):
    if SHOULD_PRINT:
        print(v)


def multi_claim_sim():

    ##### SETUP #####

    ## Setup user and epochs
    number_of_epochs = (
        int(random() * EPOCHS_RANGE) + EPOCHS_MIN if not DETERMINISTIC else EPOCHS_MIN
    )
    number_of_users = (
        int(random() * USERS_RANGE) + USERS_MIN if not DETERMINISTIC else USERS_MIN
    )

    ## For fairness check at end
    total_user_deposits = 0
    total_user_points = 0

    ## How much of b was distributed
    total_claimed_b = 0

    total_dust_b = 0

    ## Stats / Temp Vars for simulation
    claiming = (
        []
    )  ## Is the user going to claim each week
    ##    HUNCH -> Not necessary as math is not interested in your balance but the virtual balance at that time

    claimers = 0

    initial_balances = []
    balances = []
    points_a = []
    total_supply_a = 0
    total_points_a = 0

    balances_b = []
    claimed_b = []  ## How much did each user get
    points_b = []  ## points_a[user][epoch]

    ##### SETUP USER #####

    ## Setup for users
    for user in range(number_of_users):
        ## Is User Claiming
        is_claiming = random() >= 0.5
        claimers += 1 if is_claiming else 0
        claiming.append(is_claiming)

        ## User Balance
        balance = (
            (int(random() * RANGE) + MIN_SHARES) * 10**SHARES_DECIMALS
            if not DETERMINISTIC
            else MIN_SHARES * 10**SHARES_DECIMALS
        )
        balances.append(balance)
        balances_b.append(0)

        ## NOTE: Balance is token A so no increase

        temp_list = []

        ## Add empty list for points_b
        for epoch in range(number_of_epochs):
            temp_list.append(0)

        points_b.append(temp_list)

        initial_balances.append(balance)
        total_user_deposits += balance
        claimed_b.append(0)

        user_points = balance * SECONDS_PER_EPOCH
        total_user_points += user_points
        points_a.append(user_points)

        total_supply_a += balance
        total_points_a += user_points

    ##### VERIFY A #####
    acc_total_points_a = 0
    for user in range(number_of_users):
        acc_total_points_a += points_a[user]

    assert total_points_a == acc_total_points_a

    ##### SETUP B #####

    total_rewards_b = 0  ## Rewards B
    rewards_b = []  ## Rewards per epoch B

    emissions_b_b = []  ## Emissions B' B -> B'
    total_emissions_b_b = 0  ## Total Emissions B'

    total_supply_b = 0  ## Actual total amount of b

    noise_rewards_b = []
    total_noise_rewards_b = 0

    for epoch in range(number_of_epochs):
        reward_b = (
            (int(random() * VAULT_B_REWARDS_TO_A) + MIN_VAULT_B_REWARDS_TO_A)
            * 10**SHARES_DECIMALS
            if not DETERMINISTIC
            else (MIN_VAULT_B_REWARDS_TO_A) * 10**SHARES_DECIMALS
        )
        rewards_b.append(reward_b)

        total_rewards_b += reward_b
        total_supply_b += reward_b

        ## Self-Emission B -> B - Only A% of these are claimable as reward, rest belongs to other depositors
        b_self_emissions_epoch = (
            (int(random() * VAULT_B_SELF_EMISSIONS) + VAULT_B_MIN_SELF_EMISSION)
            * 10**SHARES_DECIMALS
            if not DETERMINISTIC
            else (VAULT_B_MIN_SELF_EMISSION) * 10**SHARES_DECIMALS
        )

        emissions_b_b.append(b_self_emissions_epoch)
        total_emissions_b_b += b_self_emissions_epoch

        ## Increase total Supply
        total_supply_b += b_self_emissions_epoch

        ### Extra "noise stuff" to make simulation more accurate ###

        ## B Total Supply Inflated
        ## NOTE: Per this discussion: https://miro.com/app/board/uXjVPfL1y3I=/?share_link_id=823158446929
        ## We don't need to inflate totalSupply additionally
        ## As the case of A -> B -> B'
        ## And D -> B -> B' already modifies totalSupply
        ## And adding further noise doesn't prove anything else
        ## Beside the fact that the math for A and !A works as !A being D or being D + H is the same
        ## As cD + cD = D === cD for some c

        ## Emissions to another vault, inflate total_supply, do not increase rewards
        ## Rewards to Another Vault D -> B

        b_noise_rewards_epoch = (
            (int(random() * VAULT_B_REWARDS_TO_OTHER) + VAULT_B_MIN_REWARDS_TO_OTHER)
            * 10**SHARES_DECIMALS
            if not DETERMINISTIC
            else (VAULT_B_MIN_REWARDS_TO_OTHER) * 10**SHARES_DECIMALS
        )
        noise_rewards_b.append(b_noise_rewards_epoch)
        total_noise_rewards_b += b_noise_rewards_epoch

        total_supply_b += b_noise_rewards_epoch

    ## NOTE: Replaced the math above with this check, see math prove that this covers all cases
    assert (
        total_supply_b == total_rewards_b + total_noise_rewards_b + total_emissions_b_b
    )

    ###### Claim B from B - B -> B' #######
    total_claimed_self_emissions_b = 0

    total_points_b = total_supply_b * SECONDS_PER_EPOCH

    total_emissions_b_b_points = total_emissions_b_b * SECONDS_PER_EPOCH

    ## Find Cumulative points of rewards, so we can obtain circulating supply of B
    ## See 04 for simpler math
    ## * Circulating Supply could still be in the contract, but those points are handled via "virtual positions"

    emissions_b_b_points_cumulative_per_epoch = []

    for epoch in range(number_of_epochs):
        emissions_b_b_points_cumulative_per_epoch.append(total_emissions_b_b_points)

    acc = 0
    for epoch in range(number_of_epochs):
        ## Remove acc
        emissions_b_b_points_cumulative_per_epoch[epoch] -= acc

        ## Skip first one
        acc += emissions_b_b[epoch] * SECONDS_PER_EPOCH

    ## Emission Total Points on First Epoch === Total Contract Points
    assert emissions_b_b_points_cumulative_per_epoch[0] == total_emissions_b_b_points

    if number_of_epochs > 1:
        assert (
            emissions_b_b_points_cumulative_per_epoch[1]
            == total_emissions_b_b_points - emissions_b_b[0] * SECONDS_PER_EPOCH
        )

    ## Last Epoch Only points left are from last epoch
    assert (
        emissions_b_b_points_cumulative_per_epoch[-1]
        == emissions_b_b[-1] * SECONDS_PER_EPOCH
    )

    ## Claim D (Other B)
    ## Because we can, wlog, assume all the rewards are claimed by one person
    ## And we can assume no dust has happened, we can respect all constraints (<= total_noise_rewards_b) and still skip the needles math
    total_noise_b_claim = total_noise_rewards_b

    points_noise_claimed_points = []

    for epoch in range(number_of_epochs):
        points_noise_claimed_points.append(noise_rewards_b[epoch] * SECONDS_PER_EPOCH)

        ## Add points from previous epoch
        if epoch > 0:
            points_noise_claimed_points[epoch] += points_noise_claimed_points[epoch - 1]

    ## Sanity Check
    assert points_noise_claimed_points[-1] == total_noise_b_claim * SECONDS_PER_EPOCH
    assert points_noise_claimed_points[0] == noise_rewards_b[0] * SECONDS_PER_EPOCH

    if len(points_noise_claimed_points) > 1:
        assert (
            points_noise_claimed_points[1]
            == noise_rewards_b[0] * SECONDS_PER_EPOCH
            + noise_rewards_b[1] * SECONDS_PER_EPOCH
        )

    ###### D VIRTUAL ACCOUNTS ######
    total_emissions_claimed_by_noise = 0

    ## Acc to add to future
    prev_epoch_noise_claimed = 0

    for epoch in range(number_of_epochs):
        divisor = total_points_b - emissions_b_b_points_cumulative_per_epoch[epoch]

        this_epoch_points = prev_epoch_noise_claimed + points_noise_claimed_points[epoch]

        user_total_rewards_fair = (
            emissions_b_b[epoch] * this_epoch_points // divisor
        )
        user_total_rewards_dust = (
            emissions_b_b[epoch] * this_epoch_points % divisor
        )

        claimed_points = user_total_rewards_fair * SECONDS_PER_EPOCH
        ## Add new rewards to user points for next epoch
        ## Port over old points (cumulative) + add the claimed this epoch
        points_noise_claimed_points[epoch] += claimed_points

        ## Compounding accrual
        prev_epoch_noise_claimed += claimed_points

        total_emissions_claimed_by_noise += user_total_rewards_fair
        total_dust_b += user_total_rewards_dust

    ## total_emissions_claimed_by_noise are directly claimed


    

    ###### VIRTUAL ACCOUNTS ######

    ###### VIRTUAL ACCOUNTS ######
    ## Treat Future Rewards as if they are accounts, claiming each epoch and using those claims for each subsequent claim
    total_rewards_points_b = (
        total_noise_rewards_b * SECONDS_PER_EPOCH
    )  ## All points for all rewards
    unclaimable_points_rewards_b_epoch = []

    for epoch_index in range(number_of_epochs):
        unclaimable_points_rewards_b_epoch.append(total_rewards_points_b)

    acc = 0
    for epoch in range(number_of_epochs):
        ## Remove current epoch as we already claimed in A -> B -> B'
        acc += noise_rewards_b[epoch] * SECONDS_PER_EPOCH

        ## Remove acc
        unclaimable_points_rewards_b_epoch[epoch] -= acc

    virtual_account_d = 0
    for epoch_index in range(number_of_epochs):
        total_unclaimed_points = unclaimable_points_rewards_b_epoch[
            epoch_index
        ]  ## Unclaimed are future rewards receiving emissions from previous epochs

        ## HUNCH: I A -> B, is claiming the rewards
        ## B -> B' -> Claiming the emissions via the rewards
        ## THIS: Get the unclaimed rewards, and claim the emissions from them.
        ## Since we have A -> B and B -> B':
        ## A -> Works in spite of B -> B'
        ## While B -> B' requires the B claimable directly and the B' claimed retroactively

        ## Calculate rewards earned for epochs before `epoch_index`
        virtual_divisor = (
            total_points_b - emissions_b_b_points_cumulative_per_epoch[epoch_index]
        )  ## Same as for B -> B'

        rewards_earned = (
            emissions_b_b[epoch_index]
            * (total_unclaimed_points + virtual_account_d * SECONDS_PER_EPOCH)
            // virtual_divisor
        )

        virtual_account_d += rewards_earned

    virtual_account_rewards = 0

    ##### CLAIM B and B' and Virtual Accounts(B -> B') ######
    total_claimed_direct = 0

    for epoch in range(number_of_epochs):
        divisor = total_points_a  ## No subtraction as rewards are from A which is not self-emitting

        for user in range(number_of_users):

            user_total_rewards_fair = points_a[user] * rewards_b[epoch] // divisor
            user_total_rewards_dust = points_a[user] * rewards_b[epoch] % divisor

            balances_b[user] += user_total_rewards_fair

            ## When claiming A -> B
            ## Claim B -> B' from previous epochs
            ## Then use B to claim B -> B' current
            ## The B -> B' can be done later I think

            ## NOTE:
            ## user_total_rewards_fair becomes the virtual account
            ## We simulate recursively the emission claim it performed
            ## We claim it

            ## If Claim Epoch > 0 (epoch 1 or more)
            ## Reward from Epoch 1 -> Emissions from epoch 0
            ## Reward from Epoch 2 -> Emissions from Epoch 0 and Epoch 1, etc..
            ## Memoized Reward from Epoch N = Memoized Reward from Epoch N - 1
            ## If Epoch N - 1 = 0 -> Reward(Emission)

            #### MEMOIZED EMISSIONS FOR REWARD
            ## Claim VirtualAccount(Bi -> B')
            (
                current_virtual_reward_earned,
                current_virtual_reward_dust,
            ) = process_virtual_account_emissions(
                user_total_rewards_fair,
                total_points_b,
                emissions_b_b,
                emissions_b_b_points_cumulative_per_epoch,
                epoch,
            )

            virtual_account_rewards += current_virtual_reward_earned

            balances_b[user] += current_virtual_reward_earned

            #### PROCESS EMISSIONS FROM TOTAL BALANCE
            ## Claim B -> B'
            b_rewards_eligible_for_emissions = balances_b[
                user
            ]  ## old_epoch_bal + user_total_rewards_fair + current_virtual_reward_earned

            (
                current_epoch_emissions_earned,
                current_epoch_emissions_dust,
            ) = process_emissions_for_epoch(
                b_rewards_eligible_for_emissions,
                total_points_b,
                emissions_b_b,
                emissions_b_b_points_cumulative_per_epoch,
                epoch,
            )

            total_claimed_self_emissions_b += current_epoch_emissions_earned

            ## Increase by received so it's used for next epoch
            balances_b[user] += current_epoch_emissions_earned

            ## Add the rewards + virtual_accounts emissions + emissions claimed this epoch
            claimed_points = (
                user_total_rewards_fair * SECONDS_PER_EPOCH
                + current_virtual_reward_earned * SECONDS_PER_EPOCH
                + current_epoch_emissions_earned * SECONDS_PER_EPOCH
            )

            ## Add new rewards to user points_a for next epoch
            ## Port over old points_a (cumulative) + add the claimed this epoch
            old_points = points_b[user][epoch - 1] if epoch > 0 else 0
            points_b[user][epoch] = old_points + claimed_points

            total_claimed_b += user_total_rewards_fair
            total_dust_b += user_total_rewards_dust

            total_claimed_direct += user_total_rewards_fair

        ## Ensure basic math is correct, all rewards are claimed
    assert total_claimed_b / total_rewards_b * 100 == 100
    assert total_rewards_b >= total_claimed_direct  ## Check of fairness

    ## Run a check to verify that all claimable tokens for users are properly claimed as expected
    ## e.g. total_claimed_from_above approx total_claimable_by_A_holders
    expected_total_emissions_claimed = (total_emissions_b_b * total_rewards_b) // (total_rewards_b + total_noise_rewards_b)

    ## NOTE: We add emission + virtual account as virtual account are only emissions, but accounted separately    
    ## Test: We didn't give more than expected = We do not leak value
    assert (total_claimed_self_emissions_b + virtual_account_rewards) <= expected_total_emissions_claimed
    ## Test: We gave as close to theoretical as allowed by rounding
    assert (total_claimed_self_emissions_b + virtual_account_rewards) / expected_total_emissions_claimed * 100 == 100

    ## Use if in case you test with zero-emissions
    total_emissions_claimed = total_claimed_self_emissions_b + total_emissions_claimed_by_noise + virtual_account_d
    if total_emissions_b_b > 0:
        
        print("total_claimed_self_emissions_b")
        print((total_emissions_claimed) / total_emissions_b_b * 100)
        print("virtual_account_rewards")
        print(virtual_account_rewards / total_emissions_b_b * 100)

        print(
            "total_emissions_claimed_by_noise + total_claimed_self_emissions_b + virtual_account_rewards / total_emissions_b_b * 100"
        )
        print(
            (total_emissions_claimed + virtual_account_rewards)
            / total_emissions_b_b
            * 100
        )
        ## Is math VERY accurate (total - dust) ## NOTE: More accuracy magnitude is done via the return value
        assert (
            total_emissions_claimed + virtual_account_rewards
        ) / total_emissions_b_b * 100 > 99.999999
        ## Check that we never give more emissions than possible
        assert (
            total_emissions_claimed + virtual_account_rewards
        ) <= total_emissions_b_b

    ## Amount (total - claimed) / total = approx of rounding errors

    ## NOTE: Added math for D -> B'
    total_b_obtainable = total_emissions_b_b + total_rewards_b + total_noise_rewards_b
    return (
        total_b_obtainable
        - (
            total_noise_b_claim
            + total_claimed_b
            + total_emissions_claimed
            + virtual_account_rewards
        )
    ) / (total_b_obtainable)


def main():
    fair_count = 0
    for x in range(ROUNDS):
        res = multi_claim_sim()
        if res < 1e-18:
            fair_count += 1
        else:
            print("Unfair")
            print(res)

    print("Overall number of passing tests")
    print(fair_count)
    print("Overall Percent of passing tests")
    print(fair_count / ROUNDS * 100)


def process_virtual_account_emissions(
    user_rewards,
    total_points_b,
    emissions_b_b,
    emissions_b_b_points_cumulative_per_epoch,
    epoch,
):
    """
    user_rewards -> Rewards the user got at epoch
    total_points_b -> All points for token b (Math V1 Divisor)
    emissions_b_b -> All emissions by epoch

    emissions_b_b_points_cumulative_per_epoch -> Cumulative points of emissions
        Used to calculate the Circulating Supply from Contract POV
    epoch -> Current epoch

    We will calculate rewards for all emissions from epoch 0 to epoch - 1
    """

    ## We know this because the reward has been sitting in the sim since beginning
    reward_points = user_rewards * SECONDS_PER_EPOCH

    ## NOTE: For Real Contract first-epoch time will always be less than max, we'll have to deal with the extra math in the impl
    ##  We can do this wlog because there exists a c for which cT' * S === T * S === T * cS'

    virtual_total_reward = 0
    virtual_total_dust = 0
    for old_epoch in range(epoch):
        divisor = total_points_b - emissions_b_b_points_cumulative_per_epoch[old_epoch]

        user_total_rewards_fair = emissions_b_b[old_epoch] * reward_points // divisor
        user_total_rewards_dust = emissions_b_b[old_epoch] * reward_points % divisor

        claimed_points = user_total_rewards_fair * SECONDS_PER_EPOCH

        ## Add points for next epoch as we simulate full claim
        reward_points += claimed_points

        virtual_total_reward += user_total_rewards_fair
        virtual_total_dust += user_total_rewards_dust

    return (virtual_total_reward, virtual_total_dust)


def process_emissions_for_epoch(
    b_rewards_eligible_for_emissions,
    total_points_b,
    emissions_b_b,
    emissions_b_b_points_cumulative_per_epoch,
    epoch,
):
    """
    b_rewards_eligible_for_emissions -> Rewards the user got at epoch
    total_points_b -> All points for token b (Math V1 Divisor)
    emissions_b_b -> All emissions by epoch

    emissions_b_b_points_cumulative_per_epoch -> Cumulative points of emissions
        Used to calculate the Circulating Supply from Contract POV
    epoch -> Current epoch

    We will calculate claimable emissions for this epoch only
    """

    ## We know this because the reward has been sitting in the sim since beginning
    reward_points = b_rewards_eligible_for_emissions * SECONDS_PER_EPOCH

    ## NOTE: For Real Contract first-epoch time will always be less than max, we'll have to deal with the extra math in the impl
    ##  We can do this wlog because there exists a c for which cT' * S === T * S === T * cS'

    total_reward = 0
    total_dust = 0

    divisor = total_points_b - emissions_b_b_points_cumulative_per_epoch[epoch]

    user_total_rewards_fair = emissions_b_b[epoch] * reward_points // divisor
    user_total_rewards_dust = emissions_b_b[epoch] * reward_points % divisor

    total_reward += user_total_rewards_fair
    total_dust += user_total_rewards_dust

    return (total_reward, total_dust)
