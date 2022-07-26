// SPDX-License-Identifier: MIT

pragma solidity 0.8.10;
pragma experimental ABIEncoderV2;

import {ERC20} from "@oz/token/ERC20/ERC20.sol";
import {SafeERC20} from "@oz/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@oz/security/ReentrancyGuard.sol";

interface IRewardsManager {
    function notifyTransfer(
        address,
        address,
        uint256
    ) external;
}

contract TestVault is ERC20, ReentrancyGuard {
    using SafeERC20 for ERC20;

    ERC20 public immutable token;
    IRewardsManager public immutable badgerTree;

    constructor(ERC20 _token, IRewardsManager _badgerTree)
        ERC20("Test", "TEST")
    {
        token = _token;
        badgerTree = _badgerTree;
    }

    /// === Vault / Tree Integration === ///
    function _transfer(
        address from,
        address to,
        uint256 amount
    ) internal override {
        super._transfer(from, to, amount);

        _onTransfer(from, to, amount);
    }

    /// @dev Hook to notify a transfer to the BadgerTree
    function _onTransfer(
        address from,
        address to,
        uint256 amount
    ) internal virtual {
        badgerTree.notifyTransfer(from, to, amount);
    }

    /// @dev Overridden _mint implementation to also trigger the hook to call the badgerTree
    function _mint(address recipient, uint256 shares) internal override {
        super._mint(recipient, shares);
        _onMint(recipient, shares);
    }

    /// @dev Hook to notify a Mint to the BadgerTree
    function _onMint(address to, uint256 amount) internal virtual {
        badgerTree.notifyTransfer(address(0), to, amount);
    }

    /// @dev Overridden _burn implementation to also trigger the hook to call the badgerTree
    function _burn(address from, uint256 shares) internal override {
        super._burn(from, shares);
        _onBurn(from, shares);
    }

    /// @dev Hook to notify a Burn to the BadgerTree
    function _onBurn(address from, uint256 amount) internal virtual {
        badgerTree.notifyTransfer(from, address(0), amount);
    }

    /// === Basic Mock Functionality === ///
    function deposit(uint256 amount) external nonReentrant {
        // Transfer token
        token.safeTransferFrom(msg.sender, address(this), amount);

        // Mint amount
        _mint(msg.sender, amount);
    }

    function withdraw(uint256 amount) external nonReentrant {
        // Burn Shares
        _burn(msg.sender, amount);

        // Transfer Amount
        token.safeTransfer(msg.sender, amount);
    }
}
