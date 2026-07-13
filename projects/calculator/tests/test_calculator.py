import unittest
from calculator import Calculator, add, subtract, multiply, divide, modulo, get_history
from operations import perform_operation

class TestCalculator(unittest.TestCase):
    def test_addition(self):
        calc = Calculator()
        self.assertEqual(calc.add(2, 3), 5)
        self.assertEqual(calc.add(-1, -1), -2)
        
    def test_subtraction(self):
        calc = Calculator()
        self.assertEqual(calc.subtract(4, 2), 2)
        self.assertEqual(calc.subtract(7, 3), 4)
        
    def test_multiplication(self):
        calc = Calculator()
        self.assertEqual(calc.multiply(5, 6), 30)
        self.assertEqual(calc.multiply(-1, -1), 1)
        
    def test_division(self):
        calc = Calculator()
        self.assertEqual(calc.divide(8, 2), 4)
        with self.assertRaises(ValueError):
            calc.divide(8, 0)
            
    def test_modulo(self):
        calc = Calculator()
        self.assertEqual(calc.modulo(5, 2), 1)
        with self.assertRaises(ValueError):
            calc.modulo(5, 0)

    def test_history(self):
        calc = Calculator()
        calc.add(2, 3)
        calc.subtract(4, 2)
        history = calc.get_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0], "2 + 3 = 5")
        self.assertEqual(history[1], "4 - 2 = 2")

    def test_functional_wrappers(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(subtract(4, 2), 2)
        self.assertEqual(multiply(5, 6), 30)
        self.assertEqual(divide(8, 2), 4.0)
        self.assertEqual(modulo(5, 2), 1.0)

    def test_perform_operation(self):
        self.assertEqual(perform_operation('+', 2, 3), 5)
        self.assertEqual(perform_operation('-', 4, 2), 2)
        self.assertEqual(perform_operation('*', 5, 6), 30)
        self.assertEqual(perform_operation('/', 8, 2), 4.0)
        self.assertEqual(perform_operation('%', 5, 2), 1.0)