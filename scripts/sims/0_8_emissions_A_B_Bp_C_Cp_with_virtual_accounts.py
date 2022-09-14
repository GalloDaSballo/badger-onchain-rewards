from hashlib import sha256
from pprint import pprint

from random import seed
from random import random
from copy import deepcopy
from tokenize import String

"""
  Visualization:
    https://miro.com/app/board/uXjVPfL1y3I=/
  
  Given TokenA -> RewardB -> RewardC

  General Case 2) Random Many to Many some are self-emitting (question is, do we need extra math or not?)

  e.g. (Full)
  From A -> B -> C
         -> B from B -> C from B from B
                   C -> C from C
                   C -> C from C from B from B

This Simulates A -> B -> B'
Where B and B' are not all for the depositors of A

  Token A can be Self-emitting or not (shouldn't matter) - TotalPoints
  
  Math to prove self-emitting is reduceable to this case
  Token A Self-Emitting doesn't matter as long as:
  A -> A' is always claimed first and calculates total supply as A - A'
  A -> B uses Total A
  

  Token B self emits, is also emitted by Vault β and some people hold token B
  - VAULT_B_REWARDS_TO_A
  - VAULT_B_SELF_EMISSIONS
  - VAULT_B_EMISSIONS_TO_OTHER ## Emissions of B for another random vault (Vault β)

  Fix calculation to:
    - Give back "less rewards" directly to direct claimers <- Back to 04 math which is the correct one
    
    Future Rewards Backwards Claims
    - NEW: 
      Reward Positions will claim their rewards when claimed and distribute to users
        Effectively a Reward is a "Virtual Account" meaning just like any user it's accruing rewards
        Because of this, when claiming, we need to claim the rewards that this "Virtual Position" has accrued
        Doing this allows us to never correct the divisor to unfair / overly fair levels, at the cost of computational complexity
        NOTE: At this time  I believe this to be the mathematically correct solution

  - Add non-random version which will help with debugging


  Handle Virtual Accounts along with B -> B' to simulate the "smart contract" claims

  Token C self emits, is also emitted by Vault E and some people hold token C
  - VAULT_C_REWARDS_TO_B
  - VAULT_C_SELF_EMISSIONS
  - VAULT_C_REWARDS_TO_OTHER ## Emissions of C for another random vault (Vault γ)
  - VAULT_C_HODLERS ## NOTE: Removed per cD' -> β explanation

  - Separate the noise / claims into functions
  - Use the functions for A -> B
  - Use the functions for B -> C
  - Add Noise back in

  - Rewrite all code to use list of tokens to make the random case more complicated
  - Create notation for generalized claiming
  - TODO Solve cross claims math with virtual accounts

  - TODO: Reconcile the vars below to make it so they are used as expected
"""

## Should we use randomness or use just the values provided?
DETERMINISTIC = True

## NOTE: a 1 epoch test MUST always pass
## because the issue of Future Rewards Backwards Claims is not relevant (there is no epoch of unclaimable rewards)
EPOCHS_RANGE = 0  ## Set to 0 to test specific epoch amounts
EPOCHS_MIN = 2

SHARES_DECIMALS = 18
RANGE = 10_000  ## Shares can be from 1 to 10k with SHARES_DECIMALS
MIN_SHARES = 1_000  ## Min shares per user
SECONDS_PER_EPOCH = 604800


### B VARS ###
MIN_VAULT_B_REWARDS_TO_A = (
    500  ## The "true" "base" yield from B -> A (without adding self-emissions)
)
VAULT_B_REWARDS_TO_A = 100_000  ## 100 k ETH example

## B'
VAULT_B_MIN_SELF_EMISSION = 500
VAULT_B_SELF_EMISSIONS = (
    1_000_000  ## 100M ETH example - Exacerbates issue with B -> B Claim
)

## Additional B Rewards (We call them β to separate) <- NOTE: May wanna remove noise for a time
VAULT_B_MIN_REWARDS_TO_OTHER = 0 ## TODO: Add back - Removed to nail down the math of claiming B -> C and C -> C'
VAULT_B_REWARDS_TO_OTHER = 100_000  ## Inflates total supply but is not added to rewards

