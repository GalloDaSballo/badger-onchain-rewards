# RewardsManager - NOT AUDITED - WIP - USE AT OWN RISK - UNDISCLOSED VULNERABILITIES!!!! DO NOT USE!!!
DO NOT USE IN PROD, there are known vulnerabilities!!!!

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