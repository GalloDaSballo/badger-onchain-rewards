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
    y_2 = x_1 / TOTAL_SUPPLY_X * Y

    x_2 = y_2 / TOTAL_SUPPLY_Y * X
    y_3 = x_2 / TOTAL_SUPPLY_X * Y


    y_2 = x_1 / TOTAL_SUPPLY_X * Y
    y_2 = (y_1 / TOTAL_SUPPLY_Y * X) / TOTAL_SUPPLY_X * Y
    y_2 = ((Y * r / MAX_BPS) / TOTAL_SUPPLY_Y * X) / TOTAL_SUPPLY_X * Y
    y_2 = ((Y * x_0 / TOTAL_SUPPLY_X) / TOTAL_SUPPLY_Y * X) / TOTAL_SUPPLY_X * Y
    
  

    Linear Form
    -> See Python
    -> TODO: Rewrite and put on paper or smth
    TODO: Figure out exactly what formula to use, see python rounding vs non-round
    We need exact formula, 1 value approx is not acceptable

    Limit Solution by @camotelli:
    https://hackmd.io/@re73/rJeQL-sGs

    ## HOW DO WE PROVE LIMIT CONVERGES?
    -> Demonstrate r < 1
    -> Take the limit and simplify

    ## TODO: Rest
    Once we prove limit is correct
    We need to prove that Sum(X -> Y -> Z*)
    Is equivalent to
    X -> Y
    Y -> Z*

    Meaning that we can deal with X -> Y as infinitely recursing
    Then get the Y we retrieve
    And use that to calculate the Z we receive (because  Y == SUM(y_i), means reward(Y) == reward(SUM(y_i) == Y))

    Last piece is to figure out if multiple knots cause issues and how to simplify them to avoid getting rekt

"""

## On Multiple Recursions
"""
  If we have multiple knots, then

  X -> Y -> X..... -> Y
                        -> Z -> X
         -> Z -> X -> Y
                        -> Z -> X

  With Z -> ... -> N
  And
  M -> Z -> ... N