## NOTE: Unused
## NOTE: See Math to prove we don't need as long as we have `VAULT_B_REWARDS_TO_OTHER`
# VAULT_B_HODLERS = 0


### C VARS ###
VAULT_C_MIN_REWARDS_TO_B = 0  ## 10 k ETH example
VAULT_C_REWARDS_TO_B = 0  ## 100 k ETH example

VAULT_C_MIN_SELF_EMISSIONS = 0  ## TODO: This must be 100% or I made a mistake
VAULT_C_SELF_EMISSIONS = 1_000  ## 1k ETH example

## NOTE: TODO - Zero to make initial sim simpler
## TODO: Add the math as it's not there yet
VAULT_C_MIN_REWARDS_TO_OTHER = 0
VAULT_C_REWARDS_TO_OTHER = (
    0  ## Inflates total supply but is not added to rewards
)



USERS_RANGE = 0
USERS_MIN = 2000


## How many simulations to run?
ROUNDS = 1_000 if not DETERMINISTIC else 1

## Should the print_if_if print_if stuff?
SHOULD_PRINT = ROUNDS == 1


def print_if(v):
    if SHOULD_PRINT:
        print(v)


def get_circulating_supply_at_epoch(total_supply, rewards, emissions, epoch, claim_depth):
    """
        Given the rewards and emissions
        Figure out the circulating supply at that epoch

        `claim_depth`: {enum} - Used to retrieve the divisor that is appropriate to the math
        0 -> Rewards -> Math V1 - total_supply -> Used for All non-emission claims
        1 -> Only Emissions -> Multiple emissions means we need to remove them from the circulating supply

        Ultimately the problem is to figure out circulating_supply, which does change after time

    """

    ## Given depth we'll need to go deeper / less deep
    if claim_depth == 0:
        return total_supply
    
    if claim_depth == 1:
        ## Remove the rewards until this epoch
        ## Remove the emissions until this epoch
        total_emissions_future = emissions[epoch]

        return total_supply - total_emissions_future




## Get total Claimed

## Get Virtual Accounts total Claimed

## Claim from Virtual Accounts as % of total Claimed vs claimable

## If I know how many rewards are locked in contract, and will only be available in the future
## I can claim the emissions from those rewards and use the Ratio to distribute them
# 
# 
# 
#  Reward if A != B
#  Emission if A == B
#  I can always tell if it's an emission or a reward
#  Question is what happens if I can claim from Reward and Emission to new Rewards?


## How do we get Emissions?
## Circulating Supply (- reward_i - emission_i-1) -> And ratio


## How do we get Reward from Reward + Emission?
## Circulating Supply (- reward_i - emission_i) -> And ratio
## Both are i as after the claim they are both circulating


## If No Reward nor emission can be added to future epochs
## Then we have a guarantee that divisor = total_supply for all Rewards
## And divisor = total_supply - points_from_current_emissions for all Emissions

## It follows that for a given Reward of Reward C
## For which B -> B' -> C
## Then receivedC = receivedB + receivedB' / total_supply
## Because a rational actor will claim B -> B' -> C
## Even if they could claim B -> C and loose on some emissions
## Meaning that if an emission is available it must always be claimed first

## Corollary being:
## C1 - A -> B type deal
## If no future tokens (rewards or emissions for future epochs) are present in the contract
## Meaning no extra points are being accrued to the contract but are not claimable then
## Any A -> B type claim will always be divided by B / totalSupply



