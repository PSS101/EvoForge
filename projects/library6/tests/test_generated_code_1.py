import pytest

def test_add(a, b):
    assert a + b == 3

def test_subtract(a, b):
    assert a - b == 1

def test_multiply(a, b):
    assert a * b == 6

def test_divide(a, b):
    assert a / b == 2.0

def test_square(a):
    assert a ** 2 == 4

def test_prime(a):
    assert a % 2 != 0

def test_even(a):
    assert a % 2 == 0

def test_odd(a):
    assert a % 2 != 0
