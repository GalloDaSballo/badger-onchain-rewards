from random import seed
from random import random

EPOCHS_RANGE = 10
EPOCHS_MIN = 1
SHARES_DECIMALS = 18
RANGE = 10_000 ## Shares can be from 1 to 10k with SHARES_DECIMALS
MIN_SHARES = 1_000 ## Min shares per user
SECONDS_PER_EPOCH = 604800

REWARD_PER_EPOCH = 10_000 * 10 ** SHARES_DECIMALS ## 10 k ETH example

def simple_sim():
  print("*** SIMPLE ****")
  balance = int(random() * RANGE) + MIN_SHARES
  user_points = balance * SECONDS_PER_EPOCH

  number_of_epochs = int(random() * EPOCHS_RANGE) + EPOCHS_MIN

  total_rewards = REWARD_PER_EPOCH * number_of_epochs
  contract_points = total_rewards * SECONDS_PER_EPOCH
  contract_points_per_epoch = REWARD_PER_EPOCH * SECONDS_PER_EPOCH

  total_supply = balance + total_rewards

  total_points = total_supply * SECONDS_PER_EPOCH

  ## Simulation of user claiming each epoch and contract properly re-computing divisor

  for epoch in range(number_of_epochs):
    print("User percent of total")
    print(user_points / total_points * 100)

    user_total_rewards_unfair = REWARD_PER_EPOCH * user_points // total_points
    user_dust_unfair = REWARD_PER_EPOCH * user_points % total_points

    print("user_total_rewards_unfair")
    print(user_total_rewards_unfair)
    print("user_dust_unfair")
    print(user_dust_unfair)

    user_total_rewards_fair = REWARD_PER_EPOCH * user_points // (total_points - (contract_points - contract_points_per_epoch * epoch))
    user_total_rewards_dust = REWARD_PER_EPOCH * user_points % (total_points - (contract_points - contract_points_per_epoch * epoch))

    temp_user_points = user_points
    ## Add new rewards to user points for next epoch
    user_points = temp_user_points + user_total_rewards_fair * SECONDS_PER_EPOCH

    print("user_total_rewards_fair")
    print(user_total_rewards_fair)
    print("user_total_rewards_dust")
    print(user_total_rewards_dust)

  print("*** END SIMPLE ****")

def main():
  simple_sim()
