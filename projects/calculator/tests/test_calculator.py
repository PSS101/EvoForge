import unittest
from calculator import add, subtract, multiply, divide
from operations import perform_operation

class TestCalculator(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(add(5, 3), 8)
        self.assertEqual(add(-1, 1), 0)

    def test_subtraction(self):
        self.assertEqual(subtract(5, 3), 2)
        self.assertEqual(subtract(3, 5), -2)

    def test_multiplication(self):
        self.assertEqual(multiply(5, 3), 15)
        self.assertEqual(multiply(5, 0), 0)

    def test_division(self):
        self.assertEqual(divide(6, 3), 2.0)
        with self.assertRaises(ValueError):
            divide(5, 0)

    def test_perform_operation(self):
        self.assertEqual(perform_operation('+', 2, 3), 5)
        self.assertEqual(perform_operation('-', 5, 2), 3)
        self.assertEqual(perform_operation('*', 4, 3), 12)
        self.assertEqual(perform_operation('/', 8, 2), 4.0)

if __name__ == '__main__':
    unittest.main()