## Vault -> Reward -> Emission -> Reward -> Emission -> Reward -> Emission -> Reward -> Emission -> Reward -> Emission
"""
A set of claims is basically a path to claims, where the starting point is always Vault
The intermediary steps are the token (and it's emission if available, perhaps packable via `bool`)


    1) A -> B -> B' -> C -> C'
    2) A -> C -> C'
    3) A -> D -> D' -> C -> C'

    Can be resolved as:

    1)
    A -> B
    B -> B'
    B -> C
    C -> C'

    2) 
    A -> C
    C -> C'

    3)
    A -> D
    D -> D'
    D -> C
    C -> C'

A cache of token ratios may help save gas, however ultimately
A "compound claim" is the ordered claim of pair of tokens, accrued to the current epoch


Given Paths 1, 2 and 3
A gas optimized claim would do:
A -> B -> B' -> C
A -> C
A -> D -> D' -> C
C(1 + 2+ 3) -> C'

However it may be impossible to make this replicable for all cases


## NOTE: On Subsegments

X -> A -> *
Z -> A -> *

While this would be mathematically equivalent to
X -> A
Z -> A
A -> *

Because of the function interface starting with one vault, I'll be ignoring that.
If the starting vault is different, just do n claims for each starting node

The sum of all partial claims will be equal to the total claim (minus rounding due to integer division)
"""




"""
    Let Vs = {A, B, ...Z} be the vector of balances

    TVi being Total Supply for Vault V at epoch i === Sum(A)
    vni being balance of user n at epoch i; with vni <= Sum(A)

    R being a generic reward

    Given that all Ri is claimable on each epoch

    Compound Claims Theorem

    For Each V ∈ Vs:
        Claim(V, n, i) ===
        {
            vi / Tvi * Ri; if V != R; Rewards Case
            vi / (Tvi - Ri); if V == R; Emissions Case
        }

    
    Corollary 1 - Definition of Circulating Supply

    Let Tvi being the total Supply for V ∈ Vs at epoch i;

    We define circulating supply (from the Contract POV) as 
    the sum of all Vault shares owned by users, 
    or that are rewards that can be claimed through ownership of a different Vault D ∈ Vs; D != V

    Given V ∈ Vs and TRi as the Sum(Ri) for given epoch i;
    With R == V;

    We separate TRV = TR + TV
    Where TV is circulating and TR are emissions for it

    Because TRV = TR + TV

    We define Circulating supply as TV, the amount of Rewards that are not emissions for the given Vault



    Corollary 2 - Linear Extension

    For Each V ∈ VS; 
    There is no difference if we prove theorems with a vector of one or a vector of n ∈ N

    Proof by absurd:

    Imagine a R as value of rewards and Ri ∈ N; as the specific reward claimable for epoch i

    If Ri is claimable by a single vector N ∈ Vs, then TNi the total supply of N at epoch i maps out to Ri

    If we were to introduce an additional vector M ∈ Vs with 50% of the rewards being equally split between N and M
    Then we would assert that:

    TNi maps out to 50% Ri
    and
    TMi maps out to 50% Ri

    Meaning that for any ni <= TNi; with TNi == SUM(ni); There exist a value r ∈ N; That each share amount can claim

    We can extend this idea to any number of Vaults for any ratio of Rewards.

    Given Vsi and it's subsets and Ri being respectively:
    The permutations of all possible vaults at epoch i and
    The permutation of all possible rewards for each epoch i
    
    With TRi == SUM(Ri) == C * Ri

    Meaning there must be a C ∈ <Q> (Vector of Rational Numbers) that maps out a ratio between TRi and Ri

    If there was no vector, then by absurd, in the case of a single vault 
    The following must be true:
    There is no c ∈ N such that
    TNi == SUM(ni) can claim c * Ri

    This is absurd per the example above
"""


## How do we codify Segments?

"""
    Start
    ClaimDepth
    ClaimTokens1
    ClaimEmissionTokens1
    ...
    ...
    ClaimTokens_ClaimDepth-1
    ClaimEmissionTokens_ClaimDepth-1


    ## What happens if in the middle we have start again?
    ## What happens if we have the same subpath X times?



    RANDOM_CLAIM_DEPTH

    RANDOM_CLAIM_TOKEN_LAYER_1...RANDOM_CLAIM_TOKEN_LAYER_N
    RANDOM_CLAIM_EMISSION_LAYER_1...RANDOM_CLAIM_EMISSION_LAYER_N


    ## What happens if we have the same subpath X times?
    We just recompute it and pay the extra gas, per the logic above it's still the correct math in spite of it wasting gas


    ## What happens if in the middle we have start again?
    Then the entire path is a uber path to start

    N -> A -> M

    Meaning that Start should have been N and not A

    ## NOTE: Worth checking this on Solidity, is uberPath or something, as it's not gas efficient


    ## TODO: What happens on a cross?

    A -> B
    A -> C
    A -> D
    A -> D -> B

    B -> A
    B -> C
    B -> D

    As sum of paths

    A -> D -> B -> A
    A -> D -> B -> C
    A -> D -> B -> D

    In reality

    A -> D -> B -> A
              B -> C
              B -> D
    

    A -> D
    D -> B

    B -> A
    B -> C
    B -> D

    D -> B ??? TODO: This is where problem arise


    ## NOTE: Minimal Problem Statement
    D -> B -> D

    ## RULE: We must revert if you claim the same pair / path twice

    ## What happens if something is a recursive sub path of something else
    ## What math would help?

    (B -> C)*

    B -> C
"""

