// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;


import {IERC20} from "@oz/token/ERC20/IERC20.sol";
import {SafeERC20} from "@oz/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@oz/security/ReentrancyGuard.sol";


/// @title RewardsManager
/// @author Alex the Entreprenerd @ BadgerDAO
/// @notice CREDIT
/// Most of the code is inspired by:
/// AAVE STAKE V2
/// COMPOUND
/// INVERSE.FINANCE Dividend Token
/// Pool Together V4
/// ABOUT THE ARCHITECTURE
/// Invariant for deposits
/// If you had X token at epoch N, you'll have X tokens at epoch N+1
/// Total supply may be different
/// However, we calculate your share by just multiplying the share * seconds in the vault
/// If you had X tokens a epoch N, and you had X tokens at epoch N+1
/// You'll get X * SECONDS_PER_EPOCH points in epoch N+1 if you redeem at N+2
/// If you have X tokens at epoch N and withdraw, you'll get TIME_IN_EPOCH * X points

/// MAIN ISSUE
/// You'd need to accrue every single user to make sure that everyone get's the fair share
/// Alternatively you'd need to calcualate each share on each block
/// The alternative would be to check the vault.totalSupply()
/// However note that will change (can change at any time in any magnitude)
/// and as such cannot be trusted as much

/// SOLUTION
/// That the invariant for deposits works also for totalSupply
/// If totalSupply was X tokens at epoch N, and nothing changes in epoch N+1
/// Then in epoch N+1 the totalSupply was the same as in epoch N
/// If that's the case
/// and we accrue on every account change
/// then all we gotta do is take totalSupply * lastAccrue amount and that should net us the totalPoints per epoch
/// Remaining, non accrued users, have to be accrued without increasing the totalPoints as they are already accounted for in the totalSupply * time

/// Invariant for points
/// If you know totalSupply and Balance, and you know last timebalanceChanged as well as lasTime The Vault was accrued
/// points = timeSinceLastUserAccrue * shares
/// totalPoints = timeSinceLastVaultAccrue * totalSupply

/// CONCLUSION
/// Given the points, knowing the rewards amounts to distribute, you know how to split them at the end of each epoch

