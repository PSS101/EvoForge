import sys
from operations import perform_operation
from calculator import get_history

def main():
    print("Simple Calculator Command-Line Utility")
    print("Type 'h' to view history, 'q' to quit.")
    print("Operations: +, -, *, /, %, s (sqrt)")
    while True:
        try:
            choice = input("Enter operation (+, -, *, /, %, s): ").strip()
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
            elif choice == 's':
                num_input = input("Enter one number: ").strip()
                try:
                    num = float(num_input)
                except ValueError:
                    print("Error: Please enter a valid number.")
                    continue
                result = perform_operation(choice, num, None)
                print(f"sqrt({num}) = {result}")
            else:
                print("Invalid operation. Please try again.")
        except ValueError as ve:
            print(f"Error: {ve}")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

if __name__ == "__main__":
    main()
