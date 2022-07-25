from random import seed
from random import random

USERS_MIN = 100
USERS_RANGE = 1000
SHARES_DECIMALS = 18
RANGE = 10_000 ## Shares can be from 1 to 10k with SHARES_DECIMALS
SECONDS_PER_EPOCH = 604800

## TODO: Change totalReward to be a APR with interesting interval, perhaps betwen 1 BPS and 10k%
TOTAL_REWARD = 100_000_000 * 10 ** 18 ## 10 k ETH example

def basic_simulation():
  """
    Basic Simulation for handling of self-emitting vaults and their points

    This is a simplified case where:
      - RewardsManager received the reward token an epoch before
      - Claiming is happening at end of epoch (entire accrual)
      - 
  """
  number_of_users = int(random() * USERS_RANGE) + USERS_MIN

  balances = []
  total_points = 0
  total_supply = 0
  points = []

  ## Reward will be added here at the 0th entry
  contract_points = TOTAL_REWARD * SECONDS_PER_EPOCH
  total_supply += TOTAL_REWARD
  total_points += contract_points

  balances.append(TOTAL_REWARD)
  points.append(contract_points)

  ## Ensure we're adding to 0 entry
  assert balances[0] == TOTAL_REWARD
  assert points[0] == contract_points

  ## Simulate user balances and points
  for x in range(number_of_users):
    balance = int(random() * 10 ** SHARES_DECIMALS * RANGE)
    user_points = balance * SECONDS_PER_EPOCH
    balances.append(balance)
    points.append(user_points)
    total_supply += balance
    total_points += user_points

  
  ## Simulate claim amounts - UNFAIR

  ## Distribute all points minus the contract points over this epoch
  ## All users are equally short-handed

  dust_unfair = []
  sum_of_dust_unfair = 0
  rewards_unfair = []
  sum_of_rewards_unfair = 0
  ## Calculate user points and dust
  for x in range(number_of_users):
    user_points = points[x + 1]

    user_reward = TOTAL_REWARD * user_points // total_points
    user_dust = TOTAL_REWARD * user_points % total_points

    rewards_unfair.append(user_reward)
    dust_unfair.append(user_dust)

    sum_of_dust_unfair += user_dust
    sum_of_rewards_unfair += user_reward

  
  ## Simulate claim amounts - FAIR

  ## Distribute all points plus the contract points over this epoch
  ## All users should receive all rewards, fairly
  dust = []
  sum_of_dust = 0
  rewards = []
  sum_of_rewards = 0
  for x in range(number_of_users):
    user_points = points[x+1] ## 0 is contract

    ## TO REDUCE DUST Use Distributive Property
    contract_claimable_tokens = TOTAL_REWARD * contract_points // total_points

    # user_reward_before_contract = TOTAL_REWARD * user_points // total_points
    # contract_claimable_tokens = TOTAL_REWARD * contract_points // total_points
    # user_share_of_contract_points = contract_claimable_tokens * user_points // total_points
    # total_user_rewards = user_share_of_contract_points + user_reward_before_contract

    user_total_rewards = (TOTAL_REWARD + contract_claimable_tokens) * user_points // total_points

    user_dust = (TOTAL_REWARD + contract_claimable_tokens) * user_points % total_points

    rewards.append(user_total_rewards)
    dust.append(user_dust)

    sum_of_dust += user_dust
    sum_of_rewards += user_total_rewards

  print("sum_of_dust_unfair")
  print(sum_of_dust_unfair)

  print("sum_of_dust")
  print(sum_of_dust)

  print("total_points")
  print(total_points)

  print("Contract Points")
  print(points[0])

  print("Random User Points 1")
  print(points[1])
  print("Random User Points 2")
  print(points[2])
  print("Random User Points 3")
  print(points[3])
  print("Random User Points 4")
  print(points[4])
  print("Random User Points 5")
  print(points[5])

  print("TOTAL_REWARD")
  print(TOTAL_REWARD)

  print("sum_of_rewards_unfair")
  print(sum_of_rewards_unfair)

  print("sum_of_rewards")
  print(sum_of_rewards)

  print("sum_of_rewards - sum_of_rewards_unfair")
  print(sum_of_rewards - sum_of_rewards_unfair)

  print("deltas")
  print("Unfair")
  print(TOTAL_REWARD - sum_of_rewards_unfair)
  print("as percent")
  print(abs(TOTAL_REWARD - sum_of_rewards_unfair) / TOTAL_REWARD)

  print("Fair")
  print(TOTAL_REWARD - sum_of_rewards)
  print("as percent")
  print(abs(TOTAL_REWARD - sum_of_rewards) / TOTAL_REWARD)







def main():
  basic_simulation()