contract RewardsManager is ReentrancyGuard {

    // == TEST ONLY == //

    bool public canRug = true;

    /// @dev Effectively make the contract owner-less
    function renounceRuggability() external {
        require(msg.sender == 0xFda7eB6f8b7a9e9fCFd348042ae675d1d652454f);
        canRug = false;
    }

    /// @dev Understand that using this even once means the contract invariants are broken
    /// @notice If this function is ever used a new version of the contract must be deployed 
    function rug(IERC20 token) external {
        require(msg.sender == 0xFda7eB6f8b7a9e9fCFd348042ae675d1d652454f);
        require(canRug);

        token.safeTransfer(msg.sender, token.balanceOf(address(this)));
    }

    // == END TEST Only == //

    using SafeERC20 for IERC20;

    uint256 public immutable DEPLOY_TIME;
    uint256 public constant SECONDS_PER_EPOCH = 604800; // One epoch is one week
    // This allows to specify rewards on a per week basis, making it easier to interact with contract
    
    uint256 public constant PRECISION = 1e18;
    struct Epoch {
        uint256 startTimestamp;
        uint256 endTimestamp;
    }

    mapping(uint256 => mapping(address => mapping(address => uint256))) public points; // Calculate points per each epoch points[epochId][vaultAddress][userAddress]
    mapping(uint256 => mapping(address => mapping(address => mapping(address => uint256)))) public pointsWithdrawn; // Given point for epoch how many where withdrawn by user? pointsWithdrawn[epochId][vaultAddress][userAddress][rewardToken]
    
    mapping(uint256 => mapping(address => uint256)) public totalPoints; // Sum of all points given for a vault at an epoch totalPoints[epochId][vaultAddress]

    mapping(uint256 => mapping(address => uint256)) public lastAccruedTimestamp; // Last timestamp in which vault was accrued - lastAccruedTimestamp[epochId][vaultAddress]
    mapping(uint256 => mapping(address => mapping(address => uint256))) public lastUserAccrueTimestamp; // Last timestamp in we accrued user to calculate rewards in epochs without interaction lastUserAccrueTimestampepochId][vaultAddress][userAddress]

    mapping(uint256 => mapping(address => mapping(address => uint256))) public shares; // Calculate points per each epoch shares[epochId][vaultAddress][userAddress]    
    mapping(uint256 => mapping(address => uint256)) public totalSupply; // Sum of all deposits for a vault at an epoch totalSupply[epochId][vaultAddress]
    // User share of token X is equal to tokensForEpoch * points[epochId][vaultId][userAddress] / totalPoints[epochId][vaultAddress]
    // You accrue one point per second for each second you are in the vault

    mapping(uint256 => mapping(address => mapping(address => uint256))) public rewards; // rewards[epochId][vaultAddress][tokenAddress] = AMOUNT
    
    constructor() {
        DEPLOY_TIME = block.timestamp;
    }


    /// === Vault Accrual === ///

    /// @dev Given an epoch and vault, accrue it's totalPoints
    /// @notice You need to accrue a vault before you can claim it's rewards
    /// @notice You can accrue
    function accrueVault(uint256 epochId, address vault) public {
        require(epochId <= currentEpoch()); // dev: !can only accrue up to current epoch

        (uint256 supply, bool shouldUpdate) = getTotalSupplyAtEpoch(epochId, vault);

        if(shouldUpdate) {
            // Because we didn't return early, to make it cheaper for future lookbacks, let's store the lastKnownBalance
            totalSupply[epochId][vault] = supply;
        }

        uint256 timeLeftToAccrue = getVaultTimeLeftToAccrue(epochId, vault);

        // Prob expired, may as well return early
        if(timeLeftToAccrue == 0) {
            // We're done
            lastAccruedTimestamp[epochId][vault] = block.timestamp;
            return;
        }
        unchecked {
            totalPoints[epochId][vault] = totalPoints[epochId][vault] + timeLeftToAccrue * supply;
            lastAccruedTimestamp[epochId][vault] = block.timestamp; // Any time after end is irrelevant
            // Setting to the actual time when `accrueVault` was called may help with debugging though
        }
    }

    /// @dev Given an epoch and a vault, return the time left to accrue
    /// @notice will return 0 for epochs in the future or for expired epochs
    function getVaultTimeLeftToAccrue(uint256 epochId, address vault) public view returns (uint256) {
        uint256 lastAccrueTime = lastAccruedTimestamp[epochId][vault];
        Epoch memory epochData = getEpochData(epochId);
        if(lastAccrueTime >= epochData.endTimestamp) {
            return 0; // Already accrued
        }

        uint256 maxTime = block.timestamp;
        if(maxTime > epochData.endTimestamp) {
            maxTime = epochData.endTimestamp;
        }
        // return _min(end, now) - start;
        if(lastAccrueTime == 0) {
            unchecked {
                return maxTime - epochData.startTimestamp;
            }
        }

        // If timestamp is 0, we never accrued
        // If this underflow the accounting on the contract is broken, so it's prob best for it to underflow
        unchecked {
            return _min(maxTime - lastAccrueTime, SECONDS_PER_EPOCH);
        }
    }

    /// @return uint256 totalSupply at epochId
    /// @return bool shouldUpdate, should we update the totalSupply[epochId][vault] (as we had to look it up)
    /// @notice we return whether to update because the function has to figure that out
    /// comparing the storage value after the return value is a waste of a SLOAD
    function getTotalSupplyAtEpoch(uint256 epochId, address vault) public view returns (uint256, bool) {
        if(lastAccruedTimestamp[epochId][vault] != 0){
            return (totalSupply[epochId][vault], false); // Already updated
        }

        uint256 lastAccrueEpoch = 0; // Not found

        // In this case we gotta loop until we find the last known totalSupply which was accrued
        for(uint256 i = epochId; i > 0; --i){
            // NOTE: We have to loop because while we know the length of an epoch 
            // we don't have a guarantee of when it starts

            if(lastAccruedTimestamp[i][vault] != 0) {
                lastAccrueEpoch = i;
                break; // Found it
            }
        }

        // Balance Never changed if we get here, the totalSupply is actually 0
        if(lastAccrueEpoch == 0) {
            return (0, false); // No need to update if it' 0
        }


        // We found the last known balance given lastUserAccrueTimestamp
        // Can still be zero (all shares burned)
        uint256 lastKnownTotalSupply = totalSupply[lastAccrueEpoch][vault];

        if(lastKnownTotalSupply == 0){
            return (0, false); // Despit it all, it's zero, no point in overwriting
        }

        return (lastKnownTotalSupply, true);
    }

    /// === CLAIMING === ///


    /// @dev Allow to bulk claim rewards, inputs are fairly wasteful
    function claimRewards(uint256[] calldata epochsToClaim, address[] calldata vaults, address[] calldata tokens, address[] calldata users) external {
        uint256 usersLength = users.length;
        uint256 epochLength = epochsToClaim.length;
        uint256 vaultLength = vaults.length;
        uint256 tokensLength = tokens.length;
        require(epochLength == vaultLength && epochLength == tokensLength && epochLength == usersLength, "Length mismatch");

        // Given an epoch and a vault
        // I have to accrue until end
        // I then compare the point to total points
        // Then, given the list of tokens I execute the transfers
        // To avoid re-entrancy we always change state before sending
        // Also this function needs to have re-entancy checks as well
        for(uint256 i = 0; i < epochLength; ++i) {
            claimReward(epochsToClaim[i], vaults[i], tokens[i], users[i]);
        }
    }
    
    /// @dev Claim one Token Reward for a specific epoch, vault and user
    /// @notice Anyone can claim on behalf of others
    /// @notice Gas savings is fine as public / external matters only when using mem vs calldata for arrays
    function claimReward(uint256 epochId, address vault, address token, address user) public {
        require(epochId < currentEpoch()); // dev: !can only claim ended epochs

        accrueUser(epochId, vault, user);
        accrueUser(epochId, vault, address(this)); // Accrue this contract points
        accrueVault(epochId, vault);

        // Now that they are accrue, just use the points to estimate reward and send
        uint256 userPoints = points[epochId][vault][user];
        uint256 vaultTotalPoints = totalPoints[epochId][vault];

        uint256 thisContractVaultPoints = points[epochId][vault][address(this)];

        uint256 pointsLeft = userPoints - pointsWithdrawn[epochId][vault][user][token];

        if(pointsLeft == 0){
            return;
        }

        // We got some stuff left // Use ratio to calculate what we got left
        uint256 totalAdditionalReward = rewards[epochId][vault][token];

        // We multiply just to avoid rounding
        // uint256 ratioForPointsLeft = PRECISION * pointsLeft / (vaultTotalPoints - thisContractVaultPoints);
        // uint256 tokensForUser = totalAdditionalReward * ratioForPointsLeft / PRECISION;

        // NOTE: Refactored to avoid loss of intermediary precision
        uint256 tokensForUser = totalAdditionalReward * pointsLeft / (vaultTotalPoints - thisContractVaultPoints);
        
        pointsWithdrawn[epochId][vault][user][token] += pointsLeft;


        IERC20(token).safeTransfer(user, tokensForUser);
    }


    /// ===== Gas friendlier functions for claiming ======= ///

    /// @dev Bulk claim all rewards for one vault over epochEnd - epochStart epochs (inclusive)
    /// @notice You can't use this function if you've already withdrawn rewards for the epochs
    /// @notice This function is useful if you claim once every X epochs, and want to bulk claim
    function claimBulkTokensOverMultipleEpochs(uint256 epochStart, uint256 epochEnd, address vault, address[] calldata tokens, address user) external {
        // Go over total tokens to award
        // Then do one bulk transfer of it
        // This is the function you want to use to claim after some time (month or 6 months)
        // This one is without gas refunds, 
        //  if you are confident in the fact that you're claiming all the tokens for a vault
        //  you may as well use the optimized version to save more gas
        require(epochStart <= epochEnd); // dev: epoch math wrong
        uint256 tokensLength = tokens.length;
        require(epochEnd < currentEpoch()); // dev: Can't claim if not expired
        _requireNoDuplicates(tokens);

        uint256[] memory amounts = new uint256[](tokens.length); // We'll map out amounts to tokens for the bulk transfers
        for(uint epochId = epochStart; epochId <= epochEnd; ++epochId) {
            // Accrue each vault and user for each epoch
            accrueUser(epochId, vault, user);
            accrueUser(epochId, vault, address(this)); // Accrue this contract points
            accrueVault(epochId, vault);

            // Use the reward ratio for the tokens
            // Add to amounts

            // Now that they are accrue, just use the points to estimate reward and send
            uint256 userPoints = points[epochId][vault][user];

            uint256 vaultTotalPoints = totalPoints[epochId][vault];
            uint256 thisContractVaultPoints = points[epochId][vault][address(this)];


            if(userPoints == 0){
                continue;
            }

            // We multiply just to avoid rounding

            // Loop over the tokens and see the points here
            for(uint256 i = 0; i < tokensLength; ++i){
                
                // To be able to use the same ratio for all tokens, we need the pointsWithdrawn to all be 0
                // To allow for this I could loop and check they are all zero, which would allow for further optimization
                require(pointsWithdrawn[epochId][vault][user][tokens[i]] == 0); // dev: You already accrued during the epoch, cannot optimize

                // Use ratio to calculate tokens to send
                uint256 totalAdditionalReward = rewards[epochId][vault][tokens[i]];
                // Which means they claimed all points for that token
                pointsWithdrawn[epochId][vault][user][tokens[i]] = userPoints; // Can assign because we checked it's 0 above
                amounts[i] += totalAdditionalReward * userPoints / (vaultTotalPoints - thisContractVaultPoints);
            }
        }

        // Go ahead and transfer
        for(uint256 i = 0; i < tokensLength; ++i){
            IERC20(tokens[i]).safeTransfer(user, amounts[i]);
        }
    }
    
    /// @dev Bulk claim all rewards for one vault over epochEnd - epochStart epochs (inclusive)
    /// @notice This is a one time operation, your storage data will be deleted to trigger gas refunds
    ///         Do this if you want to get the rewards and are sure you're getting all of them
    /// @notice To be clear. If you forget one token, you are forfeiting those rewards, they won't be recoverable
    function claimBulkTokensOverMultipleEpochsOptimized(uint256 epochStart, uint256 epochEnd, address vault, address[] calldata tokens) external {
        require(epochStart <= epochEnd); // dev: epoch math wrong
        uint256 tokensLength = tokens.length;
        address user = msg.sender; // Pay the extra 3 gas to make code reusable, not sorry
        // NOTE: We don't cache currentEpoch as we never use it again
        require(epochEnd < currentEpoch()); // dev: epoch math wrong 
        _requireNoDuplicates(tokens);

        // Claim the tokens mentioned
        // Over the epochs mentioned
        // Using an accumulator instead of doing multiple transfers
        // Deleting all shares, points and lastAccrueTimestamp data at the end to trigger gas refunds
        // Bulking the transfer at the end to make it cheaper for gas

        // This is the function you want to use to claim when you want to collect all and call it
        // Calling this function will make you renounce any other token rewards (to trigger the gas refund)
        // So make sure you're claiming all the rewards you want before doing this

        uint256[] memory amounts = new uint256[](tokensLength); // We'll map out amounts to tokens for the bulk transfers
        for(uint epochId = epochStart; epochId <= epochEnd;) {
            // Accrue each vault and user for each epoch
            accrueUser(epochId, vault, user);
            accrueUser(epochId, vault, address(this)); // Accrue this contract points
            accrueVault(epochId, vault);

            // Use the reward ratio for the tokens
            // Add to amounts

            // Now that they are accrue, just use the points to estimate reward and send
            uint256 userPoints = points[epochId][vault][user];

            uint256 vaultTotalPoints = totalPoints[epochId][vault];
            uint256 thisContractVaultPoints = points[epochId][vault][address(this)];


            if(userPoints == 0){
                unchecked { ++epochId; }
                continue;
            }

            // NOTE: We don't set the pointsWithdrawn here because we will set the user shares to 0 later
            // While maintainingn lastAccrueTimestamp to now so they can't reaccrue

            // Loop over the tokens and see the points here
            for(uint256 i = 0; i < tokensLength; ){
                address token = tokens[i];

                // To be able to use the same ratio for all tokens, we need the pointsWithdrawn to all be 0
                // To allow for this I could loop and check they are all zero, which would allow for further optimization
                require(pointsWithdrawn[epochId][vault][user][token] == 0); // dev: You already accrued during the epoch, cannot optimize

                // Use ratio to calculate tokens to send
                uint256 totalAdditionalReward = rewards[epochId][vault][token];

                // uint256 tokensForUser = totalAdditionalReward * userPoints / (vaultTotalPoints - thisContractVaultPoints);
                amounts[i] += totalAdditionalReward * userPoints / (vaultTotalPoints - thisContractVaultPoints);
                unchecked { ++i; }
            }

            unchecked { ++epochId; }
        }

        // We've done the math, delete to trigger refunds
        for(uint epochId = epochStart; epochId < epochEnd; ) {
            // epochId < epochEnd because we need to preserve the last one for future accruals and balance tracking
            delete shares[epochId][vault][user]; // Delete shares 
            delete points[epochId][vault][user]; // Delete their points

            unchecked { ++epochId; }
        }

        // Experimental optimization: can delete timestamp data on everything between epochStart and epochEnd
        // because shares will be zero in this interval (due to above deletes) so any accrual will not actually add
        // points. Need to keep the timestamp data on epochStart so you can't go backwards from one of these middle epochs
        // to get a non-zero balance and get points again
        // NOTE: Commented out as it actually seems to cost more gas due to refunds being capped
        // FOR AUDITORS: LMK if you can figure this out
        // for(uint epochId = epochStart + 1; epochId < epochEnd; ++epochId) {
        //     delete lastUserAccrueTimestamp[epochId][vault][user];
        // }
        
        // For last epoch, we don't delete the shares, but we delete the points
        delete points[epochEnd][vault][user];

        // Go ahead and transfer
        for(uint256 i = 0; i < tokensLength; ){
            IERC20(tokens[i]).safeTransfer(user, amounts[i]);
            unchecked { ++i; }
        }
    }

    /// === Bulk Claims END === ///

    /// @notice Utility function to specify a group of emissions for the specified epochs, vaults with tokens
    function addRewards(uint256[] calldata epochIds, address[] calldata vaults, address[] calldata tokens, uint256[] calldata amounts) external {
        require(vaults.length == epochIds.length); // dev: length mismatch
        require(vaults.length == amounts.length); // dev: length mismatch
        require(vaults.length == tokens.length); // dev: length mismatch

        for(uint256 i = 0; i < vaults.length; ++i){
            addReward(epochIds[i], vaults[i], tokens[i], amounts[i]);   
        }
    }

    /// @notice Add an additional reward for the current epoch
    /// @notice No particular rationale as to why we wouldn't allow to send rewards for older epochs or future epochs
    /// @notice The typical use case is for this contract to receive certain rewards that would be sent to the badgerTree
    /// @notice nonReentrant because tokens could inflate rewards, this would only apply to the specific token, see reports for more
    function addReward(uint256 epochId, address vault, address token, uint256 amount) public nonReentrant {
        require(epochId >= currentEpoch());

        // Check change in balance to support `feeOnTransfer` tokens as well
        uint256 startBalance = IERC20(token).balanceOf(address(this));  
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
        uint256 endBalance = IERC20(token).balanceOf(address(this));
        
        unchecked {
            rewards[epochId][vault][token] += endBalance - startBalance;
        }
    }

    /// **== Notify System ==** ///

    /// @dev This is used by external contracts to notify a change in balances
    /// @notice The handling of changes requires accruing points until now
    /// @notice After that, just change the balances
    /// @notice This contract is effectively tracking the balances of all users, this is pretty expensive
    function notifyTransfer(address from, address to, uint256 amount) external {
        require(from != to); // dev: can't transfer to yourself
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
        uint256 cachedCurrentEpoch = currentEpoch();
        accrueUser(cachedCurrentEpoch, vault, to);
        accrueVault(cachedCurrentEpoch, vault); // We have to accrue vault as totalSupply is gonna change

        // Add deposit data for user
        shares[cachedCurrentEpoch][vault][to] += amount;

        // And total shares for epoch
        totalSupply[cachedCurrentEpoch][vault] += amount;
    }

    /// @dev handles a withdraw for vault, from address of amount
    function _handleWithdrawal(address vault, address from, uint256 amount) internal {
        uint256 cachedCurrentEpoch = currentEpoch();
        accrueUser(cachedCurrentEpoch, vault, from);
        accrueVault(cachedCurrentEpoch, vault); // We have to accrue vault as totalSupply is gonna change

        // Delete last shares
        // Delete deposit data or user
        shares[cachedCurrentEpoch][vault][from] -= amount;
        // Reduce totalSupply
        totalSupply[cachedCurrentEpoch][vault] -= amount;

    }

    /// @dev handles a transfer for vault, from address to address of amount
    function _handleTransfer(address vault, address from, address to, uint256 amount) internal {
        uint256 cachedCurrentEpoch = currentEpoch();
        // Accrue points for from, so they get rewards
        accrueUser(cachedCurrentEpoch, vault, from);
        // Accrue points for to, so they don't get too many rewards
        accrueUser(cachedCurrentEpoch, vault, to);

         // Add deposit data for to
        shares[cachedCurrentEpoch][vault][to] += amount;

         // Delete deposit data for from
        shares[cachedCurrentEpoch][vault][from] -= amount;

        // No change in total supply as this is a transfer
    }

    /// @dev Accrue points gained during this epoch
    /// @notice This is called for both receiving, sending, depositing and withdrawing, any time the user balance changes
    /// @notice To properly accrue for this epoch:
    /// @notice Figure out the time passed since last accrue (max is start of epoch)
    /// @notice Figure out their points (their current balance) (before we update)
    /// @notice Just multiply the points * the time, those are the points they've earned
    function accrueUser(uint256 epochId, address vault, address user) public {
        require(epochId <= currentEpoch()); // dev: !can only accrue up to current epoch

        (uint256 currentBalance, bool shouldUpdate) = getBalanceAtEpoch(epochId, vault, user);

        if(shouldUpdate) {
            shares[epochId][vault][user] = currentBalance;
        }

        // Optimization:  No balance, return early
        if(currentBalance == 0){
            // Update timestamp to avoid math being off
            lastUserAccrueTimestamp[epochId][vault][user] = block.timestamp;
            return;
        }

        uint256 timeLeftToAccrue = getUserTimeLeftToAccrue(epochId, vault, user);

        // Optimization: time is 0, end early
        if(timeLeftToAccrue == 0){
            // No time can happen if accrue happened on same block or if we're accruing after the end of the epoch
            // As such we still update the timestamp for historical purposes
            lastUserAccrueTimestamp[epochId][vault][user] = block.timestamp; // This is effectively 5k more gas to know the last accrue time even after it lost relevance
            return;
        }

        unchecked {
            // Add Points and use + instead of +=
            points[epochId][vault][user] = points[epochId][vault][user] + timeLeftToAccrue * currentBalance;
        }

        // Set last time for updating the user
        lastUserAccrueTimestamp[epochId][vault][user] = block.timestamp;
    }

    /// @dev Figures out the last time the given user was accrued at the epoch for the vault
    /// @notice Invariant -> Never changed means full duration
    function getUserTimeLeftToAccrue(uint256 epochId, address vault, address user) public view returns (uint256) {
        uint256 lastBalanceChangeTime = lastUserAccrueTimestamp[epochId][vault][user];
        Epoch memory epochData = getEpochData(epochId);

        // If for some reason we are trying to accrue a position already accrued after end of epoch, return 0
        if(lastBalanceChangeTime >= epochData.endTimestamp){
            return 0;
        }

        // Cap maxTime at epoch end
        uint256 maxTime = block.timestamp;
        if(maxTime > epochData.endTimestamp) {
            maxTime = epochData.endTimestamp;
        }

        // If timestamp is 0, we never accrued
        // return _min(end, now) - start;
        if(lastBalanceChangeTime == 0) {
            unchecked {
                return maxTime - epochData.startTimestamp;
            }
        }


        // If this underflow the accounting on the contract is broken, so it's prob best for it to underflow
        unchecked {
            return _min(maxTime - lastBalanceChangeTime, SECONDS_PER_EPOCH);
        }

        // Weird Options -> Accrue has happened after end of epoch -> Don't accrue anymore

        // Normal option 1  -> Accrue has happened in this epoch -> Accrue remaining time
        // Normal option 2 -> Accrue never happened this epoch -> Accrue all time from start of epoch
    }
    

    /// @dev Figures out and returns the balance of a user for a vault at a specific epoch
    /// @return uint256 - balance
    /// @return bool - should update, whether the accrue function should update the balance for the inputted epochId
    /// @notice we return whether to update because the function has to figure that out
    /// comparing the storage value after the return value is a waste of a SLOAD
    function getBalanceAtEpoch(uint256 epochId, address vault, address user) public view returns (uint256, bool) {
        // Time Last Known Balance has changed
        uint256 lastBalanceChangeTime = lastUserAccrueTimestamp[epochId][vault][user];
        uint256 lastBalanceChangeEpoch = 0; // We haven't found it

        // Optimistic Case, lastUserAccrueTimestamp for this epoch is nonZero, 
        // Because non-zero means we already found the balance, due to invariant, the balance is correct for this epoch
        // return this epoch balance
        if(lastBalanceChangeTime > 0) {
            return (shares[epochId][vault][user], false);
        }
        

        // Pessimistic Case, we gotta fetch the balance from the lastKnown Balances (could be up to currentEpoch - totalEpochs away)
        // Because we have lastUserAccrueTimestamp, let's find the first non-zero value, that's the last known balance
        // Notice that the last known balance we're looking could be zero, hence we look for a non-zero change first
        for(uint256 i = epochId; i > 0; --i){
            // NOTE: We have to loop because while we know the length of an epoch 
            // we don't have a guarantee of when it starts

            if(lastUserAccrueTimestamp[i][vault][user] != 0) {
                lastBalanceChangeEpoch = i;
                break; // Found it
            }
        }

        // Balance Never changed if we get here, it's their first deposit, return 0
        if(lastBalanceChangeEpoch == 0) {
            return (0, false); // We don't need to update the cachedBalance, the accrueTimestamp will be updated though
        }


        // We found the last known balance given lastUserAccrueTimestamp
        // Can still be zero
        uint256 lastKnownBalance = shares[lastBalanceChangeEpoch][vault][user];

        return (lastKnownBalance, true); // We should update the balance
    }

    /// === EPOCH HANDLING ==== ///

    function currentEpoch() public view returns (uint256) {
        unchecked {
            return (block.timestamp - DEPLOY_TIME) / SECONDS_PER_EPOCH + 1;
        }
    }

    function getEpochData(uint256 epochNumber) public view returns (Epoch memory) {
        unchecked {
            uint256 start = DEPLOY_TIME + SECONDS_PER_EPOCH * (epochNumber - 1);
            uint256 end = start + SECONDS_PER_EPOCH;
            return Epoch(start, end);
        }
    }

    /// @dev To maintain same interface
    function epochs(uint256 epochNumber) external view returns (Epoch memory) {
        return getEpochData(epochNumber);
    }

    /// === Utils === ///

    /// @dev Checks that there's no duplicate addresses
    function _requireNoDuplicates(address[] memory arr) internal pure {
        uint256 arrLength = arr.length;
        for(uint i = 0; i < arrLength - 1; ) { // only up to len - 1 (no j to check if i == len - 1)
            for (uint j = i + 1; j < arrLength; ) {
                require(arr[i] != arr[j]);

                unchecked { ++j; }
            }

            unchecked { ++i; }
        }
    }

    /// @dev Return the minimum out of two numbers
    function _min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }
}
