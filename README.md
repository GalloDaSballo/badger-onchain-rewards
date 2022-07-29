# RewardsManager - NOT AUDITED

## Video Introduction
https://youtu.be/QoU96EWMJio

## Notion / Overview
https://mint-salesman-909.notion.site/Badger-Rewards-Intro-58ce9b2026dc4c39a180a1c3bac47477

## Miro Architecture
https://miro.com/app/board/uXjVOQU-Z8A=/?invite_link_id=120636167771

Allows to vest rewards based on time spent

Use case is deposits in a vault so that Badger Dao can move to fully onChain emissions
Code is generalized enough to allow to handle an unknown amount of rewards for an unknown amount of types of tokens



## Vulnerabilities, and reports

Commit: fb02070c919dd19f7f3ba5e2b2cfe9b4e394c1aa
Report: https://docs.google.com/document/d/1bO2XfwQ60wQWePihgJu6UsukimI5ygTmC1rBTMGGNp0/edit
Status: Vulnerabilities have been mitigated


Commit: 62a728
Report: https://www.hacknote.co/17c261f7d8fWbdml/17f3efe98b4HW20Y
Status: Vulnerabilities have been mitigated


Commit: 921ffa1edb42
Report: https://docs.google.com/document/d/1l3sWKgKrp29syOj3_dX7tCozVtmpwYOIykBj1A-unVU/edit#
Status: Vulnerabilities have been mitigated

Additional Fixes:
Vault tokens being sent to this contract causes unfairness in claiming tokens as the rewards contract will receive a portion of the rewards

Solution:
Accrue the contract and calculate the totalSupply - thisContract Supply

Status: Mitigated


## Potential Attack Vectors to Explore
- Can you cause the Points to be greater than TotalPoints, allowing to extract more than the rewards for one epoch for one vault?


## Formatting
### Install dependencies

```yarn```

### Run Formatting Tool

```
yarn format
```


# Notices

## Provably unfair math

The first release of this contract tries to handle self-emitting vaults (vaults that add themselves as rewards to depositors), however the math is provably unfair towards late claimers.

Make sure self-emitting vaults are not used (just auto-compound bruh), and if they are, make sure to claim every week.

## Week is not a week

I kind of gave up on tracking a week across leap years, either way, the contract uses EPOCHS as: `Set Amounts of time`, as such, while the "claiming day" will end up switching every 4 years, the time in between claims will be consistent (as it's tracked in seconds).

For those reasons, please don't send reports about the math not being once per week.

## Epoch time

In a system that is lower yield, higher gas, more predictable (think fixed yield), you could re-use the contract with a SECONDS_PER_EPOCH set to a month or even more.

Negatives:
- Can claim less often

Positives:
- Each claim is "bigger" and as such the fixed cost of gas is less noticeable