from random import seed
from random import random
from copy import deepcopy

## TODO: Get objects / Maps so it's easier to handle

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

  Token B self emits, is also emitted by Vault β and some people hold token B
  - VAULT_B_REWARDS_TO_A
  - VAULT_B_SELF_EMISSIONS
  - VAULT_B_EMISSIONS_TO_OTHER ## Emissions of B for another random vault (Vault β)

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

  TODO: ADD C <- WIP

  Token C self emits, is also emitted by Vault E and some people hold token C
  - VAULT_C_REWARDS_TO_B
  - VAULT_C_SELF_EMISSIONS
  - VAULT_C_REWARDS_TO_OTHER ## Emissions of C for another random vault (Vault γ)
  - VAULT_C_HODLERS ## NOTE: Removed per cD' -> β explanation


  ## TODO 
  - Separate the noise / claims into functions
  - Use the functions for A -> B
  - Use the functions for B -> C


  - Add Noise back in

  - Rewrite all code to use list of tokens to make the random case more complicated
"""

## Should we use randomness or use just the values provided?
DETERMINISTIC = True

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

## Additional B Rewards (We call them β to separate) <- NOTE: May wanna remove noise for a time
VAULT_B_MIN_REWARDS_TO_OTHER = 0 ## TODO: Add back - Removed to nail down the math of claiming B -> C and C -> C'
VAULT_B_REWARDS_TO_OTHER = 100_000  ## Inflates total supply but is not added to rewards

## NOTE: Unused
## NOTE: See Math to prove we don't need as long as we have `VAULT_B_REWARDS_TO_OTHER`
# VAULT_B_HODLERS = 0


### C VARS ###
VAULT_C_MIN_REWARDS_TO_B = 0  ## 10 k ETH example
VAULT_C_REWARDS_TO_B = 0  ## 100 k ETH example

VAULT_C_MIN_SELF_EMISSIONS = 0  ## TODO: This must be 100% or I made a mistake
VAULT_C_SELF_EMISSIONS = 1_000  ## 1k ETH example

## NOTE: TODO - Zero to make initial sim simpler
## TODO: Add the math as it's not there yet
VAULT_C_MIN_REWARDS_TO_OTHER = 0
VAULT_C_REWARDS_TO_OTHER = (
    0  ## Inflates total supply but is not added to rewards
)



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

    ## How much of c was distributed
    total_claimed_c = 0
    total_dust_c = 0

    ## Stats / Temp Vars for simulation
    initial_balances = []
    balances = []
    points_a = []
    total_supply_a = 0
    total_points_a = 0

    balances_b = []
    claimed_b = []  ## How much did each user get
    points_b = []  ## points_b[user][epoch]

    balances_c = []
    claimed_c = []  ## How much did each user get
    points_c = []  ## points_b[user][epoch]

    ##### SETUP USER #####

    ## Setup for users
    for user in range(number_of_users):
        ## User Balance
        balance = (
            (int(random() * RANGE) + MIN_SHARES) * 10**SHARES_DECIMALS
            if not DETERMINISTIC
            else MIN_SHARES * 10**SHARES_DECIMALS
        )
        balances.append(balance)
        balances_b.append(0)
        balances_c.append(0)

        ## NOTE: Balance is token A so no increase

        temp_list = []

        ## Add empty list for points_b
        for epoch in range(number_of_epochs):
            temp_list.append(0)

        points_b.append(deepcopy(temp_list))
        points_c.append(deepcopy(temp_list))

        initial_balances.append(balance)
        total_user_deposits += balance
        claimed_b.append(0)
        claimed_c.append(0)

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
        ## And β -> B -> B' already modifies totalSupply
        ## And adding further noise doesn't prove anything else
        ## Beside the fact that the math for A and !A works as !A being β or being β + H is the same
        ## As cD + cD = β === cD for some c

        ## Emissions to another vault, inflate total_supply, do not increase rewards
        ## Rewards to Another Vault β -> B

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

    
    ##### SETUP C #####

    total_rewards_c = 0  ## Rewards C
    rewards_c = []  ## Rewards per epoch C

    emissions_c_c = []  ## Emissions C' C -> C'
    total_emissions_c_c = 0  ## Total Emissions C'

    total_supply_c = 0  ## Actual total amount of C

    noise_rewards_c = []
    total_noise_rewards_c = 0

    for epoch in range(number_of_epochs):
        reward_c = (
            ## TODO: ADD VARIABLES -> VAULT_C_REWARDS_TO_B rename too
            (int(random() * VAULT_C_REWARDS_TO_B) + MIN_VAULT_B_REWARDS_TO_A)
            * 10**SHARES_DECIMALS
            if not DETERMINISTIC
            else (MIN_VAULT_B_REWARDS_TO_A) * 10**SHARES_DECIMALS
        )
        rewards_c.append(reward_c)

        total_rewards_c += reward_c
        total_supply_c += reward_c

        ## Self-Emission C -> C' - Only (B + B')% of these are claimable as reward, rest belongs to other depositors
        ## TODO: Add claim / math for this
        c_self_emissions_epoch = (
            ## TODO: VARS
            (int(random() * VAULT_C_SELF_EMISSIONS) + VAULT_C_MIN_SELF_EMISSIONS)
            * 10**SHARES_DECIMALS
            if not DETERMINISTIC
            else (VAULT_C_MIN_SELF_EMISSIONS) * 10**SHARES_DECIMALS
        )

        emissions_c_c.append(c_self_emissions_epoch)
        total_emissions_c_c += c_self_emissions_epoch

        ## Increase total Supply
        total_supply_c += c_self_emissions_epoch

        ### Extra "noise stuff" to make simulation more accurate ###

        ## B Total Supply Inflated
        ## NOTE: Per this discussion: https://miro.com/app/board/uXjVPfL1y3I=/?share_link_id=823158446929
        ## We don't need to inflate totalSupply additionally
        ## As the case of A -> B -> B'
        ## And β -> B -> B' already modifies totalSupply
        ## And adding further noise doesn't prove anything else
        ## Beside the fact that the math for A and !A works as !A being β or being β + H is the same
        ## As cD + cD = β === cD for some c

        ## Emissions to another vault, inflate total_supply, do not increase rewards
        ## Rewards to Another Vault β -> B

        c_noise_rewards_epoch = (
            (int(random() * VAULT_C_REWARDS_TO_OTHER) + VAULT_C_MIN_REWARDS_TO_OTHER)
            * 10**SHARES_DECIMALS
            if not DETERMINISTIC
            else (VAULT_C_MIN_REWARDS_TO_OTHER) * 10**SHARES_DECIMALS
        )
        noise_rewards_c.append(c_noise_rewards_epoch)
        total_noise_rewards_c += c_noise_rewards_epoch

        total_supply_c += c_noise_rewards_epoch

    ## NOTE: Replaced the math above with this check, see math prove that this covers all cases
    assert (
        total_supply_c == total_rewards_c + total_noise_rewards_c + total_emissions_c_c
    )


    ###### Claim B from B - B -> B' #######

    ## TODO: Write this as reusable function

    total_claimed_self_emissions_b = 0

    total_points_b = total_supply_b * SECONDS_PER_EPOCH

    total_emissions_b_b_points = total_emissions_b_b * SECONDS_PER_EPOCH
    
    ##### B CIRCULATING SUPPLY MATH #####
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

    ## Claim β (Other B)
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

    ###### β VIRTUAL ACCOUNTS ######
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

    virtual_account_rewards_b = 0

    ##### CLAIM B and B' and Virtual Accounts(B -> B') ######
    total_claimed_direct_b = 0

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

            virtual_account_rewards_b += current_virtual_reward_earned

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

            total_claimed_direct_b += user_total_rewards_fair

        ## Ensure basic math is correct, all rewards are claimed
    assert total_claimed_b / total_rewards_b * 100 == 100
    assert total_rewards_b >= total_claimed_direct_b  ## Check of fairness

    ## Run a check to verify that all claimable tokens for users are properly claimed as expected
    ## e.g. total_claimed_from_above approx total_claimable_by_A_holders
    expected_total_emissions_claimed = (total_emissions_b_b * total_rewards_b) // (total_rewards_b + total_noise_rewards_b)

    ## NOTE: We add emission + virtual account as virtual account are only emissions, but accounted separately    
    ## Test: We didn't give more than expected = We do not leak value
    assert (total_claimed_self_emissions_b + virtual_account_rewards_b) <= expected_total_emissions_claimed
    ## Test: We gave as close to theoretical as allowed by rounding
    assert (total_claimed_self_emissions_b + virtual_account_rewards_b) / expected_total_emissions_claimed * 100 == 100

    ## Use if in case you test with zero-emissions
    total_emissions_claimed_b = total_claimed_self_emissions_b + total_emissions_claimed_by_noise + virtual_account_d
    if total_emissions_b_b > 0:
        
        print("total_claimed_self_emissions_b")
        print((total_emissions_claimed_b) / total_emissions_b_b * 100)
        print("virtual_account_rewards_b")
        print(virtual_account_rewards_b / total_emissions_b_b * 100)

        print(
            "total_emissions_claimed_by_noise + total_claimed_self_emissions_b + virtual_account_rewards_b / total_emissions_b_b * 100"
        )
        print(
            (total_emissions_claimed_b + virtual_account_rewards_b)
            / total_emissions_b_b
            * 100
        )
        ## Is math VERY accurate (total - dust) ## NOTE: More accuracy magnitude is done via the return value
        assert (
            total_emissions_claimed_b + virtual_account_rewards_b
        ) / total_emissions_b_b * 100 > 99.999999
        ## Check that we never give more emissions than possible
        assert (
            total_emissions_claimed_b + virtual_account_rewards_b
        ) <= total_emissions_b_b

    ## Amount (total - claimed) / total = approx of rounding errors


    ##### TODO: C MATH ######
    total_noise_c_claim = 0
    total_claimed_c = 0
    total_emissions_claimed_c = 0
    virtual_account_rewards_c = 0

    total_claimed_self_emissions_c = 0

    total_points_c = total_supply_c * SECONDS_PER_EPOCH

    total_emissions_c_c_points = total_emissions_c_c * SECONDS_PER_EPOCH

    ##### C CIRCULATING SUPPLY MATH #####
    ## Find Cumulative points of rewards, so we can obtain circulating supply of C
    ## * Circulating Supply could still be in the contract, but those points are handled via "virtual positions"

    emissions_c_c_points_cumulative_per_epoch = []

    for epoch in range(number_of_epochs):
        emissions_c_c_points_cumulative_per_epoch.append(total_emissions_c_c_points)

    acc = 0
    for epoch in range(number_of_epochs):
        ## Remove acc
        emissions_c_c_points_cumulative_per_epoch[epoch] -= acc

        ## Skip first one
        acc += emissions_c_c[epoch] * SECONDS_PER_EPOCH

    ## Emission Total Points on First Epoch === Total Contract Points
    assert emissions_c_c_points_cumulative_per_epoch[0] == total_emissions_c_c_points

    if number_of_epochs > 1:
        assert (
            emissions_c_c_points_cumulative_per_epoch[1]
            == total_emissions_c_c_points - emissions_c_c[0] * SECONDS_PER_EPOCH
        )

    ## Last Epoch Only points left are from last epoch
    assert (
        emissions_c_c_points_cumulative_per_epoch[-1]
        == emissions_c_c[-1] * SECONDS_PER_EPOCH
    )

    ##### CLAIM C and C' and Virtual Accounts(C -> C') ######
    total_claimed_direct_c = 0

    for epoch in range(number_of_epochs):
        ## TODO: B is self emitting so divisor is prob wrong
        ## TODO: Maybe instead of divisor being wrong (See Math-2A), we need virtual accounts for both B and B'
        divisor = total_points_b

        for user in range(number_of_users):
            user_total_rewards_fair = points_b[user][epoch] * rewards_c[epoch] // divisor
            user_total_rewards_dust = points_b[user][epoch] * rewards_c[epoch] % divisor

            balances_c[user] += user_total_rewards_fair

            ## TODO: Verify this copy pasta with replaced A => B, B => C is still correct
            ## When claiming B -> C
            ## Claim C -> C' from previous epochs
            ## Then use C to claim C -> C' current
            ## The C -> C' can be done later I think

            ## NOTE:
            ## user_total_rewards_fair becomes the virtual account
            ## We simulate recursively the emission claim it performed
            ## We claim it

            ## If Claim Epoch > 0 (epoch 1 or more)
            ## Reward from Epoch 1 -> Emissions from epoch 0
            ## Reward from Epoch 2 -> Emissions from Epoch 0 and Epoch 1, etc..
            ## Memoized Reward from Epoch N = Memoized Reward from Epoch N - 1
            ## If Epoch N - 1 = 0 -> Reward(Emission)

            ## TODO: Virtual Account of B -> B' -> C
            ## Take B + B' claimed
            ## They have been there since time X
            ## First epoch they were added is not necessarily complete time
            ## Any epoch after that will always be full time
            ## We will claim the rewards for them <- TODO
            ##  For each B and B' from Epoch n-1 calculate the amount of c that they can claim
            ##  Add that up so we can do virtual accounts below

            ### TODO: WRONG FIGURE OUT
            ## B to C version
            ## TODO: Write sim on paper
            (
                TEMP_virtual_account_b_c,
                current_virtual_reward_dust,
            ) = process_virtual_account_emissions(
                points_b[user][epoch],
                total_points_b,
                rewards_c,
                emissions_b_b_points_cumulative_per_epoch,
                epoch,
            )

            print("TEMP_virtual_account_b_c")
            print(TEMP_virtual_account_b_c)

            virtual_account_rewards_c += TEMP_virtual_account_b_c

            ## And we will claim the emissions that those rewards earned <- Already done, just update virtual account below


            #### MEMOIZED EMISSIONS FOR REWARD
            ## Claim VirtualAccount(Ci -> C')
            (
                current_virtual_reward_earned,
                current_virtual_reward_dust,
            ) = process_virtual_account_emissions(
                user_total_rewards_fair,
                total_points_c,
                emissions_c_c,
                emissions_c_c_points_cumulative_per_epoch,
                epoch,
            )

            virtual_account_rewards_c += current_virtual_reward_earned

            balances_c[user] += virtual_account_rewards_c

            #### PROCESS EMISSIONS FROM TOTAL BALANCE
            ## Claim C -> C'
            c_rewards_eligible_for_emissions = balances_c[
                user
            ]  ## old_epoch_bal + user_total_rewards_fair + current_virtual_reward_earned

            (
                current_epoch_emissions_earned,
                current_epoch_emissions_dust,
            ) = process_emissions_for_epoch(
                c_rewards_eligible_for_emissions,
                total_points_c,
                emissions_c_c,
                emissions_c_c_points_cumulative_per_epoch,
                epoch,
            )

            total_claimed_self_emissions_c += current_epoch_emissions_earned

            ## Increase by received so it's used for next epoch
            balances_c[user] += current_epoch_emissions_earned

            ## Add the rewards + virtual_accounts emissions + emissions claimed this epoch
            claimed_points = (
                user_total_rewards_fair * SECONDS_PER_EPOCH
                + current_virtual_reward_earned * SECONDS_PER_EPOCH
                + current_epoch_emissions_earned * SECONDS_PER_EPOCH
            )

            ## Add new rewards to user points_a for next epoch
            ## Port over old points_a (cumulative) + add the claimed this epoch
            old_points = points_c[user][epoch - 1] if epoch > 0 else 0
            points_c[user][epoch] = old_points + claimed_points

            total_claimed_c += user_total_rewards_fair + current_virtual_reward_earned + current_epoch_emissions_earned
            total_dust_c += user_total_rewards_dust

            total_claimed_direct_c += user_total_rewards_fair

        ## Ensure basic math is correct, all rewards are claimed
    
    print("total_claimed_c / total_rewards_c * 100")
    print(total_claimed_c / total_rewards_c * 100)
    assert total_claimed_c / total_rewards_c * 100 == 100
    assert total_rewards_c >= total_claimed_direct_c  ## Check of fairness




    ## NOTE: Added math for β -> B'
    total_b_obtainable = total_emissions_b_b + total_rewards_b + total_noise_rewards_b
    res_b = (total_b_obtainable - (
            total_noise_b_claim
            + total_claimed_b
            + total_emissions_claimed_b
            + virtual_account_rewards_b
        )
    ) / (total_b_obtainable)

    total_c_obtainable = total_emissions_c_c + total_rewards_c + total_noise_rewards_c
    res_c = (total_c_obtainable - (
            total_noise_c_claim
            + total_claimed_c
            + total_emissions_claimed_c
            + virtual_account_rewards_c
        )
    ) / (total_c_obtainable)
    return (res_b , res_c)


def main():
    fair_count = 0
    for x in range(ROUNDS):
        (res_b, res_c) = multi_claim_sim()
        if res_b < 1e-18 and res_c < 1e-18 :
            fair_count += 1
        else:
            print("Unfair")
            print(res_b)
            print(res_c)

    print("Overall number of passing tests")
    print(fair_count)
    print("Overall Percent of passing tests")
    print(fair_count / ROUNDS * 100)


def process_virtual_account_emissions(
    balance,
    total_points,
    self_emissions,
    self_emissions_points_cumulative_per_epoch,
    epoch,
):
    """
    balance -> Rewards the user got at epoch
    total_points -> All points for token b (Math V1 Divisor)
    self_emissions -> All emissions by epoch
    self_emissions_points_cumulative_per_epoch -> Cumulative points of emissions
        Used to calculate the Circulating Supply from Contract POV
    epoch -> Current epoch

    We will calculate rewards for all emissions from epoch 0 to epoch - 1
    """

    ## We know this because the reward has been sitting in the sim since beginning
    reward_points = balance * SECONDS_PER_EPOCH

    ## NOTE: For Real Contract first-epoch time will always be less than max, we'll have to deal with the extra math in the impl
    ##  We can do this wlog because there exists a c for which cT' * S === T * S === T * cS'

    virtual_total_reward = 0
    virtual_total_dust = 0
    for old_epoch in range(epoch):
        divisor = total_points - self_emissions_points_cumulative_per_epoch[old_epoch]

        user_total_rewards_fair = self_emissions[old_epoch] * reward_points // divisor
        user_total_rewards_dust = self_emissions[old_epoch] * reward_points % divisor

        claimed_points = user_total_rewards_fair * SECONDS_PER_EPOCH

        ## Add points for next epoch as we simulate full claim
        reward_points += claimed_points

        virtual_total_reward += user_total_rewards_fair
        virtual_total_dust += user_total_rewards_dust

    return (virtual_total_reward, virtual_total_dust)


def process_emissions_for_epoch(
    rewards,
    total_points,
    self_emissions,
    self_emissions_points_cumulative_per_epoch,
    epoch,
):
    """
    rewards -> Rewards the user got at epoch
    total_points -> All points for token b (Math V1 Divisor)
    self_emissions -> All emissions by epoch

    self_emissions_points_cumulative_per_epoch -> Cumulative points of emissions
        Used to calculate the Circulating Supply from Contract POV
    epoch -> Current epoch

    We will calculate claimable emissions for this epoch only
    """

    ## We know this because the reward has been sitting in the sim since beginning
    reward_points = rewards * SECONDS_PER_EPOCH

    ## NOTE: For Real Contract first-epoch time will always be less than max, we'll have to deal with the extra math in the impl
    ##  We can do this wlog because there exists a c for which cT' * S === T * S === T * cS'

    total_reward = 0
    total_dust = 0

    divisor = total_points - self_emissions_points_cumulative_per_epoch[epoch]

    user_total_rewards_fair = self_emissions[epoch] * reward_points // divisor
    user_total_rewards_dust = self_emissions[epoch] * reward_points % divisor

    total_reward += user_total_rewards_fair
    total_dust += user_total_rewards_dust

    return (total_reward, total_dust)





def get_circulating_supply_at_epoch(total_supply, rewards, emissions, epoch, claim_depth):
    """
        Given the rewards and emissions
        Figure out the circulating supply at that epoch

        `claim_depth`: {enum} - Used to retrieve the divisor that is appropriate to the math
        0 -> Rewards -> Math V1 - total_supply -> Used for All non-emission claims
        1 -> Only Emissions -> Multiple emissions means we need to remove them from the circulating supply

        Ultimately the problem is to figure out circulating_supply, which does change after time

    """

    ## Given depth we'll need to go deeper / less deep
    if claim_depth == 0:
        return total_supply
    
    if claim_depth == 1:
        ## Remove the rewards until this epoch
        ## Remove the emissions until this epoch
        total_emissions_future = emissions[epoch]

        return total_supply - total_emissions_future




## Get total Claimed

## Get Virtual Accounts total Claimed

## Claim from Virtual Accounts as % of total Claimed vs claimable

## If I know how many rewards are locked in contract, and will only be available in the future
## I can claim the emissions from those rewards and use the Ratio to distribute them
# 
# 
# 
#  Reward if A != B
#  Emission if A == B
#  I can always tell if it's an emission or a reward
#  Question is what happens if I can claim from Reward and Emission to new Rewards?


## How do we get Emissions?
## Circulating Supply (- reward_i - emission_i-1) -> And ratio


## How do we get Reward from Reward + Emission?
## Circulating Supply (- reward_i - emission_i) -> And ratio
## Both are i as after the claim they are both circulating


## If No Reward nor emission can be added to future epochs
## Then we have a guarantee that divisor = total_supply for all Rewards
## And divisor = total_supply - points_from_current_emissions for all Emissions

## It follows that for a given Reward of Reward C
## For which B -> B' -> C
## Then receivedC = receivedB + receivedB' / total_supply
## Because a rational actor will claim B -> B' -> C
## Even if they could claim B -> C and loose on some emissions
## Meaning that if an emission is available it must always be claimed first

## Corollary being:
## C1 - A -> B type deal
## If no future tokens (rewards or emissions for future epochs) are present in the contract
## Meaning no extra points are being accrued to the contract but are not claimable then
## Any A -> B type claim will always be divided by B / totalSupply



## Vault -> Reward -> Emission -> Reward -> Emission -> Reward -> Emission -> Reward -> Emission -> Reward -> Emission
"""
A set of claims is basically a path to claims, where the starting point is always Vault
The intermediary steps are the token (and it's emission if available, perhaps packable via `bool`)


    1) A -> B -> B' -> C -> C'
    2) A -> C -> C'
    3) A -> D -> D' -> C -> C'

    Can be resolved as:

    1)
    A -> B
    B -> B'
    B -> C
    C -> C'

    2) 
    A -> C
    C -> C'

    3)
    A -> D
    D -> D'
    D -> C
    C -> C'

