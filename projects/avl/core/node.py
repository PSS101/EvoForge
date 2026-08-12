"""
avl.core.node

Defines the Node class used by the AVLTree implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Node:
    """
    Represents a node in an AVL tree.

    Attributes
    ----------
    key : Any
        Comparable value used for ordering.
    value : Any, optional
        Payload stored with the key. Defaults to None.
    left : Optional[Node], optional
        Left child (subtree of keys < self.key). Defaults to None.
    right : Optional[Node], optional
        Right child (subtree of keys > self.key). Defaults to None.
    height : int, optional
        Height of the node in the tree, used for balancing. Defaults to 1.

    Methods
    -------
    update_height()
        Recalculate the node's height based on its children.
    balance_factor() -> int
        Return left.height - right.height.
    """

    key: Any
    value: Any = None
    left: Optional["Node"] = field(default=None, repr=False)
    right: Optional["Node"] = field(default=None, repr=False)
    height: int = field(default=1, init=False)

    def update_height(self) -> None:
        """Recalculate the node's height based on its children."""
        left_h = self.left.height if self.left else 0
        right_h = self.right.height if self.right else 0
        self.height = max(left_h, right_h) + 1

    def balance_factor(self) -> int:
        """Return the difference between the heights of left and right subtrees."""
        left_h = self.left.height if self.left else 0
        right_h = self.right.height if self.right else 0
        return left_h - right_h