## Vault / Token Notation | TokenData

"""
    For the purposes of this sim:

    A -> B -> B' -> C -> C'

    Where each of them will have
    {
        ## For each epoch each user. After a claim, increase current
        ## At beginning of new epoch, port over from prev epoch bal
        ## balances[epoch][user] = balances[epoch-1][user]
        balances[epoch][user]: 

        ## How many rewards available this epoch
        rewards[epoch][token]

        ## How many emissions available this epoch (emission = reward for holding vault)
        emissions[epoch]

        ## Sum of balances + rewards + emissions
        total_supply[epoch]: 
    }
"""

def get_token_total_supply(users, token_name):
    total_supply = 0

    for user in users:
        user_bal = user.getBalanceAtEpoch(token_name, 0)
        total_supply += user_bal

    return total_supply


class Token:
    def __init__(self, id, balances, rewards, emissions, total_supply, noise = []):
        self.balances = balances
        self.rewards = rewards
        self.emissions = emissions
        self.total_supply = total_supply
        self.id = id
        self.noise = noise


def create_tokens_from_sequence(seq, start_token, epoch_count, users, min_reward, reward_range, decimals, deterministic):
    temp_seq = deepcopy(seq)

    ## TODO: Potentially can extend sim to only have emissions / rewards if present in the claim sequence
    ## However we will always create emissions and rewards for each epoch as we assume:
    ## Token is either emititng or not
    ## Token is either reward or not
    ## All tokens always emit / reward for all epochs (even if values are different)
    ## Epoch length is the same for all

    rewards = []
    emissions = []

    while len(temp_seq) > 0:
        next: ClaimPair  = temp_seq.pop(0)

        ## Handle emissions and tokens
        if next.vault == next.token:
            ## This is an emission
            if next.token not in rewards:
                rewards.append(next.token)
        else:
            ## This is a reward
            if next.token not in emissions:
                emissions.append(next.token)

    ## Create Tokens which are rewards, if not
    tokens = {}

    tokens[start_token] = create_start(users)
    print("total_epochs", epoch_count)

    for token in rewards:
        tokens[token] = create_reward_token(token, epoch_count, min_reward, reward_range, decimals, deterministic, token in emissions)
    
    return tokens
        


def create_start(users):

    ## Start is always a token that is not a reward nor an emission

    balances = []
    rewards = [0]
    emissions = [0]

    ## Cumulative amount that increases by reward on each epoch
    ## 0 -> reward_0
    ## n > reward_n-1 + reward_n
    total_supply = []

    epoch_count = users[0].epochs
    user_count = len(users)


    for epoch in range(epoch_count):
        balances.append([])
        total_supply.append(0)
        for user in range(user_count):
            balances[epoch].append(0)


    for user in range(user_count):
        ## User Balance
        balance = users[user].getBalanceAtEpoch("a", 0)
        balances[0][user] = balance

        total_supply[0] += balance

        ## NOTE: Port over total supply
        ## We don't port over balances cause we don't use them
        for epoch in range(epoch_count):
            if epoch > 0:
                total_supply[epoch] = total_supply[epoch - 1]
    

    
    return Token("a", balances, rewards, emissions, total_supply)


