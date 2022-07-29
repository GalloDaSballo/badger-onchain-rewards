// SPDX-License-Identifier: MIT

pragma solidity 0.8.10;
pragma experimental ABIEncoderV2;

import {ERC20} from "@oz/token/ERC20/ERC20.sol";

contract FakeFeeOnTransferToken is ERC20 {
    address public constant taxTank =
        0xdeaDDeADDEaDdeaDdEAddEADDEAdDeadDEADDEaD;

    constructor() ERC20("TestFeeOnTransfer", "TEST-FOT") {}

    function mint(address recipient, uint256 shares) external {
        _mint(recipient, shares);
    }

    function transferFrom(
        address from,
        address to,
        uint256 amount
    ) public override returns (bool) {
        address spender = _msgSender();
        _spendAllowance(from, spender, amount);

        uint256 _tax = _getTax(amount);
        _transfer(from, taxTank, _tax);

        _transfer(from, to, (amount - _tax));
        return true;
    }

    function transfer(address to, uint256 amount)
        public
        override
        returns (bool)
    {
        address owner = _msgSender();

        uint256 _tax = _getTax(amount);
        _transfer(owner, taxTank, _tax);

        _transfer(owner, to, (amount - _tax));
        return true;
    }

    function _getTax(uint256 amount) internal returns (uint256) {
        return (amount * 1000) / 10000;
    }
}
