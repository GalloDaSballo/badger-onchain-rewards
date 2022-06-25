import brownie
from brownie import *

AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))

"""
  Tests for `getUserNextEpochInfo` and `getVaultNextEpochInfo`
"""


"""
  Unit tests
    -> Any change this epoch -> Value from storage
    -> No change this epoch -> Value from input
    -> Withdraw all -> Value is 0 even if input is not
"""

def test_getUserNextEpochInfo_uses_timestamp_for_data(initialized_contract, user, fake_vault):
  """
    This test shows that the `lastUserAccrueTimestamp` is the logic for the `getUserNextEpochInfo`
  """
  epoch = 1
  ## We start in epoch 1
  assert initialized_contract.currentEpoch() == epoch

  ## Minor waste of time to ensure total time spent in epoch is less than 100%
  chain.sleep(15)
  chain.mine()

  INITIAL_DEPOSIT = 1e18

  OBVIOUSLY_WRONG_DEPOSIT_VALUE = 1337

  initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})
  
  assert initialized_contract.shares(epoch, fake_vault, user) == INITIAL_DEPOSIT
  assert initialized_contract.getBalanceAtEpoch(epoch, fake_vault, user)[0] == INITIAL_DEPOSIT

  ## Let's go over multiple epochs
  chain.sleep(initialized_contract.SECONDS_PER_EPOCH() * 3 + 3)
  chain.mine()

  assert initialized_contract.lastUserAccrueTimestamp(epoch, fake_vault, user) > 0

  ## Epoch 1 ##

  """
    struct UserInfo {
      uint256 balance;
      uint256 timeLeftToAccrue;
      uint256 userEpochTotalPoints; 
      uint256 pointsInStorage;
    }
  """

  ## Because we've had an accrual, balance is read from storage
  result = initialized_contract.getUserNextEpochInfo(epoch, fake_vault, user, OBVIOUSLY_WRONG_DEPOSIT_VALUE)

  ## Check that balance is correct
  assert result[0] == INITIAL_DEPOSIT

  ## Redundantly check again against known valid function
  assert result[0] == initialized_contract.getBalanceAtEpoch(epoch, fake_vault, user)[0]

  ## Because we've had an accrual, all other values are also read from storage (no skip optimization)
  ## Time to accrue will be less than 1 epoch
  assert result[1] < initialized_contract.SECONDS_PER_EPOCH()
  ## Epoch points is greater than the ones we have in storage
  assert result[2] > initialized_contract.points(epoch, fake_vault, user) 
  ## And the pointsInStorage match
  assert result[3] == initialized_contract.points(epoch, fake_vault, user) 

  ## Epoch 2 ##

  ## Because we've had an accrual, balance is read from storage
  second_result = initialized_contract.getUserNextEpochInfo(epoch + 1, fake_vault, user, OBVIOUSLY_WRONG_DEPOSIT_VALUE)

  ## And our balance is wrong as this function is not checking for it
  assert second_result[0] == OBVIOUSLY_WRONG_DEPOSIT_VALUE

  ## We get the wrong result as well
  assert second_result[0] != initialized_contract.getBalanceAtEpoch(epoch + 1, fake_vault, user)[0]
  
  ## Because of no accrual, with wrong value we get a bunch of gibberish for points
  ## Time to accrue will be exactly one epoch
  assert second_result[1] == initialized_contract.SECONDS_PER_EPOCH()

  ## Epoch points is greater than the ones we have in storage
  assert second_result[2] > initialized_contract.points(epoch + 1, fake_vault, user) ## Cause it's zero
  ## And the pointsInStorage match
  assert second_result[3] == initialized_contract.points(epoch + 1, fake_vault, user) ## It's zero
  ## Just to confirm it's zero
  assert second_result[3] == 0

  ## This value is wrong
  second_result[2]

  ## We can prove by accruing for real
  initialized_contract.accrueUser(epoch + 1, fake_vault, user)

  ## Compare against the accrued in-storage points
  assert second_result[2] != initialized_contract.points(epoch + 1, fake_vault, user)

  ## Because OBVIOUSLY_WRONG_DEPOSIT_VALUE is very small, we should be confident that calculated points is less than the actual points
  assert second_result[2] < initialized_contract.points(epoch + 1, fake_vault, user)



  
def test_epoch_basic_comprison_to_getBalanceAtEpoch(initialized_contract, user, fake_vault):
    """
      This test proves that balances are preserved across epochs, 
      as long as you cache the prev_epoch balance and send it back on the next call
    """
    epoch = 1
    ## We start in epoch 1
    assert initialized_contract.currentEpoch() == epoch

    INITIAL_DEPOSIT = 1e18

    initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})
    
    assert initialized_contract.shares(epoch, fake_vault, user) == INITIAL_DEPOSIT
    assert initialized_contract.getBalanceAtEpoch(epoch, fake_vault, user)[0] == INITIAL_DEPOSIT

    from_storage_bal = initialized_contract.getBalanceAtEpoch(epoch, fake_vault, user)[0]

    ## Sleep as epoch needs to be over
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    ## Storage read
    assert initialized_contract.getUserNextEpochInfo(epoch, fake_vault, user, from_storage_bal)[0] == INITIAL_DEPOSIT
    
    ## Because we deposited in epoch, a wrong input value doesn't matter
    assert initialized_contract.getUserNextEpochInfo(epoch, fake_vault, user, 0)[0] == INITIAL_DEPOSIT


    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    new_epoch = 2

    assert initialized_contract.currentEpoch() >= new_epoch
  

    ## For this epoch we must pass in the correct value
    assert initialized_contract.getUserNextEpochInfo(new_epoch, fake_vault, user, from_storage_bal)[0] == initialized_contract.getBalanceAtEpoch(epoch, fake_vault, user)[0]

    ## As any random value inputted will be returned (no storage on this epoch)
    fake_value = 6969
    assert initialized_contract.getUserNextEpochInfo(new_epoch, fake_vault, user, fake_value)[0] == fake_value


    ## Do it again to proove it's not a fluke
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    new_epoch = 3

    assert initialized_contract.currentEpoch() >= new_epoch

    ## For this epoch it won't be there (as we don't look back to epoch 0)
    assert initialized_contract.getUserNextEpochInfo(new_epoch, fake_vault, user, from_storage_bal)[0] == initialized_contract.getBalanceAtEpoch(new_epoch, fake_vault, user)[0]

    ## Do a second deposit, to change balance at current epoch
    latest_epoch = initialized_contract.currentEpoch()
    initialized_contract.notifyTransfer(AddressZero, user, INITIAL_DEPOSIT, {"from": fake_vault})

    ## Wait until epoch has ended
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() + 1)
    chain.mine()

    ## Because value is from storage any random flag value is fine as prev balance
    random_value = 123123
    assert initialized_contract.getUserNextEpochInfo(latest_epoch, fake_vault, user, random_value)[0] == initialized_contract.getBalanceAtEpoch(latest_epoch, fake_vault, user)[0]

    ## Even 0
    assert initialized_contract.getUserNextEpochInfo(latest_epoch, fake_vault, user, 0)[0] == initialized_contract.getBalanceAtEpoch(latest_epoch, fake_vault, user)[0]