A cache of token ratios may help save gas, however ultimately
A "compound claim" is the ordered claim of pair of tokens, accrued to the current epoch


Given Paths 1, 2 and 3
A gas optimized claim would do:
A -> B -> B' -> C
A -> C
A -> D -> D' -> C
C(1 + 2+ 3) -> C'

However it may be impossible to make this replicable for all cases


## NOTE: On Subsegments

X -> A -> *
Z -> A -> *

While this would be mathematically equivalent to
X -> A
Z -> A
A -> *

Because of the function interface starting with one vault, I'll be ignoring that.
If the starting vault is different, just do n claims for each starting node

The sum of all partial claims will be equal to the total claim (minus rounding due to integer division)
"""




"""
    Let Vs = {A, B, ...Z} be the vector of balances

    TVi being Total Supply for Vault V at epoch i === Sum(A)
    vni being balance of user n at epoch i; with vni <= Sum(A)

    R being a generic reward

    Given that all Ri is claimable on each epoch

    Compound Claims Theorem

    For Each V ∈ Vs:
        Claim(V, n, i) ===
        {
            vi / Tvi * Ri; if V != R; Rewards Case
            vi / (Tvi - Ri); if V == R; Emissions Case
        }

    
    Corollary 1 - Definition of Circulating Supply

    Let Tvi being the total Supply for V ∈ Vs at epoch i;

    We define circulating supply (from the Contract POV) as 
    the sum of all Vault shares owned by users, 
    or that are rewards that can be claimed through ownership of a different Vault D ∈ Vs; D != V

    Given V ∈ Vs and TRi as the Sum(Ri) for given epoch i;
    With R == V;

    We separate TRV = TR + TV
    Where TV is circulating and TR are emissions for it

    Because TRV = TR + TV

    We define Circulating supply as TV, the amount of Rewards that are not emissions for the given Vault



    Corollary 2 - Linear Extension

    For Each V ∈ VS; 
    There is no difference if we prove theorems with a vector of one or a vector of n ∈ N

    Proof by absurd:

    Imagine a R as value of rewards and Ri ∈ N; as the specific reward claimable for epoch i

    If Ri is claimable by a single vector N ∈ Vs, then TNi the total supply of N at epoch i maps out to Ri

    If we were to introduce an additional vector M ∈ Vs with 50% of the rewards being equally split between N and M
    Then we would assert that:

    TNi maps out to 50% Ri
    and
    TMi maps out to 50% Ri

    Meaning that for any ni <= TNi; with TNi == SUM(ni); There exist a value r ∈ N; That each share amount can claim

    We can extend this idea to any number of Vaults for any ratio of Rewards.

    Given Vsi and it's subsets and Ri being respectively:
    The permutations of all possible vaults at epoch i and
    The permutation of all possible rewards for each epoch i
    
    With TRi == SUM(Ri) == C * Ri

    Meaning there must be a C ∈ <Q> (Vector of Rational Numbers) that maps out a ratio between TRi and Ri

    If there was no vector, then by absurd, in the case of a single vault 
    The following must be true:
    There is no c ∈ N such that
    TNi == SUM(ni) can claim c * Ri

    This is absurd per the example above
