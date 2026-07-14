from calculator import add, subtract, multiply, divide, modulo, sqrt

def perform_operation(operation: str, num1: float, num2: float = None) -> float:
    """Delegates arithmetic choices to the math core logic.

    For unary operations like sqrt ('s'), num2 may be None.
    """
    if operation == '+':
        return add(num1, num2)
    elif operation == '-':
        return subtract(num1, num2)
    elif operation == '*':
        return multiply(num1, num2)
    elif operation == '/':
        return divide(num1, num2)
    elif operation == '%':
        return modulo(num1, num2)
    elif operation == 's':
        # sqrt is unary; ignore num2
        return sqrt(num1)
    else:
        raise ValueError(f"Unknown operation: {operation}")