from json.encoder import INFINITY
from random import random

"""
  See rationale:
  https://github.com/GalloDaSballo/badger-onchain-rewards/commit/f7e6a4f892bead6d638dcfe24a39a509fff45a37#diff-9c271c60ebb0eb3b8e6a08686dba223679026ff6d2323ee3b25391adffb5c718

    Sum of x and y
    REWARDS_Y * r / MAX_BPS + SUM_0_infinity(
        if(i = 0) {
            y = REWARDS_Y * r / MAX_BPS
        } else {
            y = x_i_-1 / TOTAL_SUPPLY_X * REWARDS_Y
        }
        x_i =  y_i / TOTAL_SUPPLY_Y * REWARDS_X
    )

    TODO: Just bruteforce a sim to see what happens

    This sim brute forces the above to "intuitively" show that the value converges


    Received Y
    y_1 = Y * r / MAX_BPS

    Received X from y_1
    x_1 = y_1 / Y * X

    Received Y from x_1
    y_2 = x_1 / X * Y

"""

MAX_BPS = 10_000
DECIMALS = 18

CIRCULATING_X = random() * 1000 * 1e18
CIRCULATING_Y = random() * 1000 * 1e18
# REWARDS_X = 100000 * 1e18
# REWARDS_Y = 100000 * 1e18
REWARDS_X = random() * 1000 * 1e18
REWARDS_Y = random() * 1000 * 1e18
## TODO: If we set rewards to way higher we do get reverts, I think it's due to the Circulating vs Rewards math
## Meaning we must divide by total supply as we must assume all tokens are circulating in an infinite recursion

## TODO: Add to check
TOTAL_SUPPLY_X = CIRCULATING_X + REWARDS_X
TOTAL_SUPPLY_Y = CIRCULATING_Y + REWARDS_Y

DAMPENER = 1_000 ## 10% of the token is circulating hence the math will be MAX_BPS-dampener

r = random() * MAX_BPS

## Simulates going to infinite
ROUNDS = 10_000

def main():
  do_sum()

def do_sum():
  x = 0
  y = 0

  ## First round here
  y = r / MAX_BPS * REWARDS_Y ## First Claim
  print("first round y", y)

  ## `r`` implies this
  start_x = r / MAX_BPS * TOTAL_SUPPLY_X

  ## To retrieve prev value, TODO: Use array to store all values
  last_y = y
  last_x = 0

  for i in range(ROUNDS):
    if (i > 0 and (last_y == 0 or last_x == 0)):
      print("We're at 0, we're done")
      return

    
    new_last_x = last_y / TOTAL_SUPPLY_Y * REWARDS_X
    print("new_last_x", new_last_x)
    print("last_x", last_x)
    ## Avoid infinite recursion
    # assert new_last_x != last_x
    # assert new_last_x < last_x

    last_x = new_last_x

    x += last_x

    new_last_y = last_x / TOTAL_SUPPLY_X * REWARDS_Y
    print("new_last_y", new_last_y)
    print("last_y", last_y)
    ## Avoid infinite recursion
    # assert new_last_y != last_y
    # assert new_last_y < last_y

    last_y = new_last_y
    y += last_y
    print("last_y", last_y)
    print("last_y / Y", last_y / REWARDS_Y)
  

  print("y", y)
  print("REWARDS_Y", REWARDS_Y)
  assert y <= REWARDS_Y

  ## TODO: Is this correct? Do we want this check?
  ## NOTE: Prob wrong check, once I can write this check i can write a linear approx of the recursive math
  ## Meaning I may be able to skip the recursion if I can figure out what this check should look like
  ## Most likely the asymptote of the limit of the succession
  # assert y == REWARDS_Y * r / MAX_BPS

  print("x", x)
  print("REWARDS_X + start_x", REWARDS_X + start_x)
  assert x < REWARDS_X + start_x

  




