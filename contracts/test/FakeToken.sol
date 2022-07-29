// SPDX-License-Identifier: MIT

pragma solidity 0.8.10;
pragma experimental ABIEncoderV2;

import {ERC20} from "@oz/token/ERC20/ERC20.sol";

contract FakeToken is ERC20 {
    constructor() ERC20("Test", "TEST") {}

    function mint(address recipient, uint256 shares) external {
        _mint(recipient, shares);
    }
}
