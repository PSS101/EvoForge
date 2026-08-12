import pytest

# Import the Node class from the project source code.
from avl.core.node import Node


def test_initialization():
    """Node should be created with correct defaults."""
    n = Node(key=10)
    assert n.key == 10
    assert n.value is None
    assert n.left is None
    assert n.right is None
    # Height is set to 1 by default (init=False triggers the field default).
    assert n.height == 1


def test_node_value_storage():
    """Node should store an arbitrary payload."""
    payload = {"data": 123}
    n = Node(key="a", value=payload)
    assert n.value == payload
    assert n.key == "a"


def test_update_height_no_children():
    """Height remains 1 when there are no children."""
    n = Node(key=5)
    n.update_height()
    assert n.height == 1


def test_update_height_left_child():
    """Height and balance factor with only a left child."""
    left = Node(key=3)
    parent = Node(key=4, left=left)
    # Children already have height 1.
    parent.update_height()
    assert parent.height == 2
    assert parent.balance_factor() == 1


def test_update_height_right_child():
    """Height and balance factor with only a right child."""
    right = Node(key=6)
    parent = Node(key=5, right=right)
    parent.update_height()
    assert parent.height == 2
    assert parent.balance_factor() == -1


def test_update_height_both_children():
    """Height and balance factor when both children exist."""
    left = Node(key=3)
    right = Node(key=7)
    parent = Node(key=5, left=left, right=right)
    parent.update_height()
    assert parent.height == 2
    assert parent.balance_factor() == 0


def test_balance_factor_complex_tree():
    """Test balance factor on a deeper tree."""
    # Build a small tree: root with left child that has its own left child.
    grandchild = Node(key=1)
    left_child = Node(key=3, left=grandchild)
    right_child = Node(key=5)

    root = Node(key=4, left=left_child, right=right_child)

    # Update heights bottom‑up to mimic real AVL behaviour.
    grandchild.update_height()
    left_child.update_height()
    right_child.update_height()
    root.update_height()

    assert root.height == 3
    assert root.balance_factor() == 1


def test_update_height_invalid_left():
    """update_height should raise AttributeError if left child is not a Node."""
    n = Node(key=10)
    n.left = 123  # non‑Node object
    with pytest.raises(AttributeError):
        n.update_height()


def test_update_height_invalid_right():
    """update_height should raise AttributeError if right child is not a Node."""
    n = Node(key=10)
    n.right = "not a node"
    with pytest.raises(AttributeError):
        n.update_height()
