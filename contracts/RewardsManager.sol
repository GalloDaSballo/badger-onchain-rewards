// SPDX-License-Identifier: MIT
pragma solidity ^0.8.9;


import {IERC20} from "@oz/token/ERC20/IERC20.sol";
import {SafeERC20} from "@oz/token/ERC20/utils/SafeERC20.sol";

contract RewardsManager {
    using SafeERC20 for IERC20;

    /// TODO TODO:
    /// 3 Functions to get right
    /// startNextEpoch
    /// accrueUser
    /// claimRewards
    // Fix the Vault Accrual
    // Vault should accrue with total supply, not points.


    // TODO

    // Gotta figure out the scenarios and go through them rationally

    uint256 private constant SECONDS_PER_EPOCH = 604800; // One epoch is one week
    address public BADGER = 0x3472A5A71965499acd81997a54BBA8D852C6E53d;
    // This allows to specify rewards on a per week basis, making it easier to interact with contract
    

    uint256 private constant MAX_BPS = 10_000;
    
    mapping(uint256 => Epoch) public epochs; // Epoch data for each epoch epochs[epochId]
    // id is implicit in the list
    struct Epoch {
        uint256 startTimestamp;
        uint256 endTimestamp;
    }
    uint256 public currentEpoch = 1; // NOTE: 0 has the meaning of either uninitialized or set to null

    mapping(uint256 => mapping(address => uint256)) public badgerEmissionPerEpochPerVault; // Epoch data for each epoch badgerEmissionPerEpochPerVault[epochId][vaultAddress]
    

    mapping(uint256 => mapping(address => mapping(address => uint256))) public points; // Calculate points per each epoch points[epochId][vaultAddress][userAddress]
    mapping(uint256 => mapping(address => mapping(address => mapping(address => uint256)))) public pointsWithdrawn; // Given point for epoch how many where withdrawn by user? pointsWithdrawn[epochId][vaultAddress][userAddress][rewardToken]
    
    mapping(uint256 => mapping(address => uint256)) public totalPoints; // Sum of all points given for a vault at an epoch totalPoints[epochId][vaultAddress]

    mapping(uint256 => mapping(address => uint256)) lastAccruedTimestamp; // Last timestamp in which vault was accrued - lastAccruedTimestamp[epochId][vaultAddress]
    mapping(uint256 => mapping(address => mapping(address => uint256))) lastUserAccrueTimestamp; // Last timestamp in we accrued user to calculate rewards in epochs without interaction lastUserAccrueTimestampepochId][vaultAddress][userAddress]
    mapping(address => uint256) lastVaultDeposit; // Last Epoch in which any user deposited in the vault, used to know if vault needs to be brought to new epoch
    // Or just have the check and skip the op if need be

    mapping(uint256 => mapping(address => mapping(address => uint256))) public shares; // Calculate points per each epoch shares[epochId][vaultAddress][userAddress]    
    mapping(uint256 => mapping(address => uint256)) public totalSupply; // Sum of all deposits for a vault at an epoch totalSupply[epochId][vaultAddress]
    // User share of token X is equal to tokensForEpoch * points[epochId][vaultId][userAddress] / totalPoints[epochId][vaultAddress]
    // You accrue one point per second for each second you are in the vault


    // NOTE ABOUT ARCHITECTURE
    // This contract is fundamentally tracking the balances on all registeredVaults for all users
    // This basically means we have duplicated logic, we could do without by simply adding this to the vault
    // Adding it may also allow to solve Yield Theft issues as we're accounting for value * time as a way to reward more fairly
    // NOTE: Pool Together has 100% gone through these ideas, we have 4 public audits to read through
    // CREDIT: Most of the code is inspired by:
    // AAVE STAKE V2
    // COMPOUND
    // INVERSE.FINANCE Dividend Token
    // Pool Together V4


    // Invariant for deposits
    // If you had X token at epoch N, you'll have X tokens at epoch N+1
    // Total supply may be different
    // However, we calculate your share by just multiplying the share * seconds in the vault
    // If you had X tokens a epoch N, and you had X tokens at epoch N+1
    // You'll get N + 1 * SECONDS_PER_EPOCH points in epoch N+1 if you redeem at N+2
    // If you have X tokens at epoch N and withdraw, you'll get TIME_IN_EPOCH * X points


    // MAIN ISSUE
    // You'd need to accrue every single user to make sure that everyone get's the fair share
    // Alternatively you'd need to calcualate each share on each block
    // The alternative would be to check the vault.totalSupply()
    // However note that will change (can change at any time in any magnitude)
    // and as such cannot be trusted as much
    // NOTE: That the invariant for deposits works also for totalSupply


    // If totalSupply was X tokens at epoch N, and nothing changes in epoch N+1
    // Then in epoch N+1 the totalSupply was the same as in epoch N
    // If that's the case
    // and we accrue on every account change
    // then all we gotta do is take totalSupply * lastAccrue amount and that should net us the totalPoints per epoch
    // Remaining, non accrued users, have to be accrued without increasing the totalPoints as they are already accounted for in the totalSupply * time
    

    // If the invariant that shares at x are the same as shares at n+1
    // And we accrue users on any shares changes
    // Then we do not need

    mapping(uint256 => mapping(address => mapping(address => uint256))) additionalReward; // additionalReward[epochId][vaultAddress][tokenAddress] = AMOUNT

    /// @dev Sets the new epoch
    /// @notice Accruing is not necessary, it's just a convenience for end users
    function startNextEpoch() external {
        require(block.timestamp > epochs[currentEpoch].endTimestamp); // dev: !ended
        uint256 newEpochId = ++currentEpoch;

        epochs[newEpochId] = Epoch(
            block.timestamp,
            block.timestamp + SECONDS_PER_EPOCH
        );
    }

    /// @dev Given an epoch and vault, accrue it's totalPoints
    /// @notice You need to accrue a vault before you can claim it's rewards
    /// @notice You can accrue
    function accrueVault(uint256 epochId, address vault) public returns (uint256) {
        uint256 timeLeftToAccrue = getVaultTimeLeftToAccrue(epochId, vault);

        // Prob expired, may as well return early
        if(timeLeftToAccrue == 0) {
            // We're done
            return 0; 
        }

        uint256 totalSupply = getTotalSupplyAtEpoch(epochId, vault);

        totalPoints[epochId][vault] += timeLeftToAccrue * totalSupply;
        lastAccruedTimestamp[epochId][vault] = block.timestamp; // Any time after end is irrelevant
        // Setting to the actual time when `accrueVault` was called may help with debugging though
    }

    function getVaultTimeLeftToAccrue(uint256 epochId, address vault) public returns (uint256) {
        uint256 lastAccrueTime = lastAccruedTimestamp[epochId][vault];
        Epoch memory epochData = epochs[epochId];
        if(lastAccrueTime >= epochData.endTimestamp) {
            return 0; // Already accrued
        }

        uint256 maxTime = block.timestamp;
        if(maxTime > epochData.endTimestamp) {
            maxTime = epochData.endTimestamp;
        }
        // return min(end, now) - start;
        if(lastAccrueTime == 0) {
            return maxTime - epochData.startTimestamp;
        }

        // If timestamp is 0, we never accrued
        // If this underflow the accounting on the contract is broken, so it's prob best for it to underflow
        return lastAccrueTime - epochData.startTimestamp;
    }

    
    function getTotalSupplyAtEpoch(uint256 epochId, address vault) public returns (uint256) {
        if(lastAccruedTimestamp[epochId][vault] != 0){
            return totalSupply[epochId][vault]; //We can trust the totalSupply value
        }

        uint256 lastAccrueEpoch = 0; // Not found

        // In this case we gotta loop until we find the last known totalSupply which was accrued
        for(uint256 i = epochId; i > 0; i--){
            // NOTE: We have to loop because while we know the length of an epoch 
            // we don't have a guarantee of when it starts

            if(lastAccruedTimestamp[i][vault] != 0) {
                lastAccrueEpoch = i;
                break; // Found it
            }
        }

        // Balance Never changed if we get here, the totalSupply is actually 0
        if(lastAccrueEpoch == 0) {
            return 0;
        }


        // We found the last known balance given lastUserAccrueTimestamp
        // Can still be zero (all shares burned)
        uint256 lastKnownTotalSupply = totalSupply[lastAccrueEpoch][vault];

        // Because we didn't return early, to make it cheaper for future lookbacks, let's store the lastKnownBalance
        totalSupply[epochId][vault] = lastKnownTotalSupply;

        return lastKnownTotalSupply;
    }

    // TODO: Generalize the badger emission to any token
    // Honestly badger can be generalized to the any token structure, avoiding the need for extra mappings
    // TODO: Make tonkes `address[][] calldata tokens` so that you can accrue and claim more than one set of tokens per vault per epoch
    function claimRewards(uint256[] calldata epochsToClaim, address[] calldata vaults, address[] calldata tokens) external {
        uint256 epochLength = epochsToClaim.length;
        uint256 vaultLength = vaults.length;
        uint256 tokensLength = tokens.length;
        require(epochLength == vaultLength && epochLength == tokensLength, "Length mismatch");

        // Given an epoch and a vault
        // I have to accrue until end
        // I then compare the point to total points
        // Then, given the list of tokens I execute the transfers
        // To avoid re-entrancy we always change state before sending
        // Also this function needs to have re-entancy checks as well
        for(uint256 i = 0; i < epochLength; i++) {
            claimReward(epochsToClaim[i], vaults[i], tokens[i]);
        }
    }

    // NOTE: Gas savings is fine as public / external matters only when using mem vs calldata for arrays
    // TODO: Actually check if it makes sense and it's correct
    function claimReward(uint256 epochId, address vault, address token) public {
        require(epochId < currentEpoch); // dev: !can only claim ended epochs

        // TODO: Accrue the user in the past until the end of the epoch
        accrueUser(epochId, vault, msg.sender);
        accrueVault(epochId, vault);

        // Now that they are accrue, just use the points to estimate reward and send
        uint256 userPoints = points[epochId][vault][msg.sender];
        uint256 vaultTotalPoints = totalPoints[epochId][vault];

        uint256 pointsLeft = userPoints - pointsWithdrawn[epochId][vault][msg.sender][token];

        if(pointsLeft == 0){
            return;
        }

        // We got some stuff left // Use ratio to calculate what we got left
        uint256 totalAdditionalReward = additionalReward[epochId][vault][token];

        // We multiply just to avoid rounding
        uint256 ratioForPointsLeft = MAX_BPS * pointsLeft / vaultTotalPoints;
        uint256 tokensForUser = totalAdditionalReward * ratioForPointsLeft / MAX_BPS;


        pointsWithdrawn[epochId][vault][msg.sender][token] += pointsLeft;


        token.safeTransfer(msg.sender, tokensForUser);
    }


    /// @dev add new badger emission for the specific epoch
    /// @notice you can add rewards for this epoch or future epochs
    /// @notice we don't allow retroactivelly setting the main reward 
    /// @notice as that could cause certain users (that already claimed) to loose the new rewards
    /// @notice you can only add more, no turning back once you sent these
    function setEmission(uint256 epochId, address vault, uint256 amount) public {
        require(epochId >= currentEpoch); // dev: already ended

        // NOTE: Instead of requiring emission, we just increase the amount, it gives more flexibility
        // Basically you can only get rugged in the positive, cannot go below the amount provided

        // Check change in balance just to be sure
        uint256 startBalance = IERC20(BADGER).balanceOf(address(this));  
        IERC20(BADGER).safeTransferFrom(msg.sender, address(this), amount);
        uint256 endBalance = IERC20(BADGER).balanceOf(address(this));
 
        badgerEmissionPerEpochPerVault[epochId][vault] += endBalance - startBalance;
    }

    /// @dev Utility function to specify a group of emissions for the specified epoch
    /// @notice This is how you'd typically set up emissions for a specific epoch
    function setEmissions(uint256 epochId, address[] calldata vaults, uint256[] calldata badgerAmounts) external {
        require(vaults.length == badgerAmounts.length); // dev: length mistamtch

        for(uint256 i = 0; i < vaults.length; i++){
            setEmission(epochId, vaults[i], badgerAmounts[i]);   
        }
    }

    /// @dev Add an additional reward for the current epoch
    /// @notice No particular rationale as to why we wouldn't allow to send rewards for older epochs or future epochs
    /// @notice The typical use case is for this contract to receive certain rewards that would be sent to the badgerTree
    function sendExtraReward(address vault, address extraReward, uint256 amount) external {
        // NOTE: This function can be called by anyone, effectively allowing for bribes / airdrops to vaults

        // Check change in balance to support `feeOnTransfer` tokens as well
        uint256 startBalance = IERC20(extraReward).balanceOf(address(this));  
        IERC20(extraReward).safeTransferFrom(msg.sender, address(this), amount);
        uint256 endBalance = IERC20(extraReward).balanceOf(address(this));

        additionalReward[currentEpoch][vault][extraReward] += endBalance - startBalance;
    }
    // NOTE: If you wanna do multiple rewards, just do a helper contract to call `sendExtraReward` multiple times



    // Total Points per epoch = Total Deposits * Total Points per Second * Seconds in Epoch

    /// **== Notify System ==** ///

    /// @dev This is used by external contracts to notify a change in balances
    /// @notice The handling of changes requires accruing points until now
    /// @notice After that, just change the balances
    /// @notice This contract is effectively tracking the balances of all users, this is pretty expensive
    function notifyTransfer(uint256 amount, address from, address to) external {
        // NOTE: Anybody can call this because it's indexed by msg.sender
        address vault = msg.sender; // Only the vault can change these

        if (from == address(0)) {
            _handleDeposit(vault, to, amount);
        } else if (to == address(0)) {
            _handleWithdrawal(vault, from, amount);
        } else {
            _handleTransfer(vault, from, to, amount);
        }
    }

    /// @dev handles a deposit for vault, to address of amount
    function _handleDeposit(address vault, address to, uint256 amount) internal {
        accrueUser(currentEpoch, vault, to);
        accrueVault(currentEpoch, vault); // We have to accrue vault as totalSupply is gonna change

        // Add deposit data for user
        shares[currentEpoch][vault][to] += amount;

        // And total shares for epoch
        totalSupply[currentEpoch][vault] += amount;
    }

    /// @dev handles a withdraw for vault, from address of amount
    function _handleWithdrawal(address vault, address from, uint256 amount) internal {
        accrueUser(currentEpoch, vault, from);
        accrueVault(currentEpoch, vault); // We have to accrue vault as totalSupply is gonna change

        // Delete last shares
        // Delete deposit data or user
        shares[currentEpoch][vault][from] -= amount;
        // Reduce totalSupply
        totalSupply[currentEpoch][vault] -= amount;

    }

    /// @dev handles a transfer for vault, from address to address of amount
    function _handleTransfer(address vault, address from, address to, uint256 amount) internal {
        // Accrue points for from, so they get rewards
        accrueUser(currentEpoch, vault, from);
        // Accrue points for to, so they don't get too many rewards
        accrueUser(currentEpoch, vault, to);

         // Add deposit data for to
        shares[currentEpoch][vault][to] += amount;

         // Delete deposit data for from
        shares[currentEpoch][vault][from] -= amount;

        // No change in total supply as this is a transfer
    }

    /// @dev Accrue points gained during this epoch
    /// @notice This is called for both receiving, sending, depositing and withdrawing, any time the user balance changes
    /// @notice To properly accrue for this epoch:
    /// @notice Figure out the time passed since last accrue (max is start of epoch)
    /// @notice Figure out their points (their current balance) (before we update)
    /// @notice Just multiply the points * the time, those are the points they've earned
    function accrueUser(uint256 epoch, address vault, address user) public {
        uint256 currentBalance = getBalanceAtEpoch(epoch, vault, user);

        // Optimization:  No balance, return early
        if(currentBalance == 0){
            // Update timestamp to avoid math being off
            lastUserAccrueTimestamp[epoch][vault][user] = block.timestamp;
            return;
        }

        uint256 timeInEpochSinceLastAccrue = getUserTimeLeftToAccrue(epoch, vault, user);

        // Optimization: time is 0, end early
        if(timeInEpochSinceLastAccrue == 0){
            // No time can happen if accrue happened on same block or if we're accruing after the end of the epoch
            // As such we still update the timestamp for historical purposes
            lastUserAccrueTimestamp[epoch][vault][user] = block.timestamp; // This is effectively 5k more gas to know the last accrue time even after it lost relevance
            return;
        }

        // Run the math and update the system
        uint256 newPoints = currentBalance * timeInEpochSinceLastAccrue;
        
        // Track user rewards
        points[epoch][vault][user] += newPoints;

        // Set last time for updating the user
        lastUserAccrueTimestamp[epoch][vault][user] = block.timestamp;
    }

    // @dev Figures out the last time the given user was accrued at the epoch for the vault
    // @notice Invanriant -> Never changed means full duration
    function getUserTimeLeftToAccrue(uint256 epochId, address vault, address user) public returns (uint256) {
        uint256 lastBalanceChangeTime = lastUserAccrueTimestamp[epochId][vault][user];
        Epoch memory epochData = epochs[epochId];

        // If for some reason we are trying to accrue a position already accrued after end of epoch, return 0
        if(lastBalanceChangeTime >= epochData.endTimestamp){
            return 0;
        }

        // Becase we could be in a time where a new epoch hasn't started, we need this check
        uint256 maxTime = block.timestamp;
        if(maxTime > epochData.endTimestamp) {
            maxTime = epochData.endTimestamp;
        }

        // If timestamp is 0, we never accrued
        // return min(end, now) - start;
        if(lastBalanceChangeTime == 0) {
            return maxTime - epochData.startTimestamp;
        }


        // If this underflow the accounting on the contract is broken, so it's prob best for it to underflow
        return lastBalanceChangeTime - epochData.startTimestamp;

        // Weird Options -> Accrue has happened after end of epoch -> Don't accrue anymore

        // Normal option 1  -> Accrue has happened in this epoch -> Accrue remaining time
        // Normal option 2 -> Accrue never happened this epoch -> Accrue all time from start of epoch
    }

    function getBalanceAtEpoch(uint256 epochId, address vault, address user) public returns (uint256) {
        uint256 cachedCurrentEpoch = epochId; // Cache storage var to mem

        // Time Last Known Balance has changed
        uint256 lastBalanceChangeTime = lastUserAccrueTimestamp[epochId][vault][user];
        uint256 lastBalanceChangeEpoch = 0; // We haven't found it

        // Optimistic Case, lastUserAccrueTimestamp for this epoch is nonZero, 
        // Because non-zero means we already found the balance, due to invariant, the balance is correct for this epoch
        // return this epoch balance
        if(lastBalanceChangeTime > 0) {
            return shares[epochId][vault][user];
        }
        

        // Pessimistic Case, we gotta fetch the balance from the lastKnown Balances (could be up to currentEpoch - totalEpochs away)
        // Because we have lastUserAccrueTimestamp, let's find the first non-zero value, that's the last known balance
        // Notice that the last known balance we're looking could be zero, hence we look for a non-zero change first
        for(uint256 i = epochId; i > 0; i--){
            // NOTE: We have to loop because while we know the length of an epoch 
            // we don't have a guarantee of when it starts

            if(lastUserAccrueTimestamp[i][vault][user] != 0) {
                lastBalanceChangeEpoch = i;
                break; // Found it
            }
        }

        // Balance Never changed if we get here, it's their first deposit, return 0
        if(lastBalanceChangeEpoch == 0) {
            return 0;
        }


        // We found the last known balance given lastUserAccrueTimestamp
        // Can still be zero
        uint256 lastKnownBalance = shares[lastBalanceChangeEpoch][vault][user];

        // Because we didn't return early, to make it cheaper for future lookbacks, let's store the lastKnownBalance
        shares[epochId][vault][user] = lastKnownBalance;

        return lastKnownBalance;

        // Index of epochs should be fairly easy to get as long as we force each epoch to properly start at correct time and end at correct time
        // That's because it will be equal to
        // last_epoch_count = (START + lastUserAccrueTimestamp) / epoch_length
        // This assumes each epoch starts right after the previous one ends, which is currently not enforced
        // This may end up saving gas, so we may end up doing it

        // However, for now, let's just do a basic search from current epoch to first epoch to find the last deposit

        // If they never interacted, their balance will be 0
        // We need to make sure that's the case
        // We may need to track both the epoch and the timestamp to avoid this
        // Alternartively, given timestamp we can always figure out epoch
        // Once we figure out epoch we can get value
        // Value can be 0, at which point we return 0 as that's the correct balance

        // This follows Invariant: If I had X amount of tokens at epoch N, and nothing changed, then I must have X tokens at epoch N+1
    }


    // YOU DO NOT NEED TO ACCRUE OLD EPOCHS UNTIL YOU REDEEM
    // The reason is: They are not changing, the points that have changed have already and the points that are not changed are
    // just going to be deposit * time_spent as per the invariant

}