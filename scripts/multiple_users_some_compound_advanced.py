from random import seed
from random import random

EPOCHS_RANGE = 10
EPOCHS_MIN = 2
SHARES_DECIMALS = 18
RANGE = 10_000 ## Shares can be from 1 to 10k with SHARES_DECIMALS
MIN_SHARES = 1_000 ## Min shares per user
SECONDS_PER_EPOCH = 604800

MIN_REWARDS_PER_EPOCH = 1_000 ## 10 k ETH example
REWARD_PER_EPOCH = 100_000 ## 100 k ETH example
USERS_RANGE = 10
USERS_MIN = 3


## How many simulations to run?
ROUNDS = 10_000

## Should the print_if print stuff?
SHOULD_PRINT = ROUNDS == 1




## Write function to calculate total Points for vault
## Write function to calculate points for this epoch

## Subtract

## Write stuff to recompute the total points (see commented below)

"""
  - WIP: Advanced V1 -> Random Rewards -> Decided upfront
  - TODO: Advanced V2 -> Total Supply also changes (Rewards are minted mid-epoch)
"""

def print_if(v):
  if SHOULD_PRINT:
    print(v)
  

def simple_users_sim():

  number_of_epochs = int(random() * EPOCHS_RANGE) + EPOCHS_MIN
  number_of_users = int(random() * USERS_RANGE) + USERS_MIN

  total_user_deposits = 0
  total_user_points = 0

  claiming = [] ## Is the user strat to claim each week
  claimers = 0
  initial_balances = []
  balances = []
  points = []
  total_supply = 0
  total_points = 0
  claimed = [] ## How much did each user get

  for user in range(number_of_users):
    is_claiming = random() >= 0.5
    claimers += 1 if is_claiming else 0
    claiming.append(is_claiming)
    balance = (int(random() * REWARD_PER_EPOCH) + MIN_REWARDS_PER_EPOCH) * 10 ** SHARES_DECIMALS
    balances.append(balance)


    initial_balances.append(balance)
    total_user_deposits += balance
    claimed.append(0)

    user_points = balance * SECONDS_PER_EPOCH
    total_user_points += user_points
    points.append(user_points)

    total_supply += balance

  ## Vault Stuff
  total_rewards = 0
  rewards = []
  contract_points_per_epoch = []
  contract_points_per_epoch_cumulative = []
  temp_total_points_acc = 0

  for epoch in range(number_of_epochs):
    reward = (int(random() * REWARD_PER_EPOCH) + MIN_REWARDS_PER_EPOCH) * 10 ** SHARES_DECIMALS
    rewards.append(reward)
    total_rewards += reward

    contract_points_this_epoch = reward * SECONDS_PER_EPOCH
    temp_total_points_acc += contract_points_this_epoch


  print_if("rewards")
  print_if(rewards)
  
  contract_points = total_rewards * SECONDS_PER_EPOCH

  for epoch in range(number_of_epochs):
    contract_points_per_epoch_cumulative.append(contract_points)
  
  acc = 0
  for epoch in range(number_of_epochs):
    if(epoch > 0):
      ## Remove acc
      contract_points_per_epoch_cumulative[epoch] -= acc
    
    ## Skip first one
    acc += rewards[epoch] * SECONDS_PER_EPOCH

  ## Ensure we are removing all points on first epoch
  assert contract_points == contract_points_per_epoch_cumulative[0]

  total_supply += total_rewards
  total_points = total_supply * SECONDS_PER_EPOCH

  ## Simulation of user claiming each epoch and contract properly re-computing divisor
  total_dust = 0
  total_claimed = 0

  cached_contract_points = contract_points

  ## SETUP total_points_claimed_per_epoch
  total_points_claimed_per_epoch = []

  ## Accumulator or previously claimed points to simulate contract points reduction over epoch
  total_previously_claim_epochs_ago = 0

  for epoch in range(number_of_epochs):
    total_points_claimed_per_epoch.append(0)

  for epoch in range(number_of_epochs):
    ## Subtract as the contract no longer has those points
    ## Equivalent to divisor = (total_points - (contract_points - contract_points_per_epoch * epoch))
    divisor = (total_points - contract_points_per_epoch_cumulative[epoch])
    
    print_if("epoch")
    print_if(epoch)


    for user in range(number_of_users):
      ## Skip for non-claimers
      if not (claiming[user]):
        continue

      user_total_rewards_fair = rewards[epoch] * points[user] // divisor
      user_total_rewards_dust = rewards[epoch] * points[user] % divisor

      claimed_points = user_total_rewards_fair * SECONDS_PER_EPOCH
      ## Add new rewards to user points for next epoch
      points[user] += claimed_points
      balances[user] += user_total_rewards_fair 

      claimed[user] += user_total_rewards_fair

      total_claimed += user_total_rewards_fair
      total_dust += user_total_rewards_dust
      total_previously_claim_epochs_ago += claimed_points
      total_points_claimed_per_epoch[epoch] += claimed_points

  ## Simulation of user claiming all epochs at end through new math
  ## They will use the updated balances, without reducing them (as they always claim at end of entire period)
  for epoch in range(number_of_epochs):
    divisor = (total_points - contract_points_per_epoch_cumulative[epoch])

    for user in range(number_of_users):
      ## Skip for claimers // Already done above
      if (claiming[user]):
        continue

      user_total_rewards_fair = rewards[epoch] * points[user] // divisor
      user_total_rewards_dust = rewards[epoch] * points[user] % divisor

      claimed_points = user_total_rewards_fair * SECONDS_PER_EPOCH
      ## Add new rewards to user points for next epoch
      points[user] += claimed_points
      balances[user] += user_total_rewards_fair 

      claimed[user] += user_total_rewards_fair

      total_claimed += user_total_rewards_fair
      total_dust += user_total_rewards_dust

  print_if("number_of_users")
  print_if(number_of_users)

  print_if("claimers")
  print_if(claimers)

  print_if("total_rewards")
  print_if(total_rewards)

  print_if("total_dust points")
  print_if(total_dust)

  print_if("total_claimed")
  print_if(total_claimed)

  print_if("total epochs")
  print_if(number_of_epochs)

  print_if("actual dust rewards")
  print_if(abs(total_rewards - total_claimed))

  print_if("Percent distributed over dusted")
  print_if((total_rewards - total_claimed) / total_rewards)

  
  ## 2 things about fairness
  ## Consistency -> Predictable unfairness is better than unpredictable fairness as it can be gamed to user advantage
  ## Always rounding down -> Any round up will break the accounting, it's extremely important we are "fair" but "stingy" in never giving more than what's correct

  for user in range(number_of_users):
    print_if("User")
    print_if(user)
    print_if("Deposit Ratio")
    deposit_ratio = initial_balances[user] / total_user_deposits * 100
    print_if(deposit_ratio)

    rewards_ratio = claimed[user] / total_rewards * 100
    print_if("Rewards Ratio")
    print_if(rewards_ratio)
    assert deposit_ratio >= rewards_ratio ## If it's >= we will leak value and get rekt
  
  print_if("Percent distributed over dusted")
  print_if((total_rewards - total_claimed) / total_rewards)

  return (total_rewards - total_claimed) / total_rewards

def main():
  fair_count = 0
  for x in range(ROUNDS):
    res = simple_users_sim()
    if res < 1e-18:
      fair_count += 1
    else:
      print("Unfair")
      print(res)
    
  print("Overall number of passing tests")
  print(fair_count)
  print("Overall Percent of passing tests")
  print(fair_count / ROUNDS * 100)
      