"""


## How do we codify Segments?

"""
    Start
    ClaimDepth
    ClaimTokens1
    ClaimEmissionTokens1
    ...
    ...
    ClaimTokens_ClaimDepth-1
    ClaimEmissionTokens_ClaimDepth-1


    ## What happens if in the middle we have start again?
    ## What happens if we have the same subpath X times?



    RANDOM_CLAIM_DEPTH

    RANDOM_CLAIM_TOKEN_LAYER_1...RANDOM_CLAIM_TOKEN_LAYER_N
    RANDOM_CLAIM_EMISSION_LAYER_1...RANDOM_CLAIM_EMISSION_LAYER_N


    ## What happens if we have the same subpath X times?
    We just recompute it and pay the extra gas, per the logic above it's still the correct math in spite of it wasting gas


    ## What happens if in the middle we have start again?
    Then the entire path is a uber path to start

    N -> A -> M

    Meaning that Start should have been N and not A

    ## NOTE: Worth checking this on Solidity, is uberPath or something, as it's not gas efficient


    ## TODO: What happens on a cross?

    A -> B
    A -> C
    A -> D
    A -> D -> B

    B -> A
    B -> C
    B -> D

    As sum of paths

    A -> D -> B -> A
    A -> D -> B -> C
    A -> D -> B -> D

    In reality

    A -> D -> B -> A
              B -> C
              B -> D
    

    A -> D
    D -> B

    B -> A
    B -> C
    B -> D

    D -> B ??? TODO: This is where problem arise

    ## RULE: We must revert if you claim the same pair / path twice

    ## What happens if something is a recursive sub path of something else
    ## What math would help?
