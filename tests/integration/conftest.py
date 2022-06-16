import pytest
from brownie import TestVault


"""
  Extra set of fixtures for integration test with BadgerVaults
"""
@pytest.fixture(scope='module')
def deposit_amount():
  return 1e18

@pytest.fixture(scope='module')
def real_vault(token, initialized_contract, deployer, deposit_amount, user):
  v = TestVault.deploy(token, initialized_contract, {"from": deployer})

  token.approve(v, deposit_amount, {"from": user})
  v.deposit(deposit_amount, {"from": user})

  return v

