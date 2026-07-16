# This script modifies the original code in library9/src/MyClass.
def modify_class(instance):
    """Increases the value of X by 2."""
    x = instance.X + 2
    return x

def my_function():
    """Prints a message to the console."""
    print("Hello from the function!")

# Example Usage
if __name__ == '__main__':
     my_object = MyClass()
     modified_object = modify_class(my_object)
     print(modified_object)
     my_function()
