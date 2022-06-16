from brownie import chain
from brownie.test import given, strategy

from helpers.utils import approx


MaxUint256 = str(int(2 ** 256 - 1))

"""
  Integration tests with a real vault contract to check edge cases, emissions of vault tokens, etc..
"""


"""
  Test deposit with a real vault
"""
def test_full_deposit_one_user(initialized_contract, user, real_vault, token):
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards here
  token.approve(initialized_contract, MaxUint256, {"from": user})
  initialized_contract.addReward(EPOCH, real_vault, token, REWARD_AMOUNT, {"from": user})

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = token.balanceOf(user)

  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Claim rewards here
  initialized_contract.claimReward(EPOCH, real_vault, token, user)

  ## Verify you got the entire amount
  assert token.balanceOf(user) == initial_reward_balance + REWARD_AMOUNT



"""
  What happens if we emit the vault as the reward token?
"""
def test_basic_with_vault_emitted(initialized_contract, user, real_vault, token, deployer):
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards as form of vault token here
  token.approve(real_vault, MaxUint256, {"from": deployer})
  real_vault.deposit(REWARD_AMOUNT, {"from": deployer})
  real_vault.approve(initialized_contract, MaxUint256, {"from": deployer})
  initialized_contract.addReward(EPOCH, real_vault, real_vault, REWARD_AMOUNT, {"from": deployer})

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = real_vault.balanceOf(user)
  initial_deployer_balance = real_vault.balanceOf(deployer)

  assert initial_deployer_balance == 0 ## 0 cause we sent all as reward

  ## Wait the epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Claim rewards here
  initialized_contract.claimReward(EPOCH, real_vault, real_vault, user)
  initialized_contract.claimReward(EPOCH, real_vault, real_vault, deployer)

  ## Verify that all rewards were distributed (minus 1 approx due to rounding)
  assert approx(real_vault.balanceOf(user) + real_vault.balanceOf(deployer), initial_reward_balance + REWARD_AMOUNT, 1)


"""
  Same as above but let's skip one epoch for rewards
"""
def test_basic_with_vault_emitted_with_empty_epoch(initialized_contract, user, real_vault, token, deployer):
  REWARD_AMOUNT = 1e20
  EPOCH = initialized_contract.currentEpoch() + 1

  ## Add rewards as form of vault token here
  token.approve(real_vault, MaxUint256, {"from": deployer})
  real_vault.deposit(REWARD_AMOUNT, {"from": deployer})
  real_vault.approve(initialized_contract, MaxUint256, {"from": deployer})
  initialized_contract.addReward(EPOCH, real_vault, real_vault, REWARD_AMOUNT, {"from": deployer})

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = real_vault.balanceOf(user)
  initial_deployer_balance = real_vault.balanceOf(deployer)

  assert initial_deployer_balance == 0 ## 0 cause we sent all as reward

  ## Wait the initial epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Wait the rewards epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Claim rewards here
  initialized_contract.claimReward(EPOCH, real_vault, real_vault, user)
  initialized_contract.claimReward(EPOCH, real_vault, real_vault, deployer)

  ## Verify that all rewards were distributed (minus 1 approx due to rounding)
  assert approx(real_vault.balanceOf(user) + real_vault.balanceOf(deployer), initial_reward_balance + REWARD_AMOUNT, 1)


"""
  Add rewards for epoch 1 and 2
  Claim for epoch 1
"""
@given(reward_amount=strategy('uint256', min_value=1e16, max_value=1e20))
def test_basic_with_vault_two_epochs_of_reward(initialized_contract, user, real_vault, token, deployer, reward_amount):
  EPOCH = initialized_contract.currentEpoch()

  ## Add rewards as form of vault token here
  token.approve(real_vault, MaxUint256, {"from": deployer})
  real_vault.deposit(reward_amount * 2, {"from": deployer})
  real_vault.approve(initialized_contract, MaxUint256, {"from": deployer})
  initialized_contract.addReward(EPOCH, real_vault, real_vault, reward_amount, {"from": deployer})
  initialized_contract.addReward(EPOCH + 1, real_vault, real_vault, reward_amount, {"from": deployer})

  ## Because user has the tokens too, we check the balance here
  initial_reward_balance = real_vault.balanceOf(user)
  initial_deployer_balance = real_vault.balanceOf(deployer)

  assert initial_deployer_balance == 0 ## 0 cause we sent all as reward

  ## Wait the initial epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Wait the rewards epoch to end
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
  chain.mine()

  ## Claim rewards here
  initialized_contract.claimReward(EPOCH, real_vault, real_vault, user)
  initialized_contract.claimReward(EPOCH, real_vault, real_vault, deployer)
  initialized_contract.claimReward(EPOCH + 1, real_vault, real_vault, user)
  initialized_contract.claimReward(EPOCH + 1, real_vault, real_vault, deployer)

  ## Verify that all rewards were distributed (minus 1 approx due to rounding)
  assert approx(real_vault.balanceOf(user) + real_vault.balanceOf(deployer), initial_reward_balance + reward_amount * 2, 1)

  ## DUST
  dust = initialized_contract.dust(EPOCH, real_vault, real_vault)
  assert dust == 0 or dust == 1 ## There may be some dust and we can claim it

  ## More exactly dust / total points is 1, meaning we didn't distribute 1 token

  total_points = initialized_contract.totalPoints(EPOCH, real_vault)
  contract_points = initialized_contract.points(EPOCH, real_vault, initialized_contract)

  assert dust // (total_points - contract_points) == 0 or dust // (total_points - contract_points) == 1
