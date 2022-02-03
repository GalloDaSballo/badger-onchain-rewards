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

    uint256 private constant SECONDS_PER_EPOCH = 604800; // One epoch is one week
    address public BADGER = 0x3472A5A71965499acd81997a54BBA8D852C6E53d;
    address immutable governance;
    // This allows to specify rewards on a per week basis, making it easier to interact with contract

    address[] public registeredVaults; // list of vaults, just used for iterations and convenience
    // NOTE: Probably change to OpenZeppelin IterableSet
    
    mapping(uint256 => Epoch) public epochs; // Epoch data for each epoch epochs[epochId]
    // id is implicit in the list
    struct Epoch {
        uint256 startTimestamp;
        uint256 endTimestamp;
    }
    uint256 public currentEpoch = 1; // NOTE: Epoch 0 means you have withdrawn

    mapping(uint256 => mapping(address => uint256)) public badgerEmissionPerEpochPerVault; // Epoch data for each epoch badgerEmissionPerEpochPerVault[epochId][vaultAddress]
    

    mapping(uint256 => mapping(address => mapping(address => uint256))) public points; // Calculate points per each epoch points[epochId][vaultAddress][userAddress]
    mapping(uint256 => mapping(address => mapping(address => uint256))) public pointsWithdrawn; // Given point for epoch how many where withdrawn by user? pointsWithdrawn[epochId][vaultAddress][userAddress]
    
    mapping(uint256 => mapping(address => uint256)) public totalPoints; // Sum of all points given for a vault at an epoch totalPoints[epochId][vaultAddress]

    mapping(uint256 => mapping(address => uint256)) lastAccruedTimestamp; // Last timestamp in which vault was accrued - lastUserAccrueTimestamp[epochId][vaultAddress]
    mapping(address => mapping(address => uint256)) lastUserAccrueTimestamp; // Last timestamp in we accrued user to calculate rewards in epochs without interaction lastUserAccrueTimestamp[vaultAddress][userAddress]
    mapping(address => uint256) lastVaultDeposit; // Last Epoch in which any user deposited in the vault, used to know if vault needs to be brought to new epoch
    // AFAIK changing storage to the same value is a NO-OP and won't cost extra gas
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
    // However, we calculate your share by just multiplying the share * secodns in theb vault
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

    constructor() {
        governance = msg.sender;
    }

    /// @dev Add a vault to the list of tracked vaults
    /// @notice this is used to accrue the vault at the end of the epoch
    function addVault(address newVault) external {
        require(msg.sender == governance); // dev: !gov
        registeredVaults.push(newVault); // TODO: Change to OpenZeppelin
    }


    // TODO: Generalize the badger emission to any token
    // Honestly badger can be generalized to the any token structure, avoiding the need for extra mappings

    /// @dev Adds a new epoch and starts it
    /// 
    function startNextEpoch(uint256 startTimestamp) external {
        require(msg.sender == governance); // dev: !gov

        // End previous epoch math
        // NOTE Due to Invariant:
        // totalSupply is same as last changed
        // because all deposits are same since last change
        // We can calculate the maxPoints this way, which means we have the exact total amount of points
        // Each user can be accrued just when they claim to save them the extra gas cost

        address[] memory cachedVaults = registeredVaults; // Copy to memory to save gas
        uint256 length = cachedVaults.length; // Save lenght to memory to save gas because index costs an extra ADD
        uint256 cachedCurrentEpoch = currentEpoch; // Same deal, save gas
        for(uint256 i = 0; i < length; i++) {
            address cachedVault = cachedVaults[i];
            uint256 lastTime = lastAccruedTimestamp[cachedCurrentEpoch][cachedVault];
            // TODO: use lastTime to figure how much to accrue,
            // NOTE: If vault was never accrued, max is SECONDS_PER_EPOCH
            // NOTE: Value must be less than SECONDS_PER_EPOCH
            totalPoints[cachedCurrentEpoch][cachedVault] += lastTime * totalSupply[cachedCurrentEpoch][cachedVault];
        }
        // INVARIANT: totalSupply changes on every withdraw and deposit
        // If it hasn't changed, it means nothing happened this epoch
        // NOTE: Worse case scenario (no interaction) in which case you do need to fetch the value from prev-epoch
        // NOTE: I any other case, totalPoints is just timeLeft * totalSupply


        

        // if current epoch has no points, it means that this epoch had zero transfer, withdrawals, etc
        // I don't believe this will happen in practice, but in the case it does
        // Points for each person are equal to deposit * multiplier
        // Total points are just totalSupply * multiplier * timeLeft since last accrue

        // Cache and pre-increment to change storage while saving gas laters
        uint256 newEpochId = ++currentEpoch;

        uint256 x = 1;
        epochs[newEpochId] = Epoch(
            startTimestamp,
            startTimestamp + SECONDS_PER_EPOCH
        );
        // Epochs have fixed duration

        // Rewards can be specified until end of this new epoch
    }
    // NOTE: What happens if you have no points for epoch

    function claimRewards(uint256[] calldata epochsToClaim, address[] calldata vaults, uint256[][] calldata tokens) external{
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
        _accrueUser(vault, to);
        
        // Add deposit data for user
        shares[currentEpoch][vault][to] += amount;

        // And total shares for epoch
        totalSupply[currentEpoch][vault] += amount;
    }

    /// @dev handles a withdraw for vault, from address of amount
    function _handleWithdrawal(address vault, address from, uint256 amount) internal {
        _accrueUser(vault, from);

        // Delete last shares
        // Delete deposit data or user
        shares[currentEpoch][vault][from] -= amount;
        // Reduce totalSupply
        totalSupply[currentEpoch][vault] -= amount;

    }

    /// @dev handles a transfer for vault, from address to address of amount
    function _handleTransfer(address vault, address from, address to, uint256 amount) internal {
        // Accrue points for from, so they get rewards
        _accrueUser(vault, from);
        // Accrue points for to, so they don't get too many rewards
        _accrueUser(vault, to);

         // Add deposit data for to
        shares[currentEpoch][vault][to] += amount;

         // Delete deposit data for from
        shares[currentEpoch][vault][from] -= amount;
    }

    /// @dev Accrue points gained during this epoch
    /// @notice This is called for both receiving, sending, depositing and withdrawing, any time the user balance changes
    /// @notice To properly accrue for this epoch:
    /// @notice Figure out the time passed since last accrue (max is start of epoch)
    /// @notice Figure out their points (their current balance) (before we update)
    /// @notice Just multiply the points * the time, those are the points they've earned
    function _accrueUser(address vault, address user) private {
        // However that could be zero, hence we check for lastUserAccrueTimestamp
        uint256 toMultiply = _getBalanceAtCurrentEpoch(vault, user);

        // TODO Fast fail here, if balance is 0, just update timestamp and be done with it

        uint256 timeInEpochSinceLastAccrue = _getTimeInEpochFromLastAccrue(vault, user);


        // Run the math and update the system
        uint256 newPoints = toMultiply * timeInEpochSinceLastAccrue;
        
        // Track user rewards
        points[currentEpoch][vault][user] += newPoints;
        // Track total points
        totalPoints[currentEpoch][vault] += newPoints;
        // At end of epoch userPoints / totalPoints is the percentage the user can receive of rewards (valid for any reward)

        // Set last time for updating the user
        lastUserAccrueTimestamp[vault][user] = block.timestamp;
    }



    /// @dev Given vault and user, find the last known balance
    /// @notice since we may look in the past, we also update the balance for current epoch
    function _getBalanceAtCurrentEpoch(address vault, address user) internal returns (uint256) {

        // Time Last Known Balance has changed
        uint256 lastBalanceChangeTime = lastUserAccrueTimestamp[vault][user];
        
        uint256 lastBalanceChangeEpoch = 0; // 0 means it never changed
        // If we return 0, it means that this is their first deposit

        // TODO: Since we're basically making it more and more expensive to interact, 
        // we may wanna have a way to track the first interaction as a way to save the user paying too much gas the first time
        // TODO: Get this version out and test
        // The worst case scenario is for the first deposit in the vault
        // They end up having to loop over this for each epoch just to figure out they haven't deposited
        // Having a false value may be worth it
        // Specifically a flag would be worth it after 20000 / 2100 9 epochs 
        // 2100 is cost of SLOAD on cold memo
        // 20k is cost of storing the flag to signal that we did do the check
        // To simplify/streamline that we could just store another variable to check the last epoch at which they interacted
        // 0 indicating they never interacted with the vault
        // Doing so would still cost the 20k for the 0 -> N epoch
        // It would also increase cost on each non-epoch deposit and withdrawal
        // The increase would be by 5000 gas (non-zero to non-zero)
        // Which is the equivalent of trying to read from a little less than 3 epochs
        // i.e. if they interact more than once per 3 epochs, it costs them more
        // If they interact less than once per 3 epochs, it saves them gas

        // Math NOTE: we must fix as over 100 epochs the cost goes to 210k gas which is basically 0.21 eth (900 usd)
        // No one will ever deposit if they have to pay 1k (and that's just for this btw)

        // Find Epoch
        // TODO: Gas - Iterate over memory to save gas
        // TODO: Do we have a epoch 0??? Don't think so
        for(uint256 i = currentEpoch; i > 0; i--){
            // NOTE: We have to loop because while we know the length of an epoch 
            // we don't have a guarantee of when it starts

            // We're going backwards from currentEpoch to 0, once we get to zero we know we didn't find
            if(epochs[i].startTimestamp >= lastBalanceChangeTime && lastBalanceChangeTime < epochs[i].endTimestamp){
                // It's in the 2 times, this is the epoch we're looking for
                lastBalanceChangeEpoch = i;
                break; // Break to save gas, we're done
            }
        }

        if(lastBalanceChangeEpoch == 0) {
            return 0;
        } 

        // NOTE: Since the user interacted and we'll end up removing balance, we need to update their balance at this epoch to ensure

        // TO avoid extra consuption
        if(lastBalanceChangeEpoch != currentEpoch) {
            // We update their balance at current only if we haven't already
            shares[currentEpoch][vault][user] = shares[lastBalanceChangeEpoch][vault][user];
        }

        // Since we always update their balance at current epoch, just return that
        return shares[currentEpoch][vault][user];



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


    // IF we add a way to track first interaction and last interaction
    
    /// @dev Given a vault and user, figure out the time that passed in this epoch since last accrue
    /// @notice Invariant: max is SECONDS_PER_EPOCH
    /// @notice Invariant: If user was never accrued this epoch, then their time is the current epochDuration
    function _getTimeInEpochFromLastAccrue(address vault, address user) internal returns (uint256) {
        uint256 lastBalanceChangeTime = lastUserAccrueTimestamp[vault][user];

        // Change in balance happened this epoch, just ensure we are in active epoch and return difference
        // TODO: Think about the require to decide if it's worth doing
        if(lastBalanceChangeTime > epochs[currentEpoch].endTimestamp) {
            require(block.timestamp < epochs[currentEpoch].endTimestamp, "No epoch active"); // I believe this require can be helpful if we're not in an active epoch, which hopefully we can avoid
            return lastBalanceChangeTime - epochs[currentEpoch].startTimestamp; // Also avoids overflow
        }

        // Otherwise we return max time which is current - epochStart
        return block.timestamp - epochs[currentEpoch].startTimestamp;
    }

    // YOU DO NOT NEED TO ACCRUE OLD EPOCHS UNTIL YOU REDEEM
    // The reason is: They are not changing, the points that have changed have already and the points that are not changed are
    // just going to be deposit * time_spent as per the invariant

}