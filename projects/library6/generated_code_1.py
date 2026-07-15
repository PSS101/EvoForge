def calculate_average(numbers):
    """Calculates the average of a list of numbers."""
    if not numbers:
        return 0
    total = sum(numbers)
    average = total / len(numbers)
    return average

# Example usage (for testing - not part of the core logic)
# print(calculate_average([1, 2, 3, 4, 5]))
