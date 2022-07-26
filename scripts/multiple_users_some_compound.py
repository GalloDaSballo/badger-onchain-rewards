from random import seed
from random import random

EPOCHS_RANGE = 10
EPOCHS_MIN = 1
SHARES_DECIMALS = 18
RANGE = 10_000 ## Shares can be from 1 to 10k with SHARES_DECIMALS
MIN_SHARES = 1_000 ## Min shares per user
SECONDS_PER_EPOCH = 604800

REWARD_PER_EPOCH = 10_000 * 10 ** SHARES_DECIMALS ## 10 k ETH example
USERS_RANGE = 1000
USERS_MIN = 3

def simple_users_sim():

  number_of_epochs = int(random() * EPOCHS_RANGE) + EPOCHS_MIN
  number_of_users = int(random() * USERS_RANGE) + USERS_MIN

  claiming = [] ## Is the user strat to claim each week
  claimers = 0
  balances = []
  points = []
  total_supply = 0
  total_points = 0
  for user in range(number_of_users):
    is_claiming = random() >= 0.5
    claimers += 1 if is_claiming else 0
    claiming.append(is_claiming)
    balance = int(random() * RANGE) + MIN_SHARES
    balances.append(balance)

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
  for epoch in range(number_of_epochs):
    for user in range(number_of_users):
      ## Skip for non-claimers
      if not (claiming[user]):
        continue
      
      print("User percent of total")
      print(points[user] / total_points * 100)

      user_total_rewards_unfair = REWARD_PER_EPOCH * points[user] // total_points
      user_dust_unfair = REWARD_PER_EPOCH * points[user] % total_points

      print("user_total_rewards_unfair")
      print(user_total_rewards_unfair)
      print("user_dust_unfair")
      print(user_dust_unfair)

      divisor = (total_points - (contract_points - contract_points_per_epoch * epoch))

      user_total_rewards_fair = REWARD_PER_EPOCH * points[user] // divisor
      user_total_rewards_dust = REWARD_PER_EPOCH * points[user] % divisor

      temp_user_points = points[user]
      ## Add new rewards to user points for next epoch
      points[user] = temp_user_points + user_total_rewards_fair * SECONDS_PER_EPOCH
      balances[user] += user_total_rewards_fair 

      print("user_total_rewards_fair")
      print(user_total_rewards_fair)
      print("user_total_rewards_dust")
      print(user_total_rewards_dust)
      total_claimed += user_total_rewards_fair
      total_dust += user_total_rewards_dust

  ## Simulation of user claiming all epochs at end through new math
  for epoch in range(number_of_epochs):
    for user in range(number_of_users):
      ## Skip for claimers // Already done above
      if (claiming[user]):
        continue
      
      print("User percent of total")
      print(points[user] / total_points * 100)

      user_total_rewards_unfair = REWARD_PER_EPOCH * points[user] // total_points
      user_dust_unfair = REWARD_PER_EPOCH * points[user] % total_points

      print("user_total_rewards_unfair")
      print(user_total_rewards_unfair)
      print("user_dust_unfair")
      print(user_dust_unfair)

      divisor = (total_points - (contract_points - contract_points_per_epoch * epoch))

      user_total_rewards_fair = REWARD_PER_EPOCH * points[user] // divisor
      user_total_rewards_dust = REWARD_PER_EPOCH * points[user] % divisor

      temp_user_points = points[user]
      ## Add new rewards to user points for next epoch
      points[user] = temp_user_points + user_total_rewards_fair * SECONDS_PER_EPOCH
      balances[user] += user_total_rewards_fair 

      print("user_total_rewards_fair")
      print(user_total_rewards_fair)
      print("user_total_rewards_dust")
      print(user_total_rewards_dust)
      total_claimed += user_total_rewards_fair
      total_dust += user_total_rewards_dust


  print("number_of_users")
  print(number_of_users)

  print("claimers")
  print(claimers)

  print("total_dust points")
  print(total_dust)

  print("total_claimed")
  print(total_claimed)

  print("total epochs")
  print(number_of_epochs)

  print("actual dust rewards")
  print(abs(total_rewards - total_claimed))

  print("Percent distributed over dusted")
  print((total_rewards - total_claimed) / total_rewards)


def main():
  simple_users_sim()
