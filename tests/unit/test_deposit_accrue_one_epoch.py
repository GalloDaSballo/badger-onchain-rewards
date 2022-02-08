import brownie
from brownie import *

AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

"""
  Checks that ratio changes allow different investment profiles
"""

def test_epoch_zero_to_one_weirdness(rewards_contract, user, fake_vault):
    epoch = 0
    ## We start in epoch 0
    assert rewards_contract.currentEpoch() == epoch

    INITIAL_DEPOSIT = 1e18

    rewards_contract.notifyTransfer(INITIAL_DEPOSIT, AddressZero, user, {"from": fake_vault})
    assert rewards_contract.shares(epoch, fake_vault, user) == INITIAL_DEPOSIT

    ## Here come's the weird part
    ## Because prev epoch was zero, we can't get the prev balance
    tx = rewards_contract.startNextEpoch({"from": user})
    new_epoch = 1

    assert rewards_contract.currentEpoch() == new_epoch
    
    assert rewards_contract.shares(new_epoch, fake_vault, user) == 0 ## Need to port them over via getBalanceAtEpoch

    ## Update the balance
    rewards_contract.getBalanceAtEpoch(new_epoch, fake_vault, user)

    ## For this epoch it won't be there (as we don't look back to epoch 0)
    assert rewards_contract.shares(new_epoch, fake_vault, user) == 0



def test_epoch_changes_balances_are_preserved(initialized_contract, user, fake_vault):
    epoch = 1
    ## We start in epoch 0
    assert initialized_contract.currentEpoch() == epoch

    INITIAL_DEPOSIT = 1e18

    initialized_contract.notifyTransfer(INITIAL_DEPOSIT, AddressZero, user, {"from": fake_vault})
    
    assert initialized_contract.shares(epoch, fake_vault, user) == INITIAL_DEPOSIT
    initialized_contract.getBalanceAtEpoch(epoch, fake_vault, user) ## Updates internal not actually needed
    assert initialized_contract.shares(epoch, fake_vault, user) == INITIAL_DEPOSIT


    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    ## Because prev epoch was zero, we can't get the prev balance
    tx = initialized_contract.startNextEpoch({"from": user})
    new_epoch = 2

    assert initialized_contract.currentEpoch() == new_epoch
    
    ## Update the balance
    initialized_contract.getBalanceAtEpoch(new_epoch, fake_vault, user)

    ## For this epoch it won't be there (as we don't look back to epoch 0)
    assert initialized_contract.shares(new_epoch, fake_vault, user) == INITIAL_DEPOSIT ## Invariant is maintained

    ## Do it again to proove it's not a fluke
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    initialized_contract.startNextEpoch({"from": user})
    new_epoch = 3

    assert initialized_contract.currentEpoch() == new_epoch
    
    ## Update the balance
    initialized_contract.getBalanceAtEpoch(new_epoch, fake_vault, user)

    ## For this epoch it won't be there (as we don't look back to epoch 0)
    assert initialized_contract.shares(new_epoch, fake_vault, user) == INITIAL_DEPOSIT ## Invariant is maintained




def temp(
    strategy, sett, governance, want, deployer, locker
):
    rando = accounts[6]

    sett.setMin(5000, {"from": governance})  ## 50%

    startingBalance = want.balanceOf(deployer)
    want.approve(sett, MaxUint256, {"from": deployer})
    sett.deposit(startingBalance, {"from": deployer})

    sett.earn({"from": governance})

    ## Assert that 50% is invested and 50% is not
    assert want.balanceOf(sett) == startingBalance / 2  ## 50% is deposited in the vault
    assert (
        locker.lockedBalanceOf(strategy) >= startingBalance / 2
    )  ## 50% is locked (due to rounding between cvx and bcvx we use >=)
