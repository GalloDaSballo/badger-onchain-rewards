// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;


import {IERC20} from "@oz/token/ERC20/IERC20.sol";
import {SafeERC20} from "@oz/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@oz/security/ReentrancyGuard.sol";


/// @title RewardsManager
/// @author Alex the Entreprenerd @ BadgerDAO
/// @notice CREDIT
/// Most of the code is inspired by:
/// SNX / CVX RewardsPool
/// Aave Stake V2
/// Compound
/// Inverse.Finance Dividend Token
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
    
    using SafeERC20 for IERC20;

    uint256 public immutable DEPLOY_TIME; // NOTE: Must be `immutable`, remove `immutable` for coverage report
    uint256 public constant SECONDS_PER_EPOCH = 604800; // One epoch is one week
    // This allows to specify rewards on a per week basis, making it easier to interact with contract
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
            totalPoints[epochId][vault] += timeLeftToAccrue * supply;
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

        // Shortcut
        if(epochId == 1) {
            // If epoch is first one, and we don't have a totalSupply, then totalSupply is zero
            return (0, false);

            // This allows to do epochId - 1 below
        }

        uint256 lastAccrueEpoch = 0; // Not found

        // In this case we gotta loop until we find the last known totalSupply which was accrued
        for(uint256 i = epochId - 1; i > 0; ){
            // NOTE: We have to loop because while we know the length of an epoch 
            // we don't have a guarantee of when it starts

            if(lastAccruedTimestamp[i][vault] != 0) {
                lastAccrueEpoch = i;
                break; // Found it
            }

            unchecked {
                --i;
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

        require(usersLength == epochLength); // dev: length mismatch
        require(epochLength == vaultLength); // dev: length mismatch
        require(vaultLength == tokensLength); // dev: length mismatch

        // Given an epoch and a vault
        // I have to accrue until end
        // I then compare the point to total points
        // Then, given the list of tokens I execute the transfers
        // To avoid re-entrancy we always change state before sending
        // Also this function needs to have re-entancy checks as well
        for(uint256 i; i < epochLength; ) {
            claimReward(epochsToClaim[i], vaults[i], tokens[i], users[i]);

            unchecked {
                ++i;
            }
        }
    }
    
    /// @dev Claim one Token Reward for a specific epoch, vault and user
    /// @notice Reference version of the function, fully onChain, fully in storage
    ///     This function is as expensive as it gets
    /// @notice Anyone can claim on behalf of others
    /// @notice Gas savings is fine as public / external matters only when using mem vs calldata for arrays
    function claimRewardReference(uint256 epochId, address vault, address token, address user) public {
        require(epochId < currentEpoch()); // dev: !can only claim ended epochs

        accrueUser(epochId, vault, user);
        accrueUser(epochId, vault, address(this)); // Accrue this contract points
        accrueVault(epochId, vault);

        // Now that they are accrue, just use the points to estimate reward and send
        uint256 userPoints = points[epochId][vault][user];
        uint256 pointsLeft = userPoints - pointsWithdrawn[epochId][vault][user][token];

        // Early return
        if(pointsLeft == 0){
            return;
        }

        // Get amounts to divide over
        uint256 vaultTotalPoints = totalPoints[epochId][vault];
        uint256 thisContractVaultPoints = points[epochId][vault][address(this)];

        
        // We got some stuff left // Use ratio to calculate what we got left
        uint256 totalAdditionalReward = rewards[epochId][vault][token];

        // NOTE: We don't check for zero reward, make sure to claim a token you can receive!

        // NOTE: Divison at end to minimize dust, on avg 2 Million Claims = 1 USDC of dust
        uint256 tokensForUser = totalAdditionalReward * pointsLeft / (vaultTotalPoints - thisContractVaultPoints);
        
        // Update points
        unchecked {
            // Cannot overflow per the math above
            pointsWithdrawn[epochId][vault][user][token] += pointsLeft;
        }

        // Transfer the token
        IERC20(token).safeTransfer(user, tokensForUser);
    }

    /// @dev Claim Rewards, without accruing points, saves gas for one-off claims
    function claimReward(uint256 epochId, address vault, address token, address user) public {
        require(epochId < currentEpoch()); // dev: !can only claim ended epochs

        (uint256 userBalanceAtEpochId, ) = getBalanceAtEpoch(epochId, vault, user);

        // For all epochs from start to end, get user info
        UserInfo memory userInfo = getUserNextEpochInfo(epochId, vault, user, userBalanceAtEpochId);

        // If userPoints are zero, go next fast
        if (userInfo.userEpochTotalPoints == 0) {
            return; // Nothing to claim
        }


        (uint256 vaultSupplyAtEpochId, ) = getTotalSupplyAtEpoch(epochId, vault);
        (uint256 startingContractBalance, ) = getBalanceAtEpoch(epochId, vault, address(this));

        VaultInfo memory vaultInfo = getVaultNextEpochInfo(epochId, vault, vaultSupplyAtEpochId);
        UserInfo memory thisContractInfo = getUserNextEpochInfo(epochId, vault, address(this), startingContractBalance);


        // To be able to use the same ratio for all tokens, we need the pointsWithdrawn to all be 0
        require(pointsWithdrawn[epochId][vault][user][token] == 0); // dev: You already claimed during the epoch, cannot optimize

        // We got some stuff left // Use ratio to calculate what we got left
        uint256 totalAdditionalReward = rewards[epochId][vault][token];

        // Calculate tokens for user
        uint256 tokensForUser = totalAdditionalReward * userInfo.userEpochTotalPoints / (vaultInfo.vaultEpochTotalPoints - thisContractInfo.userEpochTotalPoints);
        
        // We checked it was zero, no need to add
        pointsWithdrawn[epochId][vault][user][token] = userInfo.userEpochTotalPoints;

        IERC20(token).safeTransfer(user, tokensForUser);
    }

    /// @dev Claim Rewards, without accruing points, for non-emitting vaults, saves gas for one-off claims
    function claimRewardNonEmitting(uint256 epochId, address vault, address token, address user) public {
        require(epochId < currentEpoch()); // dev: !can only claim ended epochs

        // Get balance for this epoch
        (uint256 userBalanceAtEpochId, ) = getBalanceAtEpoch(epochId, vault, user);
        
        // Get user info for this epoch
        UserInfo memory userInfo = getUserNextEpochInfo(epochId, vault, user, userBalanceAtEpochId);

        // If userPoints are zero, go next fast
        if (userInfo.userEpochTotalPoints == 0) {
            return; // Nothing to claim
        }

        (uint256 vaultSupplyAtEpochId, ) = getTotalSupplyAtEpoch(epochId, vault);

        VaultInfo memory vaultInfo = getVaultNextEpochInfo(epochId, vault, vaultSupplyAtEpochId);

        // To be able to use the same ratio for all tokens, we need the pointsWithdrawn to all be 0
        require(pointsWithdrawn[epochId][vault][user][token] == 0); // dev: You already claimed during the epoch, cannot optimize

        // We got some stuff left // Use ratio to calculate what we got left
        uint256 totalAdditionalReward = rewards[epochId][vault][token];

        // Calculate tokens for user
        uint256 tokensForUser = totalAdditionalReward * userInfo.userEpochTotalPoints / vaultInfo.vaultEpochTotalPoints;
        
        // We checked it was zero, no need to add
        pointsWithdrawn[epochId][vault][user][token] = userInfo.userEpochTotalPoints;

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

        uint256[] memory amounts = new uint256[](tokensLength); // We'll map out amounts to tokens for the bulk transfers
        for(uint epochId = epochStart; epochId <= epochEnd; ) {
            // Accrue each vault and user for each epoch
            accrueUser(epochId, vault, user);

            // Now that they are accrued, just use the points to estimate reward and send
            uint256 userPoints = points[epochId][vault][user];
            
            // No need for more SLOADs if points are zero
            if(userPoints == 0){
                unchecked { ++epochId; }
                continue;
            }

            accrueUser(epochId, vault, address(this)); // Accrue this contract points
            accrueVault(epochId, vault);

            uint256 vaultTotalPoints = totalPoints[epochId][vault];
            uint256 thisContractVaultPoints = points[epochId][vault][address(this)];



            // We multiply just to avoid rounding

            // Loop over the tokens and see the points here
            for(uint256 i; i < tokensLength; ){
                
                // To be able to use the same ratio for all tokens, we need the pointsWithdrawn to all be 0
                // To allow for this I could loop and check they are all zero, which would allow for further optimization
                require(pointsWithdrawn[epochId][vault][user][tokens[i]] == 0); // dev: You already accrued during the epoch, cannot optimize

                // Use ratio to calculate tokens to send
                uint256 totalAdditionalReward = rewards[epochId][vault][tokens[i]];
                // Which means they claimed all points for that token
                pointsWithdrawn[epochId][vault][user][tokens[i]] = userPoints; // Can assign because we checked it's 0 above
                amounts[i] += totalAdditionalReward * userPoints / (vaultTotalPoints - thisContractVaultPoints);

                unchecked { ++i; }
            }

            unchecked { ++epochId; }
        }

        // Go ahead and transfer
        for(uint256 i; i < tokensLength; ){
            IERC20(tokens[i]).safeTransfer(user, amounts[i]);

            unchecked { ++i; }
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

            // Now that they are accrue, just use the points to estimate reward and send
            uint256 userPoints = points[epochId][vault][user];

            // Early return
            if(userPoints == 0){
                unchecked { ++epochId; }
                continue;
            }

            accrueUser(epochId, vault, address(this)); // Accrue this contract points
            accrueVault(epochId, vault);

            uint256 vaultTotalPoints = totalPoints[epochId][vault];
            uint256 thisContractVaultPoints = points[epochId][vault][address(this)];

            // NOTE: We don't set the pointsWithdrawn here because we will set the user shares to 0 later
            // While maintainingn lastAccrueTimestamp to now so they can't reaccrue

            // Loop over the tokens and see the points here
            for(uint256 i; i < tokensLength; ){
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

        // Optimization: can delete timestamp data on everything between epochStart and epochEnd
        // because shares will be zero in this interval (due to above deletes) so any accrual will not actually add
        // points. Need to keep the timestamp data on epochStart so you can't go backwards from one of these middle epochs
        // to get a non-zero balance and get points again
        unchecked {
            // Sums cannot overflow
            for(uint epochId = epochStart + 1; epochId < epochEnd; ++epochId) {
                delete lastUserAccrueTimestamp[epochId][vault][user];
            }
        }
        
        // For last epoch, we don't delete the shares, but we delete the points
        delete points[epochEnd][vault][user];

        // Go ahead and transfer
        for(uint256 i; i < tokensLength; ){
            IERC20(tokens[i]).safeTransfer(user, amounts[i]);
            unchecked { ++i; }
        }
    }

    /// === Bulk Claims END === ///

    /// === Add Bulk Rewards === ///

    /// @dev Given start and endEpoch, add an equal split of amount of token for the given vault
    /// @notice Use this to save gas and do a linear distribution over multiple epochs
    ///     E.g. for Liquidity Mining or to incentivize liquidity / rent it
    /// @notice Will not work with feeOnTransferTokens, use the addReward function for those
    function addBulkRewardsLinearly(uint256 startEpoch, uint256 endEpoch, address vault, address token, uint256 total) external nonReentrant {
        require(startEpoch >= currentEpoch()); // dev: Cannot add in the past
        require(endEpoch >= startEpoch); // dev: no epochs
        uint256 totalEpochs;
        unchecked {
            totalEpochs = endEpoch - startEpoch + 1;
        }
        // Amount needs to be equally divisible per epoch, for custom additions, use this and then add more single rewards
        require(total % totalEpochs == 0); // dev: multiple
        uint256 perEpoch = total / totalEpochs;

        // Transfer Token in, must receive the exact total
        uint256 startBalance = IERC20(token).balanceOf(address(this));  
        IERC20(token).safeTransferFrom(msg.sender, address(this), total);
        uint256 endBalance = IERC20(token).balanceOf(address(this));

        require(endBalance - startBalance == total); // dev: no weird fees bruh

        // Give each epoch an equal amount of reward
        for(uint256 epochId = startEpoch; epochId <= endEpoch; ) {
            
            unchecked {
                rewards[epochId][vault][token] += perEpoch;
            }

            unchecked { 
                ++epochId;
            }
        }
    }

    /// @dev Given start and endEpoch, add the token amounts of rewards for the interval specified
    /// @notice Use this to save gas and do a custom distribution over multiple epochs
    ///     E.g. for Liquidity Mining where there's a curve (less rewards over time)
    /// @notice Will not work with feeOnTransferTokens, use the addReward function for those
    function addBulkRewards(uint256 startEpoch, uint256 endEpoch, address vault, address token, uint256[] calldata amounts) external nonReentrant {
        require(startEpoch >= currentEpoch()); // dev: Cannot add in the past
        require(endEpoch >= startEpoch); // dev: no epochs
        uint256 totalEpochs;
        unchecked {
            totalEpochs = endEpoch - startEpoch + 1;
        }
        require(totalEpochs == amounts.length); // dev: Length Mismatch

        // Calculate total for one-off transfer
        uint256 total;
        for(uint256 i; i < totalEpochs; ) {
            unchecked {
                total += amounts[i];
                ++i;
            }
        }

        // Transfer Token in, must receive the exact total
        uint256 startBalance = IERC20(token).balanceOf(address(this));  
        IERC20(token).safeTransferFrom(msg.sender, address(this), total);
        uint256 endBalance = IERC20(token).balanceOf(address(this));

        require(endBalance - startBalance == total); // dev: no weird fees bruh

        // Give each epoch an equal amount of reward
        for(uint256 epochId = startEpoch; epochId <= endEpoch; ) {
            unchecked {
                rewards[epochId][vault][token] += amounts[epochId - startEpoch];
            }

            unchecked { 
                ++epochId;
            }
        }
    }

    /// @notice Utility function to specify a group of emissions for the specified epochs, vaults with tokens
    function addRewards(uint256[] calldata epochIds, address[] calldata vaults, address[] calldata tokens, uint256[] calldata amounts) external nonReentrant{
        uint256 vaultsLength = vaults.length;
        require(vaultsLength == epochIds.length); // dev: length mismatch
        require(vaultsLength == amounts.length); // dev: length mismatch
        require(vaultsLength == tokens.length); // dev: length mismatch

        for(uint256 i; i < vaultsLength; ){
            _addReward(epochIds[i], vaults[i], tokens[i], amounts[i]);

            unchecked {
                ++i;
            }
        }
    }

    /// @dev see `_addReward`
    function addReward(uint256 epochId, address vault, address token, uint256 amount) external nonReentrant {
        _addReward(epochId, vault, token, amount);
    }


    /// @notice Add an additional reward for the current epoch
    /// @notice No particular rationale as to why we wouldn't allow to send rewards for older epochs or future epochs
    /// @notice The typical use case is for this contract to receive certain rewards that would be sent to the badgerTree
    /// @notice nonReentrant because tokens could inflate rewards, this would only apply to the specific token, see reports for more
    function _addReward(uint256 epochId, address vault, address token, uint256 amount) internal {
        require(epochId >= currentEpoch());

        // Check change in balance to support `feeOnTransfer` tokens as well
        uint256 startBalance = IERC20(token).balanceOf(address(this));  
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
        uint256 endBalance = IERC20(token).balanceOf(address(this));

        // Allow underflow in case of malicious token
        uint256 diff = endBalance - startBalance;

        unchecked {
            rewards[epochId][vault][token] += diff;
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
        // Vault is msg.sender, and msg.sender cost 1 less gas

        if (from == address(0)) {
            _handleDeposit(msg.sender, to, amount);
        } else if (to == address(0)) {
            _handleWithdrawal(msg.sender, from, amount);
        } else {
            _handleTransfer(msg.sender, from, to, amount);
        }
    }

    /// @dev handles a deposit for vault, to address of amount
    function _handleDeposit(address vault, address to, uint256 amount) internal {
        uint256 cachedCurrentEpoch = currentEpoch();
        accrueUser(cachedCurrentEpoch, vault, to);
        accrueVault(cachedCurrentEpoch, vault); // We have to accrue vault as totalSupply is gonna change

        unchecked {
            // Add deposit data for user
            shares[cachedCurrentEpoch][vault][to] += amount;

            // And total shares for epoch
            totalSupply[cachedCurrentEpoch][vault] += amount;
        }
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

        unchecked {
            // Add deposit data for to
            shares[cachedCurrentEpoch][vault][to] += amount;
        }

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
            points[epochId][vault][user] += timeLeftToAccrue * currentBalance;
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
        if(lastUserAccrueTimestamp[epochId][vault][user] != 0 ) {
            return (shares[epochId][vault][user], false);
        }

        // Shortcut
        if(epochId == 1) {
            // If epoch is first one, and we don't have a balance, then balance is zero
            return (0, false);

            // This allows to do epochId - 1 below
        }

        uint256 lastBalanceChangeEpoch = 0; // We haven't found it

        // Pessimistic Case, we gotta fetch the balance from the lastKnown Balances (could be up to currentEpoch - totalEpochs away)
        // Because we have lastUserAccrueTimestamp, let's find the first non-zero value, that's the last known balance
        // Notice that the last known balance we're looking could be zero, hence we look for a non-zero change first
        for(uint256 i = epochId - 1; i > 0; ){
            // NOTE: We have to loop because while we know the length of an epoch 
            // we don't have a guarantee of when it starts

            if(lastUserAccrueTimestamp[i][vault][user] != 0) {
                lastBalanceChangeEpoch = i;
                break; // Found it
            }

            unchecked {
                --i;
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
        for(uint i; i < arrLength - 1; ) { // only up to len - 1 (no j to check if i == len - 1)
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


    /// ===== EXPERIMENTAL ==== ////

    /// NOTE: Non storage writing functions
    /// With the goal of making view functions cheap
    /// And to make optimized claiming way cheaper
    /// Intuition: On optimized version we delete storage
    /// This means the values are not useful after we've used them
    /// So let's skip writing to storage all together, use memory and skip any SSTORE, saving 5k / 20k per epoch per claim


    /// NOTE: These functions are based on the assumption that epochs are ended
    /// They are meant to optimize claiming
    /// For this reason extreme attention needs to be put into verifying that the epochs used have ended
    /// If it's not massive gas we may just check that `epochId` < `currentEpoch` but for now we can just assume and then we'll test


    /// NOTE: While the functions are public, only the uses that are internal will make sense, for that reason
    /// DO NOT USE THESE FUNCTIONS FOR INTEGRATIONS, YOU WILL GET REKT
    /// These functions should be private, but I need to test them right now.


    /// === Optimized functions === ////
    /// Invariant -> Epoch has ended
    /// Invariant -> Never changed means full duration & Balance is previously known
    /// 2 options. 
        /// Never accrued -> Use SECONDS_PER_EPOCH and prevBalance
        /// We did accrue -> Read Storage
    
    /// @dev Get the balance and timeLeft so you can calculate points
    /// @return balance - the balance of the user in this epoch
    /// @return timeLeftToAccrue - how much time in the epoch left to accrue (userPoints + balance * timeLeftToAccrue == totalPoints)
    /// @return userEpochTotalPoints - -> The totalPoints, getting them from here will save gas
    
    struct UserInfo {
        uint256 balance;
        uint256 timeLeftToAccrue;
        uint256 userEpochTotalPoints; 
        uint256 pointsInStorage;
    }
    
    /// @dev Return the userEpochInfo for the given epochId, vault, user
    /// @notice Requires `prevEpochBalance` to allow optimized claims
    ///     If an accrual happened during `epochId` it will read data from storage (expensive)
    ///     If no accrual happened (optimistic case), it will use `prevEpochBalance` to compute the rest of the values
    function getUserNextEpochInfo(uint256 epochId, address vault, address user, uint256 prevEpochBalance) public view returns (UserInfo memory info) {
        // Ideal scenario is no accrue, no balance change so that we can calculate all from memory without checking storage
        
        require(epochId < currentEpoch()); // dev: epoch must be over // TODO: if we change to internal we may remove to save gas

        // Time left to Accrue //
        uint256 lastBalanceChangeTime = lastUserAccrueTimestamp[epochId][vault][user];
        if(lastBalanceChangeTime == 0) {
            info.timeLeftToAccrue = SECONDS_PER_EPOCH;
        } else {
            // NOTE: If we do else if we gotta load the struct into memory
            // because we optimize for the best case, I believe it's best not to use else if here
            // If you got math to prove otherwise please share: alex@badger.com

            // An accrual for the epoch has happened
            Epoch memory epochData = getEpochData(epochId);

            // Already accrued after epoch end
            if(lastBalanceChangeTime >= epochData.endTimestamp){
                // timeLeftToAccrue = 0; // No need to set
            } else {
                info.timeLeftToAccrue = _min(epochData.endTimestamp - lastBalanceChangeTime, SECONDS_PER_EPOCH);
            }
        }

        // Balance //
        if(lastBalanceChangeTime == 0) {
            info.balance = prevEpochBalance;
        } else {
            info.balance = shares[epochId][vault][user];
        }

        // Points //

        // Never accrued means points in storage are 0
        if(lastBalanceChangeTime == 0) {
            // Just multiply from scratch
            info.userEpochTotalPoints = info.balance * info.timeLeftToAccrue;
        } else {
            // We have accrued, return the sum of points from storage and the points that are not accrued
            info.pointsInStorage = points[epochId][vault][user];
            info.userEpochTotalPoints = info.pointsInStorage + info.balance * info.timeLeftToAccrue;
        }
    }

    struct VaultInfo {
        uint256 vaultTotalSupply;
        uint256 timeLeftToAccrue;
        uint256 vaultEpochTotalPoints;
        uint256 pointsInStorage;
    }

    /// @dev Same as above but for Vault
    function getVaultNextEpochInfo(uint256 epochId, address vault, uint256 prevEpochTotalSupply) public view returns (VaultInfo memory info) {
        require(epochId < currentEpoch()); // dev: epoch must be over // TODO: if we change to internal we may remove to save gas

        uint256 lastAccrueTime = lastAccruedTimestamp[epochId][vault];
        if(lastAccrueTime == 0) {
            info.timeLeftToAccrue = SECONDS_PER_EPOCH;
        } else {
            // NOTE: If we do else if we gotta load the struct into memory
            // because we optimize for the best case, I believe it's best not to use else if here
            // If you got math to prove otherwise please share: alex@badger.com
            
            // An accrual for the epoch has happened
            Epoch memory epochData = getEpochData(epochId);

            // Already accrued after epoch end
            if(lastAccrueTime >= epochData.endTimestamp) {
                // timeLeftToAccrue = 0;
            } else {
                info.timeLeftToAccrue = _min(epochData.endTimestamp - lastAccrueTime, SECONDS_PER_EPOCH);
            }
        }

        if(lastAccrueTime == 0) {
            info.vaultTotalSupply = prevEpochTotalSupply;
        } else {
            info.vaultTotalSupply = totalSupply[epochId][vault];
        }


        if(lastAccrueTime == 0) {
            // Just multiply from scratch
            info.vaultEpochTotalPoints = info.vaultTotalSupply * info.timeLeftToAccrue;
            // pointsInStorage = 0;
        } else {
            // We have accrued, return the sum of points from storage and the points that are not accrued
            info.pointsInStorage = totalPoints[epochId][vault];
            info.vaultEpochTotalPoints = info.pointsInStorage + info.vaultTotalSupply * info.timeLeftToAccrue;
        }
    }


    struct OptimizedClaimParams {
        uint256 epochStart;
        uint256 epochEnd;
        address vault;
        address[] tokens;
    }

    /// @dev My attempt at making this contract actually usable on mainnet
    function claimBulkTokensOverMultipleEpochsOptimizedWithoutStorage(OptimizedClaimParams calldata params) external {
        require(params.epochStart <= params.epochEnd); // dev: epoch math wrong
        address user = msg.sender; // Pay the extra 3 gas to make code reusable, not sorry
        require(params.epochEnd < currentEpoch()); // dev: epoch math wrong 
        _requireNoDuplicates(params.tokens);

        // Instead of accruing user and vault, we just compute the values in the loop
        // We can use those value for reward distribution
        // We must update the storage that we don't delete to ensure that user can only claim once
        // This is equivalent to deleting the user storage

        (uint256 userBalanceAtEpochId, ) = getBalanceAtEpoch(params.epochStart, params.vault, user);
        (uint256 vaultSupplyAtEpochId, ) = getTotalSupplyAtEpoch(params.epochStart, params.vault);
        (uint256 startingContractBalance, ) = getBalanceAtEpoch(params.epochStart, params.vault, address(this));

        uint256 tokensLength = params.tokens.length;
        uint256[] memory amounts = new uint256[](tokensLength); // We'll map out amounts to tokens for the bulk transfers
    
        for(uint epochId = params.epochStart; epochId <= params.epochEnd;) {

            // For all epochs from start to end, get user info
            UserInfo memory userInfo = getUserNextEpochInfo(epochId, params.vault, user, userBalanceAtEpochId);
            VaultInfo memory vaultInfo = getVaultNextEpochInfo(epochId, params.vault, vaultSupplyAtEpochId);
            UserInfo memory thisContractInfo = getUserNextEpochInfo(epochId, params.vault, address(this), startingContractBalance);

            // If userPoints are zero, go next fast
            if (userInfo.userEpochTotalPoints == 0) {
                // NOTE: By definition user points being zero means storage points are also zero
                userBalanceAtEpochId = userInfo.balance;
                vaultSupplyAtEpochId = vaultInfo.vaultTotalSupply;
                startingContractBalance = thisContractInfo.balance;

                unchecked { ++epochId; }
                continue;
            }

            // Use the info to get userPoints and vaultPoints
            if (userInfo.pointsInStorage > 0) {
                delete points[epochId][params.vault][user]; // Delete them as they need to be set to 0 to avoid double claiming
            }

        
            // Use points to calculate amount of rewards
            for(uint256 i; i < tokensLength; ){
                address token = params.tokens[i];

                // To be able to use the same ratio for all tokens, we need the pointsWithdrawn to all be 0
                require(pointsWithdrawn[epochId][params.vault][user][token] == 0); // dev: You already accrued during the epoch, cannot optimize

                // Use ratio to calculate tokens to send
                uint256 totalAdditionalReward = rewards[epochId][params.vault][token];
        
                amounts[i] += totalAdditionalReward * userInfo.userEpochTotalPoints / (vaultInfo.vaultEpochTotalPoints - thisContractInfo.userEpochTotalPoints);
                unchecked { ++i; }
            }


            // End of iteration, assign new balances for next loop
            unchecked {
                userBalanceAtEpochId = userInfo.balance;
                vaultSupplyAtEpochId = vaultInfo.vaultTotalSupply;
                startingContractBalance = thisContractInfo.balance;
            }

            unchecked { ++epochId; }
        }

        // == Storage Changes == //
        // No risk of overflow but seems to save 26 gas
        unchecked {
            // Port over shares from last check
            shares[params.epochEnd][params.vault][user] = userBalanceAtEpochId; 

            // Delete the points for that epoch so nothing more to claim
            delete points[params.epochEnd][params.vault][user]; // This may be zero and may have already been deleted

            // Because we set the accrue timestamp to end of the epoch
            lastUserAccrueTimestamp[params.epochEnd][params.vault][user] = block.timestamp; // Must set thsi so user can't claim and their balance here is non-zero / last known
            
            // And we delete the initial balance meaning they have no balance left
            delete shares[params.epochStart][params.vault][user];
            lastUserAccrueTimestamp[params.epochStart][params.vault][user] = block.timestamp;
        }

        // Go ahead and transfer
        {
            for(uint256 i; i < tokensLength; ){
                IERC20(params.tokens[i]).safeTransfer(user, amounts[i]);
                unchecked { ++i; }
            }
        }
    }

    /// @dev See above but for non-emitting strategy
    function claimBulkTokensOverMultipleEpochsOptimizedWithoutStorageNonEmitting(OptimizedClaimParams calldata params) external {
        require(params.epochStart <= params.epochEnd); // dev: epoch math wrong
        address user = msg.sender; // Pay the extra 3 gas to make code reusable, not sorry
        require(params.epochEnd < currentEpoch()); // dev: epoch math wrong 
        _requireNoDuplicates(params.tokens);

        // Instead of accruing user and vault, we just compute the values in the loop
        // We can use those value for reward distribution
        // We must update the storage that we don't delete to ensure that user can only claim once
        // This is equivalent to deleting the user storage

        (uint256 userBalanceAtEpochId, ) = getBalanceAtEpoch(params.epochStart, params.vault, user);
        (uint256 vaultSupplyAtEpochId, ) = getTotalSupplyAtEpoch(params.epochStart, params.vault);

        // Cache tokens length, resused in loop and at end for transfer || Saves almost 1k gas over a year of claims
        uint256 tokensLength = params.tokens.length;

        uint256[] memory amounts = new uint256[](tokensLength); // We'll map out amounts to tokens for the bulk transfers
    
        for(uint epochId = params.epochStart; epochId <= params.epochEnd;) {

            // For all epochs from start to end, get user info
            UserInfo memory userInfo = getUserNextEpochInfo(epochId, params.vault, user, userBalanceAtEpochId);
            VaultInfo memory vaultInfo = getVaultNextEpochInfo(epochId, params.vault, vaultSupplyAtEpochId);

            // If userPoints are zero, go next fast
            if (userInfo.userEpochTotalPoints == 0) {
                // NOTE: By definition user points being zero means storage points are also zero
                userBalanceAtEpochId = userInfo.balance;
                vaultSupplyAtEpochId = vaultInfo.vaultTotalSupply;

                unchecked { ++epochId; }
                continue;
            }

            // Use the info to get userPoints and vaultPoints
            if (userInfo.pointsInStorage > 0) {
                delete points[epochId][params.vault][user]; // Delete them as they need to be set to 0 to avoid double claiming
            }

        
            // Use points to calculate amount of rewards
            for(uint256 i; i < tokensLength; ){
                address token = params.tokens[i];

                // To be able to use the same ratio for all tokens, we need the pointsWithdrawn to all be 0
                require(pointsWithdrawn[epochId][params.vault][user][token] == 0); // dev: You already accrued during the epoch, cannot optimize

                // Use ratio to calculate tokens to send
                uint256 totalAdditionalReward = rewards[epochId][params.vault][token];

                
                unchecked { 
                    // vaultEpochTotalPoints can't be zero if userEpochTotalPoints is > zero
                    amounts[i] += totalAdditionalReward * userInfo.userEpochTotalPoints / vaultInfo.vaultEpochTotalPoints;
                    ++i; 
                }
            }


            // End of iteration, assign new balances for next loop
            unchecked {
                // Seems to save 26 gas
                userBalanceAtEpochId = userInfo.balance;
                vaultSupplyAtEpochId = vaultInfo.vaultTotalSupply;
            }

            unchecked { ++epochId; }
        }

        // == Storage Changes == //
        // No risk of overflow but seems to save 26 gas
        unchecked {
            // Port over shares from last check
            shares[params.epochEnd][params.vault][user] = userBalanceAtEpochId; 

            // Delete the points for that epoch so nothing more to claim
            delete points[params.epochEnd][params.vault][user]; // This may be zero and may have already been deleted

            // Because we set the accrue timestamp to end of the epoch
            lastUserAccrueTimestamp[params.epochEnd][params.vault][user] = block.timestamp; // Must set thsi so user can't claim and their balance here is non-zero / last known
            
            // And we delete the initial balance meaning they have no balance left
            delete shares[params.epochStart][params.vault][user];
            lastUserAccrueTimestamp[params.epochStart][params.vault][user] = block.timestamp;
        }

        // Go ahead and transfer
        {
            for(uint256 i; i < tokensLength; ){
                IERC20(params.tokens[i]).safeTransfer(user, amounts[i]);
                unchecked { ++i; }
            }
        }
    }
}