"""

## Vault / Token Notation | TokenData

"""
    For the purposes of this sim:

    A -> B -> B' -> C -> C'

    Where each of them will have
    {
        ## For each epoch each user. After a claim, increase current
        ## At beginning of new epoch, port over from prev epoch bal
        ## balances[epoch][user] = balances[epoch-1][user]
        balances[epoch][user]: 

        ## How many rewards available this epoch
        rewards[epoch][token]

        ## How many emissions available this epoch (emission = reward for holding vault)
        emissions[epoch]

        ## Sum of balances + rewards + emissions
        total_supply[epoch]: 
    }
"""

class Token:
    def __init__(self, balances, rewards, emissions, total_supply):
        self.balances = balances
        self.rewards = rewards
        self.emissions = emissions
        self.total_supply = total_supply


def create_start(epoch_count, user_count, min_shares, shares_range, decimals, determinsitic):

    ## Start is always a token that is not a reward nor an emission

    balances = []
    rewards = []
    emissions = []

    ## Cumulative amount that increases by reward on each epoch
    ## 0 -> reward_0
    ## n > reward_n-1 + reward_n
    total_supply = []


    for epoch in range(epoch_count):
        balances.append([])
        rewards.append([])
        emissions.append([])
        total_supply.append([])

    for user in range(user_count):
        ## User Balance
        balance = (
            (int(random() * shares_range) + min_shares) * 10**decimals
            if not determinsitic
            else min_shares * 10**decimals
        )
        balances[0].append(balance)

        total_supply[0] += balance
    
    return Token(balances, rewards, emissions, total_supply)


def create_reward_token(epoch_count, min_reward, reward_range, decimals, determinsitic, with_emission = True):
    ## Reward means no emissions
    ## Add the flip somewhere else
    
    balances = []
    rewards = []
    emissions = []
    total_supply = []

    for epoch in range(epoch_count):
        balances.append([]) ## 0

        rewards.append([])
        emissions.append([]) ## 0
        total_supply.append([])

    for epoch in range(epoch_count):
        ## Create reward always
        reward = (
            (int(random() * reward_range) + min_reward) * 10**decimals
            if not determinsitic
            else min_reward * 10**decimals
        )
        rewards[epoch].append(reward)

        if(epoch > 0):
            total_supply[epoch] = total_supply[epoch - 1]
        
        total_supply[epoch] += reward

        if(with_emission):
            ## Emission and reward math is same, TODO: deal with it

            emission = (
                (int(random() * reward_range) + min_reward) * 10**decimals
                if not determinsitic
                else min_reward * 10**decimals
            )
            emissions[epoch].append(emission)
            
            total_supply[epoch] += emission

    
    return Token(balances, rewards, emissions, total_supply)

## Claim Sequence Notation | ClaimSequence

"""
    tokens{
        [id]: TokenData
    }

    ## Linked list like data structure
    claimSequence[start, 
                            next, 
                            next,   next (TODO)
                            next,   next, 
                                    next
    ]

    claimSequence(start, claimData[])

    claimData {
        Tokens: [address, bool], ## Rewards to claim, and should we claim emissions as well?
        Next: claimData[]
    }
    
    Classic Linked List
    TODO: Check Austin's work
    https://medium.com/coinmonks/linked-lists-in-solidity-cfd967af389b


    received{
        [id]: 
            [user]:
                {
                    rewards[epoch]
                    emissions[epoch]
                }   
    }
