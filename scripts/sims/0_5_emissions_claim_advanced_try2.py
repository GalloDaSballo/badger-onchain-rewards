from random import seed
from random import random

"""
  Given TokenA -> RewardB -> RewardC

  General Case 2) Random Many to Many some are self-emitting (question is, do we need extra math or not?)

  e.g. (Full)
  From A -> B -> C
         -> B from B -> C from B from B
                   C -> C from C
                   C -> C from C from B from B

  Token A can be Self-emitting or not (shouldn't matter) - TotalPoints
  (TODO: Math to prove self-emitting is reduceable to this case)

  
  NOTE: Working on B first to reach POC

  Token B self emits, is also emitted by Vault D and some people hold token B
  - VAULT_B_REWARDS_TO_A
  - VAULT_B_SELF_EMISSIONS
  - VAULT_B_EMISSIONS_TO_OTHER ## Emissions of B for another random vault (Vault D)
  - VAULT_B_HODLERS ## Users with direct deposits to B

  TODO: Fix calculation to:
    - Give back "less rewards" directly to direct claimers <- Back to 04 math which is the correct one
    
    Future Rewards Backwards Claims
    - NEW: 
      Reward Positions will claim their rewards when claimed and distribute to users
        Effectively a Reward is a "Virtual Account" meaning just like any user it's accruing rewards
        Because of this, when claiming, we need to claim the rewards that this "Virtual Position" has accrued
        Doing this allows us to never correct the divisor to unfair / overly fair levels, at the cost of computational complexity
        NOTE: At this time  I believe this to be the mathematically correct solution, I


  TODO: ADD C

  Token C self emits, is also emitted by Vault E and some people hold token C
  - VAULT_C_EMISSIONS_TO_B
  - VAULT_C_SELF_EMISSIONS
  - VAULT_C_EMISSIONS_TO_OTHER ## Emissions of C for another random vault (Vault E)
  - VAULT_C_HODLERS ## Users with direct deposits to C
"""
## NOTE: a 1 epoch test MUST always pass 
## because the issue of Future Rewards Backwards Claims is not relevant (there is no epoch of unclaimable rewards)
EPOCHS_RANGE = 0 ## Set to 0 to test specific epoch amounts
EPOCHS_MIN = 1

SHARES_DECIMALS = 18
RANGE = 10_000 ## Shares can be from 1 to 10k with SHARES_DECIMALS
MIN_SHARES = 1_000 ## Min shares per user
SECONDS_PER_EPOCH = 604800

## Amount of extra B that doesn't belong to the emissions from Vault A ()
## TODO: Think about this.
## Basically other deposits
NOISE_B_PER_EPOCH = 123123 


### B VARS ###
MIN_VAULT_B_REWARDS_TO_A = 1_000 ## The "true" "base" yield from B -> A (without adding self-emissions)
VAULT_B_REWARDS_TO_A = 100_000 ## 100 k ETH example

VAULT_B_SELF_EMISSIONS = 100_000_000 ## 100M ETH example - Exacerbates issue with B -> B Claim
VAULT_B_EMISSIONS_TO_OTHER = 1_000_000 ## Inflates total supply but is not added to rewards
VAULT_B_HODLERS = 1_000_000 ## Inflates total supply and dilutes all emissions (even from C)


### C VARS ###
MIN_VAULT_C_EMISSIONS_TO_B = 1_000 ## 10 k ETH example
VAULT_C_EMISSIONS_TO_B = 100_000 ## 100 k ETH example

VAULT_C_SELF_EMISSIONS = 100_000 ## 100k ETH example
VAULT_C_EMISSIONS_TO_OTHER = 1_000_000 ## Inflates total supply but is not added to rewards
VAULT_C_HODLERS = 1_000_000 ## Inflates total supply and dilutes all emissions from C


USERS_RANGE = 0
USERS_MIN = 2000


## How many simulations to run?
ROUNDS = 1

## Should the print_if_if print_if stuff?
SHOULD_PRINT = ROUNDS == 1

def print_if(v):
  if SHOULD_PRINT:
    print(v)