"""

MAX_BPS = 10_000
DECIMALS = 1 ## Issue with Infinity with 18 decimals and exponentiation

## making start circulation friendly to convergence compared to total supply or rewards, e.g., start ciculation is (1 / 1 Million) of total supply 
CIRCULATING_X = random() * 1000 * 1e18
CIRCULATING_Y = random() * 1000 * 1e18
# REWARDS_X = 100000 * 1e18
# REWARDS_Y = 100000 * 1e18

## TODO: When one of rewards is higher than Circulating, it always gives out more rewards than expected
REWARDS_X = random() * 1000 * 1e18
REWARDS_Y = random() * 1000 * 1e18
## TODO: If we set rewards to way higher we do get reverts, I think it's due to the Circulating vs Rewards math
## Meaning we must divide by total supply as we must assume all tokens are circulating in an infinite recursion
## TODO: There are situations where we give too much rewards, need to figure that out
## TODO: Add to check
TOTAL_SUPPLY_X = CIRCULATING_X + REWARDS_X
assert TOTAL_SUPPLY_X > REWARDS_X
TOTAL_SUPPLY_Y = CIRCULATING_Y + REWARDS_Y
assert TOTAL_SUPPLY_Y > REWARDS_Y

r = random() * MAX_BPS

## Simulates going to infinite
TESTS = 100 ## How many sims to run
SIM_ROUNDS = 100000 ## NOTE: Exponentiation test stops at 10 rounds due to Overflow

def main():
  for x in range(TESTS):
    do_sum()

def do_sum():
  x = 0
  y = 0

  ## `r`` implies this
  start_x = r / MAX_BPS * CIRCULATING_X

  ## First round here
  y = start_x * REWARDS_Y // TOTAL_SUPPLY_X  ## First Claim
  print("first round y", y)

  ## To retrieve prev value, TODO: Use array to store all values
  last_y = y
  last_x = 0

  for i in range(SIM_ROUNDS):
    i = i + 1
    print("** Round ** ", i)
    if (i - 1 > 0 and (last_y == 0 or last_x == 0)):
      print("We're at 0, we're done")
      break

    
    new_last_x = last_y * REWARDS_X // TOTAL_SUPPLY_Y 
    print("new_last_x", new_last_x)
    print("last_x", last_x)
    ## Avoid infinite recursion
    # assert new_last_x != last_x
    # assert new_last_x < last_x

    ## TODO: Make this work for all i
    # from_theoretical_formula_x = (start_x * REWARDS_X ** (i + 1) * REWARDS_Y ** (i + 1)) / (TOTAL_SUPPLY_X ** (i + 1) * TOTAL_SUPPLY_Y ** (i + 1))
    if(i < 10):
      from_theoretical_formula_x = start_x * REWARDS_X ** (i) // (TOTAL_SUPPLY_X ** (i)) * REWARDS_Y ** (i) // TOTAL_SUPPLY_Y ** (i)
      print("from_theoretical_formula_x", from_theoretical_formula_x)
      ## They are the same approx by 1^-18
      ## -1 as we have a rounding error due to single floor due to issue with exponentiation overflow
      # assert (
      #   new_last_x == from_theoretical_formula_x or new_last_x == from_theoretical_formula_x - 1 or new_last_x == from_theoretical_formula_x + 1 or

      #   ## TODO: MUST explain this, but for now we'll live with this
      #   ## This means our check is ok, for the previous estimate, meaning somehow we're looking back or something
      #   ## Again TODO explain this as it may break the math
      #   last_x == from_theoretical_formula_x or last_x == from_theoretical_formula_x - 1 or last_x == from_theoretical_formula_x + 1
      # )




    last_x = new_last_x

    x += last_x

    new_last_y = last_x * REWARDS_Y // TOTAL_SUPPLY_X

    ## TODO: Make this work for all i
    if(i < 10):
      # from_theoretical_formula_y =  (start_x * REWARDS_X ** (i) * REWARDS_Y ** (i + 1)) / (TOTAL_SUPPLY_X ** (i + 1) * TOTAL_SUPPLY_Y ** (i))
      from_theoretical_formula_y =  (start_x * REWARDS_X ** (i)) / (TOTAL_SUPPLY_X ** (i + 1)) * REWARDS_Y ** (i + 1) //  TOTAL_SUPPLY_Y ** (i)
      print("new_last_y", new_last_y)
      print("last_y", last_y)
      print("from_theoretical_formula_y", from_theoretical_formula_y)
      # assert (
      #   from_theoretical_formula_y == new_last_y or new_last_y == from_theoretical_formula_y - 1 or new_last_y == from_theoretical_formula_y + 1 or
        
      #   ## TODO: MUST explain this, but for now we'll live with this
      #   ## This means our check is ok, for the previous estimate, meaning somehow we're looking back or something
      #   ## Again TODO explain this as it may break the math
      #   last_y == from_theoretical_formula_y or last_y == from_theoretical_formula_y - 1 or last_y == from_theoretical_formula_y + 1
      # )
    ## Avoid infinite recursion
    # assert new_last_y != last_y
    # assert new_last_y < last_y

    last_y = new_last_y
    y += last_y
    print("last_y", last_y)
    print("last_y / Y", last_y / REWARDS_Y)

  

  print("CIRCULATING_X", CIRCULATING_X)
  print("CIRCULATING_Y", CIRCULATING_Y)
  print("REWARDS_X", REWARDS_X)
  print("REWARDS_Y", REWARDS_Y)
  

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

  ## check theoretically the summation limit for rewards
  ## ref https://en.wikipedia.org/wiki/Geometric_series#Closed-form_formula
  z_0 = start_x * REWARDS_Y / TOTAL_SUPPLY_X
  print("z_0", z_0)
  ab = (REWARDS_X / TOTAL_SUPPLY_Y) * (REWARDS_Y / TOTAL_SUPPLY_X)
  print("ab", ab)
  oneMinusAB = 1 - ab
  print("oneMinusAB", oneMinusAB)
  sumRewardLimitY = z_0 + (z_0 * ab / oneMinusAB)
  sumRewardLimitX = (z_0 * REWARDS_X / TOTAL_SUPPLY_Y) / oneMinusAB
  print("reward summation limit in X=", sumRewardLimitX)
  print("reward summation limit in Y=", sumRewardLimitY)
  diffInX = abs(x - sumRewardLimitX) / x
  diffInY = abs(y - sumRewardLimitY) / y

  print("difference ratio btw summation limit and simulation for X=", diffInX)
  print("difference ratio btw summation limit and simulation for Y=", diffInY)
  
  ## TODO: Need Way more precision
  assert diffInX < 1e-15
  assert diffInY < 1e-15

