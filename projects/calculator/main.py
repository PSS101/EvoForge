import sys
from operations import perform_operation

def main():
    print("Simple Calculator Command-Line Utility")
    print("Type 'q' to quit.")
    while True:
        try:
            choice = input("Enter operation (+, -, *, /): ").strip()
            if choice.lower() == 'q':
                break
            if choice in ['+', '-', '*', '/']:
                num_input = input("Enter two numbers separated by space: ").split()
                if len(num_input) != 2:
                    print("Error: Please enter exactly two numbers.")
                    continue
                num1, num2 = map(float, num_input)
                result = perform_operation(choice, num1, num2)
                print(f"{num1} {choice} {num2} = {result}")
            else:
                print("Invalid operation. Please try again.")
        except ValueError as ve:
            print(f"Error: {ve}")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

if __name__ == "__main__":
    main()
