import sys
from operations import perform_operation
from calculator import get_history

def main():
    print("Simple Calculator Command-Line Utility")
    print("Type 'h' to view history, 'q' to quit.")
    while True:
        try:
            choice = input("Enter operation (+, -, *, /, %): ").strip()
            if choice.lower() == 'q':
                break
            if choice.lower() == 'h':
                history = get_history()
                if not history:
                    print("No operations performed yet.")
                else:
                    print("Operation History:")
                    for entry in history:
                        print(f"  {entry}")
                continue
            if choice in ['+', '-', '*', '/', '%']:
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