def create_reward_token(name, epoch_count, min_reward, reward_range, decimals, deterministic, with_emission = True):
    ## Reward means no emissions
    ## Add the flip somewhere else

    print("Creating token", name, epoch_count)
    
    balances = [0]
    rewards = [0]
    emissions = [0]
    total_supply = [0]

    ## Balances that are entitled to emissions and not reward
    ## Can just be a single amount per epoch as you can imagine the vector or holders and sum it up to one user
    noise = [0]

    for epoch in range(epoch_count):
        balances.append([]) ## 0

        noise.append(0)
        rewards.append(0)
        emissions.append(0)
        total_supply.append(0)

    for epoch in range(epoch_count):
        ## Create reward always
        reward = (
            (int(random() * reward_range) + min_reward) * 10**decimals
            if not deterministic
            else min_reward * 10**decimals
        )
        rewards[epoch] = reward

        ## Port over Total Supply
        ## Also add noise and port it over for all epochs
        if(epoch > 0):
            total_supply[epoch] = total_supply[epoch - 1]
            noise[epoch] = noise[epoch - 1] ## Port over noise from prev as it's cumulative
        else:
            ## If epoch is 0 add the noise
            ## We port it over for math later
            noise_bal = (
                (int(random() * reward_range) + min_reward) * 10**decimals
                if not deterministic
                else min_reward * 10**decimals
            )
            noise[epoch] = noise_bal
            total_supply[epoch] += noise_bal


        total_supply[epoch] += reward

        if(with_emission):
            ## Emission and reward math is same, TODO: deal with it
            emission = (
                (int(random() * reward_range) + min_reward) * 10**decimals
                if not deterministic
                else min_reward * 10**decimals
            )
            emissions[epoch] = emission
            
            total_supply[epoch] += emission

    
    return Token(name, balances, rewards, emissions, total_supply, noise)


## ClaimPair Notation
"""
(Vault, Token)

isReward if Vault != Token

isEmission if Vault == Token

This allows us to write the whole claim loop as
do_claim(ClaimPair[], epochStart, epochEnd)

Which will call for i = epochStart; i < epochEnd
do_claim(Vs, ClaimPair[], epoch_i)

Which calls
for n = 0; n < claimPair.length
do_claim(Vs, claimPair_n, epoch_i)

Where Vs is the Virtual State of balances accrued
claimPair[] is the list of all claimPair, all pairs are unique at this time (no crossing)
TODO: Figure out Crossing

Uniqueness of claims
We can track it via claimed[epoch][vault][token]
Which we can sim in Python via
claimed = [keccak(epoch + vault + token)] where + is the string concatenation operator and keccak is SHA256
Verifying uniqueness of claim in python is trivial

Interestingly enough, for gas purposes it may be cheaper to use the same technique in Solidity and then Zero Out all arrays for balances, 
making claims cheaper by deleting your balance.

Downside is if you don't claim exhaustively in one go, you will lose a lot of value potentially

Upside is I think this eliminates one storage slot for all claims so that's pretty huge (20k per epoch)
"""


def get_random_user_start_balance():
    balance = (
        (int(random() * MIN_SHARES) + MIN_SHARES) * 10**SHARES_DECIMALS
        if not DETERMINISTIC
        else MIN_SHARES * 10**SHARES_DECIMALS
    )

    return balance


class ClaimPair:
    def __init__(self, vault, token, epoch):
        self.vault = vault
        self.token = token
        self.epoch = epoch

class UserBalances:
    """
        start_token
        tokens
        epochs

        Just use `getBalanceAtEpoch`
        Which also updates the balance from old epoch
    """
    def __init__(self, start_token, tokens, epochs):
        ## Create empty token balances
        empty_balance = []
        for epoch in range(epochs):
            empty_balance.append(0)
        
        start_token_balance = empty_balance.copy()
        start_token_balance[0] = get_random_user_start_balance()

        setattr(self, start_token, start_token_balance.copy())

        for token in tokens:
            setattr(self, token, empty_balance.copy())

        ## Limit of epochs, just for addBalanceAtEpoch
        self.epochs = epochs
    
    def getBalances(self, token_name):
        return getattr(self, token_name)
    
    def getBalanceAtEpoch(self, token_name, epoch):
        balances = getattr(self, token_name)

        ## Saves us having to port over balances
        ## If > 0 and if not last epoch
        ## NOTE: Assumes we always loop from 0 -> n stepwise, skipping one epoch = break the logic
        if(balances[epoch] == 0 and epoch > 0):
            balances[epoch] = balances[epoch - 1]
            setattr(self, token_name, balances.copy())
        
        return balances[epoch]
    
    def addBalanceAtEpoch(self, token_name, epoch, amount):
        if(epoch > self.epochs):
            return False
        
        ## Lookback + port over balance
        balanceAtEpoch = self.getBalanceAtEpoch(token_name, epoch)
        balanceAtEpoch += amount

        balances = getattr(self, token_name)
        balances[epoch] = balanceAtEpoch

        setattr(self, token_name, balances.copy())


