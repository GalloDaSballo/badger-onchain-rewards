from random import seed
from random import random

EPOCHS_RANGE = 10
EPOCHS_MIN = 1
SHARES_DECIMALS = 18
RANGE = 10_000 ## Shares can be from 1 to 10k with SHARES_DECIMALS
MIN_SHARES = 1_000 ## Min shares per user
SECONDS_PER_EPOCH = 604800

REWARD_PER_EPOCH = 10_000 * 10 ** SHARES_DECIMALS ## 10 k ETH example
USERS_RANGE = 10
USERS_MIN = 3

SHOULD_PRINT = True

def print_if(v):
  if SHOULD_PRINT:
    print(v)


"""
  Basic test showing how compound and non-compound claims will work
  Assumes that rewards per epoch are always the same
"""
  

def simple_users_sim():

  number_of_epochs = int(random() * EPOCHS_RANGE) + EPOCHS_MIN
  number_of_users = int(random() * USERS_RANGE) + USERS_MIN

  total_user_deposits = 0

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
    balance = int(random() * RANGE) + MIN_SHARES
    balances.append(balance)


    initial_balances.append(balance)
    total_user_deposits += balance
    claimed.append(0)

    user_points = balance * SECONDS_PER_EPOCH
    points.append(user_points)

    total_supply += balance
    
  total_rewards = REWARD_PER_EPOCH * number_of_epochs
  contract_points = total_rewards * SECONDS_PER_EPOCH
  contract_points_per_epoch = REWARD_PER_EPOCH * SECONDS_PER_EPOCH

  total_supply += total_rewards

  total_points = total_supply * SECONDS_PER_EPOCH

  ## Simulation of user claiming each epoch and contract properly re-computing divisor
  total_dust = 0
  total_claimed = 0

  cached_contract_points = contract_points

  ## SETUP total_points_claimed_per_epoch
  total_points_claimed_per_epoch = []

  for epoch in range(number_of_epochs):
    total_points_claimed_per_epoch.append(0)


  for epoch in range(number_of_epochs):
    ## Divisor for this epoch
    ## Equivalent to divisor = (total_points - (contract_points - contract_points_per_epoch * epoch))
    divisor = (total_points - contract_points_per_epoch * (number_of_epochs - epoch))

    for user in range(number_of_users):
      ## Skip for non-claimers
      if not (claiming[user]):
        continue
      
      print_if("User percent of total")
      print_if(points[user] / total_points * 100)

      user_total_rewards_unfair = REWARD_PER_EPOCH * points[user] // total_points
      user_dust_unfair = REWARD_PER_EPOCH * points[user] % total_points

      print_if("user_total_rewards_unfair")
      print_if(user_total_rewards_unfair)
      print_if("user_dust_unfair")
      print_if(user_dust_unfair)


      user_total_rewards_fair = REWARD_PER_EPOCH * points[user] // divisor
      user_total_rewards_dust = REWARD_PER_EPOCH * points[user] % divisor


      claimed_points = user_total_rewards_fair * SECONDS_PER_EPOCH
      ## Add new rewards to user points for next epoch
      points[user] += claimed_points
      balances[user] += user_total_rewards_fair 

      claimed[user] += user_total_rewards_fair

      print_if("user_total_rewards_fair")
      print_if(user_total_rewards_fair)
      print_if("user_total_rewards_dust")
      print_if(user_total_rewards_dust)
      total_claimed += user_total_rewards_fair
      total_dust += user_total_rewards_dust
      total_points_claimed_per_epoch[epoch] += claimed_points
    
    ## Subtract points at end of epoch
    contract_points -= total_points_claimed_per_epoch[epoch]

    ## integrity test
    acc = 0
    for user in range(number_of_users):
      acc += points[user]
    
    assert acc + contract_points == total_points

  
  ## After the weekly claimers sim, reset
  contract_points = cached_contract_points

  ## Simulation of user claiming all epochs at end through new math
  ## They will use the updated balances, without reducing them (as they always claim at end of entire period)
  for epoch in range(number_of_epochs):
    ## Equivalent to divisor = (total_points - (contract_points - contract_points_per_epoch * epoch))
    divisor = (total_points - contract_points_per_epoch * (number_of_epochs - epoch))

    for user in range(number_of_users):
      ## Skip for claimers // Already done above
      if (claiming[user]):
        continue
      
      print_if("User percent of total")
      print_if(points[user] / total_points * 100)

      user_total_rewards_unfair = REWARD_PER_EPOCH * points[user] // total_points
      user_dust_unfair = REWARD_PER_EPOCH * points[user] % total_points

      print_if("user_total_rewards_unfair")
      print_if(user_total_rewards_unfair)
      print_if("user_dust_unfair")
      print_if(user_dust_unfair)

      user_total_rewards_fair = REWARD_PER_EPOCH * points[user] // divisor
      user_total_rewards_dust = REWARD_PER_EPOCH * points[user] % divisor

      claimed_points = user_total_rewards_fair * SECONDS_PER_EPOCH
      ## Add new rewards to user points for next epoch
      points[user] += claimed_points
      balances[user] += user_total_rewards_fair 

      claimed[user] += user_total_rewards_fair

      print_if("user_total_rewards_fair")
      print_if(user_total_rewards_fair)
      print_if("user_total_rewards_dust")
      print_if(user_total_rewards_dust)
      total_claimed += user_total_rewards_fair
      total_dust += user_total_rewards_dust
    
    ## At end of current epoch, subtract points claimed by claimers from previous loop (weekly claimers)
    ## Subtract points at end of epoch
    contract_points -= total_points_claimed_per_epoch[epoch]

    ## integrity test TODO: OUT OF WACK DUE TO HOW WE DO POINTS
    # acc = 0
    # for user in range(number_of_users):
    #   acc += points[user]
    # print("acc + contract_points == total_points")
    # print(acc + contract_points)
    # print(total_points)
    # assert acc + contract_points == total_points


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
    print_if(initial_balances[user] / total_user_deposits * 100)
    print_if("Rewards Ratio")
    print_if(claimed[user] / total_rewards * 100)
  
  print_if("Percent distributed over dusted")
  print_if((total_rewards - total_claimed) / total_rewards)

  return (total_rewards - total_claimed) / total_rewards

ROUNDS = 1000

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
      