def multi_claim_sim():

  ##### SETUP #####

  ## Setup user and epochs
  number_of_epochs = int(random() * EPOCHS_RANGE) + EPOCHS_MIN
  number_of_users = int(random() * USERS_RANGE) + USERS_MIN

  ## For fairness check at end
  total_user_deposits = 0
  total_user_points = 0

  ## How much of b was distributed
  total_claimed_b = 0

  total_dust_b = 0

  ## Stats / Temp Vars for simulation
  claiming = [] ## Is the user going to claim each week ## TODO: Use or prove not necessary
  claimers = 0

  initial_balances = []
  balances = []
  points_a = []
  total_supply_a = 0
  total_points_a = 0

  claimed_b = [] ## How much did each user get
  points_b = [] ## points_a[user][epoch]

  ##### SETUP USER #####

  ## Setup for users
  for user in range(number_of_users):
    ## Is User Claiming
    is_claiming = random() >= 0.5
    claimers += 1 if is_claiming else 0
    claiming.append(is_claiming)

    ## User Balance
    balance = (int(random() * RANGE) + MIN_SHARES) * 10 ** SHARES_DECIMALS
    balances.append(balance)

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

  total_rewards_b = 0 ## Rewards B
  rewards_b = [] ## Rewards per epoch B

  emissions_b_b = [] ## Emissions B' B -> B'
  total_emissions_b_b = 0 ## Total Emissions B' 

  total_supply_b = 0 ## Actual total amount of b

  for epoch in range(number_of_epochs):
    reward_b = (int(random() * VAULT_B_REWARDS_TO_A) + MIN_VAULT_B_REWARDS_TO_A) * 10 ** SHARES_DECIMALS
    rewards_b.append(reward_b)

    total_rewards_b += reward_b
    total_supply_b += reward_b

    ### Extra "noise stuff" to make simulation more accurate ###
     
    ## Self-Emission B -> B - Only A% of these are claimable as reward, rest belongs to other depositors
    b_self_emissions_epoch = (int(random() * VAULT_B_SELF_EMISSIONS) + MIN_VAULT_B_REWARDS_TO_A) * 10 ** SHARES_DECIMALS

    emissions_b_b.append(b_self_emissions_epoch)
    total_emissions_b_b += b_self_emissions_epoch

    ## Increase total Supply
    total_supply_b += b_self_emissions_epoch

    ## Emissions to another vault, inflate total_supply, do not increase rewards
    ## TODO: Emissiosn to Another Vault D -> B

    ## TODO: B Total Supply Inflated
    
    ## Store them for math late

    

  
  acc_verify_total_rewards = 0
  acc_verify_total_emissions = 0
  for epoch in range(number_of_epochs):
    ## TEMP: Test sum to ensure totalSupply is correct
   acc_verify_total_rewards += rewards_b[epoch]
   acc_verify_total_emissions += emissions_b_b[epoch]
  
  ## NOTE: This will break once we add more | TODO: Update to handle extra emissions and other holders
  assert total_supply_b == acc_verify_total_rewards + acc_verify_total_emissions
  assert total_supply_b == total_emissions_b_b + total_rewards_b
  assert acc_verify_total_rewards == total_rewards_b
  assert acc_verify_total_emissions == total_emissions_b_b

  print("Ratio for Rewards vs Total Supply")
  print(acc_verify_total_rewards / total_supply_b * 100)
  print("Ratio for Emissions vs Total Supply")
  print(acc_verify_total_emissions / total_supply_b * 100)


  ##### CLAIM B ######
  total_claimed_direct = 0

  for epoch in range(number_of_epochs):
    divisor = total_points_a ## No subtraction as rewards are from A which is not self-emitting

    for user in range(number_of_users):      

      user_total_rewards_fair = points_a[user] * rewards_b[epoch] // divisor
      user_total_rewards_dust = points_a[user] * rewards_b[epoch] % divisor

      claimed_points = user_total_rewards_fair * SECONDS_PER_EPOCH
      
      ## Add new rewards to user points_a for next epoch
      ## Port over old points_a (cumulative) + add the claimed this epoch
      old_points = points_b[user][epoch - 1] if epoch > 0 else 0
      points_b[user][epoch] = old_points + claimed_points

      total_claimed_b += user_total_rewards_fair
      total_dust_b += user_total_rewards_dust

      total_claimed_direct += user_total_rewards_fair

    ## Ensure basic math is correct, all rewards are claimed
  assert total_claimed_b / total_rewards_b * 100 == 100
  assert total_rewards_b >= total_claimed_direct ## Check of fairness


  ###### Claim B from B #######

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
    if(epoch > 0):
      ## Remove acc
      emissions_b_b_points_cumulative_per_epoch[epoch] -= acc
    
    ## Skip first one
    acc += emissions_b_b[epoch] * SECONDS_PER_EPOCH

  ## Emission Total Points on First Epoch === Total Contract Points
  assert emissions_b_b_points_cumulative_per_epoch[0] == total_emissions_b_b_points

  if number_of_epochs > 1:
     assert emissions_b_b_points_cumulative_per_epoch[1] == total_emissions_b_b_points - emissions_b_b[0] * SECONDS_PER_EPOCH

  ## Last Epoch Only points left are from last epoch
  assert emissions_b_b_points_cumulative_per_epoch[-1] == emissions_b_b[-1] * SECONDS_PER_EPOCH

  ## Actually Claim B -> B'

  ## Accumulator of total emissions claimed to check accuracy of model
  total_claimed_self_emissions_b = 0

  ## Accumulator of all b_rewards claimed so we can port over to next epoch to simulate compound rewards
  prev_user_claim_acc = []
  for user in range(number_of_users):
    prev_user_claim_acc.append(0)

  for epoch in range(number_of_epochs):
    divisor = total_points_b - emissions_b_b_points_cumulative_per_epoch[epoch]

    for user in range(number_of_users):

      user_total_rewards_fair = emissions_b_b[epoch] * points_b[user][epoch] // divisor
      user_total_rewards_dust = emissions_b_b[epoch] * points_b[user][epoch] % divisor

      claimed_points = user_total_rewards_fair * SECONDS_PER_EPOCH
      ## Add new rewards to user points for next epoch
      ## Port over old points (cumulative) + add the claimed this epoch
      points_b[user][epoch] += claimed_points

      ## Compounding accrual
      prev_user_claim_acc[user] += claimed_points

      assert prev_user_claim_acc[user] > 0

      if epoch + 1 < number_of_epochs:
        # Port over cumulative claims
        points_b[user][epoch + 1] += prev_user_claim_acc[user]


      total_claimed_b += user_total_rewards_fair
      total_claimed_self_emissions_b += user_total_rewards_fair
      total_dust_b += user_total_rewards_dust

  ## NOTE: Direct B -> B' Claim will fail for now, as you're not getting the many emissions that are being earned by future rewards 

  print("Percent of emissions claimed via Direct Claims")
  print(total_claimed_b / total_emissions_b_b * 100)


  # ###### TEMP TEST ######
  ## NOTE: This is plain wrong, but can be helpful
  # ## Intermediary step, get the points that were not claimed and prove that those points will get all remaining emissions
  # unclaimed_b = total_supply_b - total_claimed_b ## NOTE: This will break if we add "noise"
  # points_unclaimed = unclaimed_b * SECONDS_PER_EPOCH

  # rewards_unclaimed = 0
  # for epoch_index in range(number_of_epochs):
  #   virtual_divisor = total_points_b - emissions_b_b_points_cumulative_per_epoch[epoch] ## Same as for B -> B'

  #   rewards_earned = emissions_b_b[epoch_index] * points_unclaimed / virtual_divisor

  #   rewards_unclaimed += rewards_earned
  
  # print("(total_claimed_b + rewards_unclaimed) / total_supply_b")
  # print((total_claimed_b + rewards_unclaimed) / total_supply_b)
  # assert total_claimed_b + rewards_unclaimed == total_supply_b



  ###### VIRTUAL ACCOUNTS ######
  ## Treat Future Rewards as if they are accounts, claiming each epoch and using those claims for each subsequent claim

  virtual_account_rewards = 0
  acc_total_rewards_used_check = 0
  for epoch_index in range(number_of_epochs):
    total_unclaimed = rewards_b[epoch_index] ## Unclaimed are future rewards receiving emissions from previous epochs
    total_unclaimed_points = total_unclaimed * SECONDS_PER_EPOCH

    acc_total_rewards_used_check += total_unclaimed

    if epoch_index > 0:
      for y in range(epoch_index):

        ## Calculate rewards earned for epochs before `epoch_index`
        virtual_divisor = total_points_b - emissions_b_b_points_cumulative_per_epoch[epoch] ## Same as for B -> B'

        print("total_unclaimed_points / divisor")
        print((total_unclaimed_points + virtual_account_rewards * SECONDS_PER_EPOCH) / virtual_divisor * 100)

        rewards_earned = emissions_b_b[y] * (total_unclaimed_points + virtual_account_rewards * SECONDS_PER_EPOCH) / virtual_divisor

        virtual_account_rewards += rewards_earned

  assert acc_total_rewards_used_check == total_rewards_b

  print("total_claimed_self_emissions_b + virtual_account_rewards / total_emissions_b_b * 100")    
  print((total_claimed_self_emissions_b + virtual_account_rewards) / total_emissions_b_b * 100)    
  assert (total_claimed_self_emissions_b + virtual_account_rewards) / total_emissions_b_b * 100 == 100

  ## Amount (total - claimed) / total = approx of rounding errors
  return (total_emissions_b_b - (total_claimed_self_emissions_b + virtual_account_rewards)) / total_emissions_b_b







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