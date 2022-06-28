from brownie import RewardsManager, accounts, interface, TestVault
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
def second_user():
    return accounts[3]

@pytest.fixture
def token(user, deployer):
    whale = accounts.at("0xD0A7A8B98957b9CD3cFB9c0425AbE44551158e9e", force=True)
    t = interface.IERC20("0x3472A5A71965499acd81997a54BBA8D852C6E53d")
    t.transfer(user, t.balanceOf(whale) // 2, {"from": whale})
    t.transfer(deployer, t.balanceOf(whale) // 2, {"from": whale})
    return t

@pytest.fixture
def wbtc():
    return interface.IERC20("0x2260fac5e5542a773aa44fbcfedf7c193bc2c599")

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

    return contract


@pytest.fixture
def setup_contract(deployer):
    """
    Deploys the contract with full setup (epoch, rewards, deposit)
    """

    contract = RewardsManager.deploy({"from": deployer})

    ## TODO: Add a deposit
    ## TODO: Add rewards
    ## TODO: Ask for someone to refactor all the INITIAL_DEPOSITS here

    return contract


"""
  Extra set of fixtures for integration test with BadgerVaults
"""
@pytest.fixture
def deposit_amount():
  return 1e18

@pytest.fixture
def real_vault(token, initialized_contract, deployer, deposit_amount, user):
  v = TestVault.deploy(token, initialized_contract, {"from": deployer})

  token.approve(v, deposit_amount, {"from": user})
  v.deposit(deposit_amount, {"from": user})

  return v


## Forces reset before each test
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


