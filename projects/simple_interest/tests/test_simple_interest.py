import os
import unittest
import tempfile
from simple_interest import CalculatorMath, DataStorage

class TestSimpleInterest(unittest.TestCase):

    def test_calculate_simple_interest(self):
        # Case 1: Standard positive values
        # P = 1000, R = 5%, T = 2 years
        # Interest should be 1000 * 5 * 2 / 100 = 100
        interest = CalculatorMath.calculate_simple_interest(1000, 5, 2)
        self.assertAlmostEqual(interest, 100.0)

        # Case 2: Zero values
        self.assertAlmostEqual(CalculatorMath.calculate_simple_interest(0, 5, 2), 0.0)
        self.assertAlmostEqual(CalculatorMath.calculate_simple_interest(1000, 0, 2), 0.0)
        self.assertAlmostEqual(CalculatorMath.calculate_simple_interest(1000, 5, 0), 0.0)

    def test_invalid_input(self):
        # Calculation should raise ValueError for negative numbers
        with self.assertRaises(ValueError):
            CalculatorMath.calculate_simple_interest(-1000, 5, 2)
        with self.assertRaises(ValueError):
            CalculatorMath.calculate_simple_interest(1000, -5, 2)
        with self.assertRaises(ValueError):
            CalculatorMath.calculate_simple_interest(1000, 5, -2)

    def test_data_storage_text(self):
        # Create a temp file to store output
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_report.txt")
            DataStorage.store_result_text(temp_file, 1000.0, 5.0, 2.0, 100.0)
            
            # Verify file creation and contents
            self.assertTrue(os.path.exists(temp_file))
            with open(temp_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("Principal Amount: 1000.00", content)
                self.assertIn("Annual Interest Rate: 5.00%", content)
                self.assertIn("Time Period: 2.00 years", content)
                self.assertIn("Calculated Simple Interest: 100.00", content)

    def test_data_storage_pdf(self):
        # Create a temp file to store PDF
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_report.pdf")
            DataStorage.store_result_pdf(temp_file, 1000.0, 5.0, 2.0, 100.0)
            
            # Verify PDF file exists and is non-empty
            self.assertTrue(os.path.exists(temp_file))
            self.assertGreater(os.path.getsize(temp_file), 0)

if __name__ == '__main__':
    unittest.main()