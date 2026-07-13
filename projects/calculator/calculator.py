class Calculator:
    def __init__(self):
        self.history = []

    def add(self, num1: float, num2: float) -> float:
        """Adds two numbers."""
        res = num1 + num2
        self.history.append(f"{num1} + {num2} = {res}")
        return res

    def subtract(self, num1: float, num2: float) -> float:
        """Subtracts the second number from the first."""
        res = num1 - num2
        self.history.append(f"{num1} - {num2} = {res}")
        return res

    def multiply(self, num1: float, num2: float) -> float:
        """Multiplies two numbers."""
        res = num1 * num2
        self.history.append(f"{num1} * {num2} = {res}")
        return res

    def divide(self, num1: float, num2: float) -> float:
        """Divides the first number by the second.

        Raises:
            ValueError: if division by zero is attempted.
        """
        if num2 == 0:
            raise ValueError("Cannot divide by zero.")
        res = num1 / num2
        self.history.append(f"{num1} / {num2} = {res}")
        return res

    def modulo(self, num1: float, num2: float) -> float:
        """Calculates the remainder of dividing the first number by the second.

        Raises:
            ValueError: if division by zero is attempted.
        """
        if num2 == 0:
            raise ValueError("Cannot divide by zero.")
        res = num1 % num2
        self.history.append(f"{num1} % {num2} = {res}")
        return res

    def get_history(self):
        """Returns the list of recorded operations."""
        return self.history

# Shared global instance for functional interface compatibility
_shared_calculator = Calculator()

def add(num1: float, num2: float) -> float:
    return _shared_calculator.add(num1, num2)

def subtract(num1: float, num2: float) -> float:
    return _shared_calculator.subtract(num1, num2)

def multiply(num1: float, num2: float) -> float:
    return _shared_calculator.multiply(num1, num2)

def divide(num1: float, num2: float) -> float:
    return _shared_calculator.divide(num1, num2)

def modulo(num1: float, num2: float) -> float:
    return _shared_calculator.modulo(num1, num2)

def get_history():
    return _shared_calculator.get_history()
