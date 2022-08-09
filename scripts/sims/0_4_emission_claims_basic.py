from random import seed
from random import random

"""
  Given TokenA -> RewardB -> RewardC

  Claim
  DEMO CASE

  General Case 1) -> Random Many to Many

  From A -> B -> C

  General Case 2) Random Many to Many some are self-emitting (question is, do we need extra math or not?)
  e.g. (Basic)
  From A -> B -> C
         -> B from B -> C from B from B

  e.g. (Full)
  From A -> B -> C
        -> B from B -> C from B from B
                  C -> C from C
                  C -> C from C from B from B
"""

EPOCHS_RANGE = 10
EPOCHS_MIN = 2
SHARES_DECIMALS = 18
RANGE = 10_000 ## Shares can be from 1 to 10k with SHARES_DECIMALS
MIN_SHARES = 1_000 ## Min shares per user
SECONDS_PER_EPOCH = 604800

MIN_REWARDS_B_PER_EPOCH = 1_000 ## 10 k ETH example
REWARD_B_PER_EPOCH = 100_000 ## 100 k ETH example

MIN_REWARDS_C_PER_EPOCH = 1_000 ## 10 k ETH example
REWARD_C_PER_EPOCH = 100_000 ## 100 k ETH example

USERS_RANGE = 10
USERS_MIN = 3


## How many simulations to run?
ROUNDS = 10_000

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

  print_if("number_of_users")
  print_if(number_of_users)
  print_if("number_of_epochs")
  print_if(number_of_epochs)
  print_if("points_b")
  print_if(points_b)
  print_if("points_b len")
  print_if(len(points_b))

  ## Reward B
  total_rewards_b = 0
  rewards_b = []
  contract_points_b_per_epoch = []

  for epoch in range(number_of_epochs):
    reward_b = (int(random() * REWARD_B_PER_EPOCH) + MIN_REWARDS_B_PER_EPOCH) * 10 ** SHARES_DECIMALS
    rewards_b.append(reward_b)
    total_rewards_b += reward_b

    ## Points of b inside of Contract
    contract_points_b = reward_b * SECONDS_PER_EPOCH

    contract_points_b_per_epoch.append(contract_points_b)
  

  ## Reward C
  total_rewards_c = 0
  rewards_c = []
  contract_points_c_per_epoch = []
  
  for epoch in range(number_of_epochs):
    reward_c = (int(random() * REWARD_C_PER_EPOCH) + MIN_REWARDS_C_PER_EPOCH) * 10 ** SHARES_DECIMALS
    rewards_c.append(reward_c)
    total_rewards_c += reward_c

    ## Don't think we need to calculate points for C as we just claim it
    contract_points_c = reward_c * SECONDS_PER_EPOCH

    contract_points_c_per_epoch.append(contract_points_c)
  
  ## Find B Adjustor
  total_b_points = total_rewards_b * SECONDS_PER_EPOCH
  b_points_per_epoch_cumulative = []
  
  acc = 0
  for epoch in range(number_of_epochs):
    acc += rewards_b[epoch] * SECONDS_PER_EPOCH
    b_points_per_epoch_cumulative.append(acc)
    

  
  assert b_points_per_epoch_cumulative[-1] == total_b_points

  ## Claim B
  for epoch in range(number_of_epochs):
    divisor = (total_points) ## No subtraction as not self-emitting

    for user in range(number_of_users):
      ## NOTE: Hunch - no distinction between early and late claimers, as divisor is based on reward points


      user_total_rewards_fair = rewards_b[epoch] * points[user] // divisor
      user_total_rewards_dust = rewards_b[epoch] * points[user] % divisor

      claimed_points = user_total_rewards_fair * SECONDS_PER_EPOCH
      ## Add new rewards to user points for next epoch
      ## Port over old points (cumulative) + add the claimed this epoch
      old_points = points_b[user][epoch - 1] if epoch > 0 else 0
      points_b[user][epoch] = old_points + claimed_points

      total_claimed_b += user_total_rewards_fair
      total_dust_b += user_total_rewards_dust

  ## Claim B from B
  ## NOT HERE

  ## Claim C from B

  ## TODO: Track balance of B in user to know how much to claim

  for epoch in range(number_of_epochs):
    ## Assume totalSupply never changes
    divisor = b_points_per_epoch_cumulative[epoch]
    
    ## My hunch is divisor should be same to self-emitting vaults

    ## Options for Divisor:
    ## TotalSupply -> Unfair as early dist means tons of rewards are not distributed
    ## 
    ##


    for user in range(number_of_users):
      ## NOTE: Hunch - no distinction between early and late claimers, as divisor is based on reward points
      
      user_total_rewards_fair = rewards_c[epoch] * points_b[user][epoch] // divisor
      user_total_rewards_dust = rewards_c[epoch] * points_b[user][epoch] % divisor

      claimed_points = user_total_rewards_fair * SECONDS_PER_EPOCH
      ## Add new rewards to user points for next epoch


      claimed_c[user] += user_total_rewards_fair

      total_claimed_c += user_total_rewards_fair
      total_dust_c += user_total_rewards_dust

  ## Claim C from C
  ## NOT HERE

  print_if("Claimed B")
  print_if(total_claimed_b / total_rewards_b * 100)

  print_if("Claimed C")
  print_if(total_claimed_c / total_rewards_c * 100)

  ## Obviously we claimed all B
  assert total_claimed_b / total_rewards_b * 100 == 100 

  return (total_rewards_c - total_claimed_c) / total_rewards_c


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