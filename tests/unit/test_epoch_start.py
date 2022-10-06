import brownie
from brownie import *

"""
  After a deployment, we're in "limbo", epoch 0
"""

## Note, because of how stuff is coded, if the system is in epoch 0 changes will be lost.
## Do not interact with the contract if we're not above epoch 0


def test_epoch_zero_to_one(user):
    rewards_contract = RewardsManager.deploy({"from": user})
    tx = history[-1]

    ## Epoch is now 1
    assert rewards_contract.currentEpoch() == 1

    onChain_epoch_start = rewards_contract.getEpochData(
        rewards_contract.currentEpoch()
    )[0]
    onChain_epoch_end = rewards_contract.getEpochData(rewards_contract.currentEpoch())[
        1
    ]

    assert onChain_epoch_start == tx.timestamp  ## New epoch starts with new TX
    assert (
        onChain_epoch_end == tx.timestamp + rewards_contract.SECONDS_PER_EPOCH()
    )  ## And ends exactly at start + SECONDS_PER_EPOCH


def test_epoch_changes_only_after_epoch_has_ended(initialized_contract, user, deployer):
    assert initialized_contract.currentEpoch() == 1

    ## Get info for epoch
    onChain_epoch_end = initialized_contract.getEpochData(
        initialized_contract.currentEpoch()
    )[1]

    ## And even if you wait (less than epoch ended), it still the current epoch
    chain.sleep(initialized_contract.SECONDS_PER_EPOCH() - 1231)
    chain.mine()

    initialized_contract.currentEpoch() == 1

    ## However, if we roll over until end of epoch, we are good to go
    sec_to_wait = onChain_epoch_end - chain.time()
    chain.sleep(sec_to_wait + 1)  ## +1 because >
    chain.mine()  ## Mine so the update happens

    assert initialized_contract.currentEpoch() == 2
