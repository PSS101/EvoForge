import csv
import json
import os

class SimpleConverter:
    """A utility class to parse CSV files and export them to JSON format."""

    def __init__(self):
        pass

    def read_csv(self, file_path: str) -> str:
        """Reads a CSV file and returns its content as a formatted JSON string.

        Args:
            file_path: Path to the target CSV file.

        Returns:
            A formatted JSON string representing the CSV rows.

        Raises:
            FileNotFoundError: If the CSV file does not exist.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        data = []
        with open(file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Clean up values (strip whitespace and skip None values)
                clean_row = {
                    key.strip(): value.strip() if value else ""
                    for key, value in row.items()
                    if key is not None
                }
                data.append(clean_row)

        return json.dumps(data, indent=4)
