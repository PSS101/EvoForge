import pytest

from utils import input_int, input_str

def test_input_int_valid():
    assert input_int("Enter an integer: ") == 42

def test_input_int_invalid():
    with pytest.raises(ValueError):
        input_int("Enter an integer: ")

def test_input_str_valid():
    assert input_str("Enter a string: ") == "hello"

def test_input_str_empty():
    assert input_str("Enter a string: ") == ""
