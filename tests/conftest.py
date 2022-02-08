from brownie import *
from dotmap import DotMap
import pytest

"""
  Deploy the Contract
  Set up one reward
  Set up one vault -> Avoided by using an account
"""




@pytest.fixture
def deployer():
    return accounts[0]

## We pretend the vault is a contract as there's no difference
## Only thing is we gotta keep track of "balances" and supply ourselves
## TODO (after more tests), add a real V1.5 vault and integrate it
@pytest.fixture
def fake_vault():
    return accounts[1]

@pytest.fixture
def user():
    return accounts[2]

@pytest.fixture
def token():
    return interface.IERC20("0x3472A5A71965499acd81997a54BBA8D852C6E53d")




@pytest.fixture
def rewards_contract(deployer):
    """
      Deploys the Contract without any setup
    """

    contract = RewardsManager.deploy({"from": deployer})

    return contract 


@pytest.fixture
def initialized_contract(deployer):
    """
    Deploys the contract with full setup (epoch, rewards, deposit)
    """

    contract = RewardsManager.deploy({"from": deployer})
    contract.startNextEpoch({"from": deployer})

    return contract 


@pytest.fixture
def setup_contract(deployer):
    """
    Deploys the contract with full setup (epoch, rewards, deposit)
    """

    contract = RewardsManager.deploy({"from": deployer})
    contract.startNextEpoch({"from": deployer})

    ## TODO: Add a deposit
    ## TODO: Add rewards

    return contract 

## Forces reset before each test
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


