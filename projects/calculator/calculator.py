def add(num1: float, num2: float) -> float:
    """Adds two numbers."""
    return num1 + num2

def subtract(num1: float, num2: float) -> float:
    """Subtracts the second number from the first."""
    return num1 - num2

def multiply(num1: float, num2: float) -> float:
    """Multiplies two numbers."""
    return num1 * num2

def divide(num1: float, num2: float) -> float:
    """Divides the first number by the second.

    Raises:
        ValueError: if division by zero is attempted.
    """
    if num2 == 0:
        raise ValueError("Cannot divide by zero.")
    return num1 / num2