def create_users(epoch_count, user_count, start_token, tokens):
    users = []
    for user in range(user_count):
        new_user = UserBalances(start_token, tokens, epoch_count)
        users.append(new_user)
    
    return users

    


## Validate claimSequence

"""
    Loop over the sequence

    Next.rewards[0][token] MUST be non-zero.

    In Solidity we won't be perfoming the check

    A subsequence zero epoch is acceptable, but first one needs to be non-zero
"""

def keccak(value):
    return sha256(value)


def create_claim_sequence(epoch_count, start: str):
    pairs = []

    ## TODO: Make this completely random
    """
        Generate Start Sequence
        Rest is: has_emissions
        Then a value to stop
        And a way to give a unique name for each token
        For now no crossing as I believe that will break the system
    """

    for epoch in range(epoch_count):
        ## A -> B
        pairs.append(ClaimPair(start, "b", epoch))

        ## B -> B'
        pairs.append(ClaimPair("b", "b", epoch))

        ## B -> C
        pairs.append(ClaimPair("b", "c", epoch))

        ## C -> C'
        pairs.append(ClaimPair("c", "c", epoch))

    return pairs
    

def is_valid_sequence(sequence: list, vault: str):
    pairs_already_done = []

    ## keccak(sequence.vault, sequence.token, sequence.epoch)

    ## Ensure we are starting with vault
    assert sequence[0].vault == vault

    while len(sequence) > 0:
        
        ## Reduces len so while ends
        entry: ClaimPair = sequence.pop(0)
        
        ## Get hash like we'd do in solidity via keccak
        string = (str(entry.epoch) + entry.vault + entry.token).encode("utf-8")
        hashed = keccak(string).hexdigest()

        if hashed in pairs_already_done:
            return False
        
        ## Append so if it repeats it's a dup
        pairs_already_done.append(hashed)


    return True




## Claim Math

"""
    ## From Claim proof
        For Each V ∈ Vs:
        Claim(V, n, i) ===
        {
            vi / Tvi * Ri; if V != R; Rewards Case
            vi / (Tvi - Ri); if V == R; Emissions Case
        }
"""

def get_reward(balance, total_supply, rewards):
    """
        Use it to receive A -> B type rewards
        Where A != B

        Returns (claimed, dust)
    """

    divisor = total_supply

    claimed = balance * rewards // divisor
    dust = balance * rewards % divisor

    return (claimed, dust)

def get_emission(balance, total_supply, emissions):
    """
        Given an (updated e.g already claimed reward) balance, claim the emissions for this epoch

        Use it to receive B -> B' type rewards
        Where B == B' they are the same token

        Returns (claimed, dust)
    """

    print("get_emission")
    print("balance", balance)
    print("total_supply", total_supply)
    print("emissions", emissions)

    ## Any older emission is assumed to be claimed
    ## Because we assume nothing from the future is in, we can just subtract the one from the current claim
    divisor = total_supply - emissions

    claimed = balance * emissions // divisor
    dust = balance * emissions % divisor

    print("claimed", claimed)
    return (claimed, dust)

## Fairness Check at end

"""
    User Deposited / TotalSupply = Expected %


    Recursive validation via:
    -> Expected %
    -> Vs realized %

    NOTE: Can do this because we prove that claiming every week vs once per year is equivalent
    ## As our divisor is not relative to the value
"""

