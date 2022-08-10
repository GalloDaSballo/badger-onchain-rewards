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
  - VAULT_B_EMISSIONS_TO_A
  - VAULT_B_SELF_EMISSIONS
  - VAULT_B_EMISSIONS_TO_OTHER ## Emissions of B for another random vault (Vault D)
  - VAULT_B_HODLERS ## Users with direct deposits to B

  TODO: Fix calculation to:
    - Give back "less rewards" directly to direct claimers <- Back to 04 math which is the correct one

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

EPOCHS_RANGE = 0
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
MIN_VAULT_B_EMISSIONS_TO_A = 1_000 ## The "true" "base" yield from B -> A (without adding self-emissions)
VAULT_B_EMISSIONS_TO_A = 100_000 ## 100 k ETH example

VAULT_B_SELF_EMISSIONS = 100_000_000 ## 100M ETH example - Exacerbates issue with B -> B Claim
VAULT_B_EMISSIONS_TO_OTHER = 1_000_000 ## Inflates total supply but is not added to rewards
VAULT_B_HODLERS = 1_000_000 ## Inflates total supply and dilutes all emissions (even from C)


### C VARS ###
MIN_VAULT_C_EMISSIONS_TO_B = 1_000 ## 10 k ETH example
VAULT_C_EMISSIONS_TO_B = 100_000 ## 100 k ETH example

VAULT_C_SELF_EMISSIONS = 100_000 ## 100k ETH example
VAULT_C_EMISSIONS_TO_OTHER = 1_000_000 ## Inflates total supply but is not added to rewards
VAULT_C_HODLERS = 1_000_000 ## Inflates total supply and dilutes all emissions from C


USERS_RANGE = 10
USERS_MIN = 3


## How many simulations to run?
ROUNDS = 1

## Should the print_if_if print_if stuff?
SHOULD_PRINT = ROUNDS == 1

def print_if(v):
  if SHOULD_PRINT:
    print(v)

