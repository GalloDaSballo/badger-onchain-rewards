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

MIN_REWARDS_PER_EPOCH = 1_000 ## 10 k ETH example
REWARD_PER_EPOCH = 100_000 ## 100 k ETH example
USERS_RANGE = 10
USERS_MIN = 3


## How many simulations to run?
ROUNDS = 10_000

## Should the print_if print stuff?
SHOULD_PRINT = ROUNDS == 1