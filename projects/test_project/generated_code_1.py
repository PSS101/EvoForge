def calculate_average(numbers):
    """Calculates the average of a list of numbers."""
    if len(numbers) > 0:
        total = sum(numbers)
        return total / len(numbers)
    else:
       return 0

def main():
    numbers = [1, 2, 3, 4, 5]
    average_value = calculate_average(numbers)
    print(f"The average of {numbers} is: {average_value}")

if __name__ == "__main__":
    calculate_average(numbers)