def multi_claim_sim():

  ## Setup user and epochs
  number_of_epochs = int(random() * EPOCHS_RANGE) + EPOCHS_MIN
  number_of_users = int(random() * USERS_RANGE) + USERS_MIN

  ## For fairness check at end
  total_user_deposits = 0
  total_user_points = 0
  ## How much of b and c was distributed || 100% - dust is the expected result
  total_claimed_b = 0
  total_claimed_c = 0

  total_dust_b = 0
  total_dust_c = 0

  ## Stats / Temp Vars for simulation
  claiming = [] ## Is the user going to claim each week
  claimers = 0
  initial_balances = []
  balances = []
  points = []
  total_supply = 0
  total_points = 0
  claimed_b = [] ## How much did each user get
  claimed_c = [] ## How much did each user get

  points_b = [] ## points[user][epoch]

  ## Setup for users
  for user in range(number_of_users):
    is_claiming = random() >= 0.5
    claimers += 1 if is_claiming else 0
    claiming.append(is_claiming)
    balance = (int(random() * RANGE) + MIN_SHARES) * 10 ** SHARES_DECIMALS
    balances.append(balance)

    temp_list = []

    ## Add empty list for points_b
    for epoch in range(number_of_epochs):
      temp_list.append(0)
    
    points_b.append(temp_list)

    initial_balances.append(balance)
    total_user_deposits += balance
    claimed_b.append(0)
    claimed_c.append(0)

    user_points = balance * SECONDS_PER_EPOCH
    total_user_points += user_points
    points.append(user_points)

    total_supply += balance

    total_points += user_points

  ## Reward B
  total_rewards_b_float = 0 ## Rewards we can receive
  rewards_b_direct = []
  total_direct_rewards_b = 0
  contract_points_b_per_epoch = []
  total_supply_b = 0 ## Actual total amount of b
  total_points_b = 0 ## total_supply_b * SECONDS_PER_EPOCH
  ## NOTE: Could prob just use same value per epoch but will randomize for better nuance
  rewards_b_self_emissions_to_b = []
  total_b_emitted_b_rewards = 0
  b_emissions_to_other = []

  for epoch in range(number_of_epochs):
    reward_b = (int(random() * VAULT_B_EMISSIONS_TO_A) + MIN_VAULT_B_EMISSIONS_TO_A) * 10 ** SHARES_DECIMALS
    rewards_b_direct.append(reward_b)
    total_rewards_b_float += reward_b
    total_direct_rewards_b += reward_b
    total_supply_b += reward_b

    ## Points of b inside of Contract
    contract_points_b = reward_b * SECONDS_PER_EPOCH

    contract_points_b_per_epoch.append(contract_points_b)

    ### Extra "noise stuff" to make simulation more accurate ###
     
    ## Self-Emission B -> B - Only A% of these are claimable as reward, rest belongs to other depositors
    b_self_emissions_epoch = (int(random() * VAULT_B_SELF_EMISSIONS) + MIN_VAULT_B_EMISSIONS_TO_A) * 10 ** SHARES_DECIMALS

    ## Emissions to another vault, inflate total_supply, do not increase rewards
    b_extra_emissions_epoch = (int(random() * VAULT_B_EMISSIONS_TO_OTHER) + MIN_VAULT_B_EMISSIONS_TO_A) * 10 ** SHARES_DECIMALS
    
    ## Store them for math later
    rewards_b_self_emissions_to_b.append(b_self_emissions_epoch)
    total_b_emitted_b_rewards += b_self_emissions_epoch

    b_emissions_to_other.append(b_extra_emissions_epoch)

    ## Increase total Supply
    total_supply_b += b_extra_emissions_epoch
  
  total_contract_points_b = total_direct_rewards_b * SECONDS_PER_EPOCH

  ## Add random extra hodlers that hold B
  b_hodlers = (int(random() * VAULT_B_HODLERS) + MIN_VAULT_B_EMISSIONS_TO_A) * 10 ** SHARES_DECIMALS

  total_supply_b += b_hodlers

  ## As ratio
  ## Use Total Supply to calculate ratio here
  before_emisisons_rewards_b = total_rewards_b_float
  before_emisisons_total_supply_b = total_supply_b
  b_claimable_emissions = 0

  estimate_claimable_per_epoch = []

  ## Add Self-Emission % as Reward for Fairness Estimate
  for b_self_emission in rewards_b_self_emissions_to_b:
    ## % of B such that A -> B / totalSupply(B) * Emission
    emission_float = b_self_emission * before_emisisons_rewards_b / before_emisisons_total_supply_b
    estimate_claimable_per_epoch.append(emission_float)
    total_rewards_b_float += emission_float
    b_claimable_emissions += int(emission_float)
    ## Also update total supply after accounting the emissions
    total_supply_b += b_self_emission

  total_points_b = total_supply_b * SECONDS_PER_EPOCH

  ## TODO: What are exactly the B that you can receive?
  ## They should be Sum(b_direct + %b_to_b)
  ## Distribute Direct -> rewards[epoch][tokenA][tokenB]
  ## Distribute Side -> rewards[epoch][tokenB][tokenB]
  
  
  ## Find B Adjustor | TODO: Figure out what the adjustor looks like
  total_b_emitted_b_points = total_b_emitted_b_rewards * SECONDS_PER_EPOCH

  self_emitting_rewards_points_b_cumulative = []

  ## Correction value as those tokens are in the contract but they will not be claimable by anyone
  ## In other words, we're removing points from rewards from future epochs
  ## Otherwise these tokens are receiving rewards that you'd be expecting to claim
  ## In other words, these are the non-circulating rewards
  ## Which we must remove as only the circulating rewards can receive emissions
  ## TODO: Move this spiel to contract_points_b_per_epoch
  directly_claimable_reward_contract_points_corrections = []

  for epoch in range(number_of_epochs):
    self_emitting_rewards_points_b_cumulative.append(total_b_emitted_b_points)

    ## Last value of contract_points_b is 
    directly_claimable_reward_contract_points_corrections.append(total_contract_points_b)
  
  acc = 0
  acc_direct = 0
  for epoch in range(number_of_epochs):
    if(epoch > 0):
      ## Remove acc
      self_emitting_rewards_points_b_cumulative[epoch] -= acc
    
    ## Skip first one
    acc += rewards_b_self_emissions_to_b[epoch] * SECONDS_PER_EPOCH
    acc_direct += contract_points_b_per_epoch[epoch]
    directly_claimable_reward_contract_points_corrections[epoch] -= acc_direct

  assert self_emitting_rewards_points_b_cumulative[0] == total_b_emitted_b_points
  ## Verify that we're reducing rewards from first epoch
  assert directly_claimable_reward_contract_points_corrections[0] == total_contract_points_b - contract_points_b_per_epoch[0]
  ## End is 0 as all tokens are circulating
  assert directly_claimable_reward_contract_points_corrections[-1] == 0 
  ## Penultimate should be equal to last set of points in contract
  # assert directly_claimable_reward_contract_points_corrections[-2] == contract_points_b_per_epoch[-1]

  total_claimed_direct = 0
  ## Claim B
  for epoch in range(number_of_epochs):
    divisor = (total_points) ## No subtraction as rewards are from A which is not self-emitting

    for user in range(number_of_users):
      ## NOTE: Hunch - no distinction between early and late claimers, as divisor is based on reward points
      user_total_rewards_fair = rewards_b_direct[epoch] * points[user] // divisor
      user_total_rewards_dust = rewards_b_direct[epoch] * points[user] % divisor

      claimed_points = user_total_rewards_fair * SECONDS_PER_EPOCH
      ## Add new rewards to user points for next epoch
      ## Port over old points (cumulative) + add the claimed this epoch
      old_points = points_b[user][epoch - 1] if epoch > 0 else 0
      points_b[user][epoch] = old_points + claimed_points

      total_claimed_b += user_total_rewards_fair
      total_dust_b += user_total_rewards_dust

      total_claimed_direct += user_total_rewards_fair

  ## Ensure basic math is correct, all rewards are claimed
  print(total_claimed_direct / total_direct_rewards_b * 100)
  assert total_claimed_direct / total_direct_rewards_b * 100 == 100
  assert total_direct_rewards_b >= total_claimed_direct ## Check of fairness

  ## Claim B from B
  ## TODO: WIP
  ## HUNCH: divisor = (total_points - contract_points_per_epoch * (number_of_epochs - epoch))
  ## B to B must be done via that so that we claim only the % we are entitled to

  ## Accumulator of all b_rewards claimed so we can port over to next epoch to simulate compound rewards
  prev_user_claim_acc = []
  for user in range(number_of_users):
    prev_user_claim_acc.append(0)

  total_claimed_self_emissions_b = 0

  print("directly_claimable_reward_contract_points_corrections")
  print(directly_claimable_reward_contract_points_corrections)

  ## Percentage of B claimed as percentage of total B claimeable for % of rewards[b][b]
  for epoch in range(number_of_epochs):
    ## No subtraction as rewards are from A which is not self-emitting
    ## DONE: Remove the points the contract has as effect of self-emission, just like in SIM_04
    ## TODO: CHECK: Remove the points from future, non-self-emissions to account for circulating tokens that can claim
    divisor = total_points_b - self_emitting_rewards_points_b_cumulative[epoch] ##- directly_claimable_reward_contract_points_corrections[epoch]

    assert divisor <= total_points_b

    print("total_points_b")
    print(total_points_b)
    print("divisor")
    print(divisor)

    claimed_this_epoch = 0

    ## Each user will acc from 0 to N and use this as supporting variable to retain the claims from prev epochs
    ## Quick fix to avoid re-setting old rewards
    for user in range(number_of_users):
      user_total_rewards_fair = rewards_b_self_emissions_to_b[epoch] * points_b[user][epoch] // divisor
      user_total_rewards_dust = rewards_b_self_emissions_to_b[epoch] * points_b[user][epoch] % divisor

      claimed_points = user_total_rewards_fair * SECONDS_PER_EPOCH
      ## Add new rewards to user points for next epoch
      ## Port over old points (cumulative) + add the claimed this epoch
      points_b[user][epoch] += claimed_points

      ## TODO: Fix compounding accrual
      prev_user_claim_acc[user] += claimed_points

      assert prev_user_claim_acc[user] > 0

      if epoch + 1 < number_of_epochs:
        # Port over cumulative claims
        points_b[user][epoch + 1] += prev_user_claim_acc[user]

      total_claimed_b += user_total_rewards_fair
      claimed_this_epoch += user_total_rewards_fair
      total_claimed_self_emissions_b += user_total_rewards_fair
      total_dust_b += user_total_rewards_dust
    
    print("claimed_this_epoch")
    print(claimed_this_epoch / estimate_claimable_per_epoch[epoch] * 100)


  ## VERIFY B CLAIMS ARE FAIR AND MAKE SENSE
  ## TODO






  ###############################

  ## Claim C from B
  ## TODO

  ## Claim C from C
  ## TODO


  print("Claimed B")
  print(total_claimed_b / total_rewards_b_float * 100)

  print_if("Dust B")
  print_if(total_rewards_b_float - total_claimed_b)

  print("Percent Emission of Emitting Claimed")
  print((b_claimable_emissions - total_claimed_self_emissions_b) / b_claimable_emissions * 100)


  assert b_claimable_emissions >= total_claimed_self_emissions_b
  assert total_rewards_b_float >= total_claimed_b

  # print_if("Claimed C")
  # print_if(total_claimed_c / total_rewards_c * 100)

  return (total_rewards_b_float - total_claimed_b) / total_claimed_b

  # return (total_rewards_c - total_claimed_c) / total_rewards_c


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