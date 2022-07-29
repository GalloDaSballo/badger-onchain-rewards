from random import seed
from random import random

USERS_RANGE = 1_000_000
SHARES_DECIMALS = 18
RANGE = 10_000_000_000 ## Shares can be from 1 to 10M with SHARES_DECIMALS
SECONDS_PER_EPOCH = 604800

TOTAL_REWARD = 10 ** 6 ## 10 USDC example

def simulation():
  number_of_users = int(random() * USERS_RANGE)
  balances = []
  total_points = 0
  total_supply = 0
  points = []
  for x in range(number_of_users):
    balance = int(random() * 10 ** SHARES_DECIMALS * RANGE)
    user_points = balance * SECONDS_PER_EPOCH
    balances.append(balance)
    points.append(user_points)
    total_supply += balance
    total_points += user_points

  print(balances)
  print(total_supply)
  print(total_points)


  dust = []
  sum_of_dust = 0
  rewards = []
  ## Calculate user points and dust
  for x in range(number_of_users):
    user_points = points[x]

    user_reward = TOTAL_REWARD * user_points // total_points
    user_dust = TOTAL_REWARD * user_points % total_points

    rewards.append(user_reward)
    dust.append(user_dust)

    sum_of_dust += user_dust
  
  print(dust)
  print(rewards)
  print(sum_of_dust)
  print(number_of_users)
  print(sum_of_dust // total_points)











def main():
  simulation()