"""

def create_claim_sequence():
    ## TODO: Generalize

    ## For now just return A -> B -> B' -> C -> C'
    return 

## Validate claimSequence

"""
    Loop over the sequence

    Next.rewards[0][token] MUST be non-zero.

    In Solidity we won't be perfoming the check

    A subsequence zero epoch is acceptable, but first one needs to be non-zero
"""

def is_valid_next_step(vault, reward, previous_paths):
    ## previous_paths[vault]: tokens[]
    ## List of tokens contains
    if reward in previous_paths[vault]:
        ## Revert if already there
        assert False


## Claim Math

"""
    ## From Claim proof
        For Each V ∈ Vs:
        Claim(V, n, i) ===
        {
            vi / Tvi * Ri; if V != R; Rewards Case
            vi / (Tvi - Ri); if V == R; Emissions Case
        }
"""

def get_reward(balance, total_supply, rewards, epoch, token):
    """
        Use it to receive A -> B type rewards
        Where A != B

        Returns (claimed, dust)
    """
    divisor = total_supply[epoch]

    claimed = balance * rewards[epoch][token] // divisor
    dust = balance * rewards[epoch][token] % divisor

    return (claimed, dust)

def get_emission(balance, total_supply, emissions, epoch):
    """
        Given an (updated e.g already claimed reward) balance, claim the emissions for this epoch

        Use it to receive B -> B' type rewards
        Where B == B' they are the same token

        Returns (claimed, dust)
    """
    ## Any older emission is assumed to be claimed
    ## Because we assume nothing from the future is in, we can just subtract the one from the current claim
    divisor = total_supply[epoch] - emissions[epoch]

    claimed = balance * emissions[epoch] // divisor
    dust = balance * emissions[epoch] % divisor

    return (claimed, dust)

## Fairness Check at end

"""
    User Deposited / TotalSupply = Expected %


    Recursive validation via:
    -> Expected %
    -> Vs realized %

    NOTE: Can do this because we prove that claiming every week vs once per year is equivalent
    ## As our divisor is not relative to the value
"""

def fairness_check(user_count, epoch_count, balances, total_supply, received_rewards, total_rewards, received_emissions, total_emissions):

    for user in range(user_count):
        for epoch in range(epoch_count):
            check_fair_received(balances[epoch][user], total_supply, received_rewards[epoch], total_rewards[epoch], received_emissions[epoch], total_emissions[epoch])

    ## TODO: Sum it all up

    ## Is the sum of all tokens fair as well?


def check_fair_received(balance, total_supply, received_reward, total_rewards, received_emission, total_emissions):

    expected_percent = balance / total_supply

    ## TODO: Change to allow dust
    assert total_rewards / received_reward == expected_percent
    assert received_emission / total_emissions == expected_percent

    ## Maybe just check on sum, although I think it will always need to be the correct ratio