def main():
    epoch_count = 3
    user_count = 3
    min_shares = MIN_SHARES
    shares_range = MIN_SHARES 
    decimals = SHARES_DECIMALS
    deterministic = True

    start_token = "a"
    seq = create_claim_sequence(epoch_count, start_token)
    ## NOTE: Tested to work
    assert is_valid_sequence(deepcopy(seq), start_token)



    ## Then use the claim sequence to loop over the tokens and claim them each epoch

    ## Then use the claim sequence to verify that the claimed is correct / appropriate

    users = create_users(epoch_count, user_count, start_token, ["b", "c"])

    ## Create users + tokens from the claim sequence
    ## Then get the total Supply
    tokens = create_tokens_from_sequence(seq, start_token, epoch_count, users, min_shares, shares_range, decimals, deterministic)

    ## Solution -> Make first token just like others
    ## It's not special, with the exception that it will never has self
    ## NOTE: Self emissions could be added and I don't think it would be an issue either

    print("len(seq)", len(seq))
    while len(seq) > 0:
        pair: ClaimPair = seq.pop(0)

        vault_name = pair.vault
        rewards_name = pair.token
        epoch = pair.epoch

        print("Pair", vault_name, rewards_name)

        total_rewards_token = 0
        total_emissions_token = 0

        has_claimed_noise = False

        for user in range(user_count):
            in_token = tokens[vault_name]
            out_token = tokens[rewards_name]

            if vault_name != rewards_name:
                ## Handle Reward
                (gained, dust) = get_reward(users[user].getBalanceAtEpoch(vault_name, epoch), in_token.total_supply[epoch], out_token.rewards[epoch])

                users[user].addBalanceAtEpoch(rewards_name, epoch, gained)
                
                total_rewards_token += gained

                ### === Bring the Noise === ###
                ## Always claim noise, once per pair per epoch, except on A as we know it has no noise by design
                if(out_token.noise[epoch] > 0 and not has_claimed_noise and vault_name != "a"):
                    has_claimed_noise = True

                    (gained_emission_from_noise, dust_emission_from_noise) = get_reward(in_token.noise[epoch], in_token.total_supply[epoch], out_token.rewards[epoch])
                    ## Update current for below (This will be used for new pair with noise)
                    out_token.noise[epoch] += gained_emission_from_noise

                    if epoch + 1 < epoch_count:
                        ## Port over old balance as well
                        out_token.noise[epoch + 1] = out_token.noise[epoch]
                    
                    total_rewards_token += gained_emission_from_noise

            else:
                (gained_emission, dust_emission) = get_emission(users[user].getBalanceAtEpoch(rewards_name, epoch), out_token.total_supply[epoch], out_token.emissions[epoch])

                ## Update user Balance for B with B'
                users[user].addBalanceAtEpoch(rewards_name, epoch, gained_emission)

                total_emissions_token += gained_emission

                ### === Bring the Noise === ###
                ## Always claim noise, once per pair per epoch
                if(out_token.noise[epoch] > 0 and not has_claimed_noise):
                    has_claimed_noise = True
                    print("Claim from noise")
                    print("Before noise already claimed ", total_emissions_token / out_token.emissions[epoch])

                    (gained_emission_from_noise, dust_emission_from_noise) = get_emission(out_token.noise[epoch], out_token.total_supply[epoch], out_token.emissions[epoch])
                    ## Update current for below (This will be used for new pair with noise)
                    out_token.noise[epoch] += gained_emission_from_noise

                    if epoch + 1 < epoch_count:
                        ## Port over old balance as well
                        print("")
                        out_token.noise[epoch + 1] = out_token.noise[epoch]
                    
                    total_emissions_token += gained_emission_from_noise




        ## Fairness check for epoch
        print("Fairness / Distribution Ratio for Epoch and TokenPair", epoch, vault_name, rewards_name)
        if vault_name != rewards_name:
            rewards_ratio = total_rewards_token / out_token.rewards[epoch]
            print(rewards_ratio)
            assert rewards_ratio == 1
        else:
            emissions_ratio = total_emissions_token / out_token.emissions[epoch]
            print(emissions_ratio)
            assert emissions_ratio == 1

    return True