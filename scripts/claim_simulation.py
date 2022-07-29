"""
  Calculate Gas cost for 52 weeks of claims
  For 1 token
  For 5 tokens
  For 20 tokens

  NOTE: DO NOT RUN THIS ON MAINNET!!!!!
"""

from brownie import *
MaxUint256 = str(int(2 ** 256 - 1))
AddressZero = "0x0000000000000000000000000000000000000000"

TOKENS = 5
EPOCHS = 50 ## 1 Year with 1 epoch per week
INITIAL_MINT = 52_000_000
INITIAL_DEPOSIT = 100
def test_full_deposit_claim_one_year_of_rewards_with_optimization():
  deployer = accounts[0]

  initialized_contract = RewardsManager.deploy({"from": deployer})

  fake_vault = accounts[1]

  user = accounts[2]

  ## Make deposit for user
  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})


  tokens = []
  txs = []
  for x in range(TOKENS):
    token = FakeToken.deploy({"from": deployer})
    token.mint(deployer, INITIAL_MINT, {"from": deployer})
    tokens.append(token)

    token.approve(initialized_contract, MaxUint256, {"from": deployer})

    ## Add rewards for all epochs from 1 to EPOCHS
    add_tx = initialized_contract.addBulkRewardsLinearly(1, EPOCHS, fake_vault, token, INITIAL_MINT, {"from": deployer})
    txs.append(add_tx)
  
  ## Sleep until epochs have passed
  for x in range(EPOCHS):
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()
  

  ## Random tx to wake up ganache
  token.mint(deployer, 1, {"from": deployer})

  print("Epoch")
  print(initialized_contract.currentEpoch())

  ## Claim Bulk
  tx = initialized_contract.reap([1, EPOCHS, fake_vault, tokens], {"from": user})

  print("Gas Cost to add")
  print(EPOCHS)
  print("Of rewards")
  print(txs[-1].gas_used)

  print("Gas Cost to claim the rewards")
  print(tx.gas_used)

def main():
  test_full_deposit_claim_one_year_of_rewards_with_optimization()