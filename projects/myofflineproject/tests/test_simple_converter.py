import unittest
import os
import json
from simple_converter import SimpleConverter

class TestSimpleConverter(unittest.TestCase):
    def setUp(self):
        self.test_csv = 'test_sample.csv'
        with open(self.test_csv, 'w', encoding='utf-8') as f:
            f.write("name,age\nJohn,30\nAlice,25\n")
        self.converter = SimpleConverter()

    def tearDown(self):
        if os.path.exists(self.test_csv):
            os.remove(self.test_csv)

    def test_read_csv(self):
        json_output = self.converter.read_csv(self.test_csv)
        data = json.loads(json_output)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'John')
        self.assertEqual(data[0]['age'], '30')

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.converter.read_csv('non_existent.csv')

if __name__ == '__main__':
    unittest.main()