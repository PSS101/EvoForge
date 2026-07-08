from calculator import add, subtract, multiply, divide

def perform_operation(operation: str, num1: float, num2: float) -> float:
    """Delegates arithmetic choices to the math core logic."""
    if operation == '+':
        return add(num1, num2)
    elif operation == '-':
        return subtract(num1, num2)
    elif operation == '*':
        return multiply(num1, num2)
    elif operation == '/':
        return divide(num1, num2)
    else:
        raise ValueError(f"Unknown operation: {operation}")
