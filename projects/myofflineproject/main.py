import argparse
import sys
from simple_converter import SimpleConverter

def main():
    parser = argparse.ArgumentParser(description="Convert CSV file to JSON format.")
    parser.add_argument("csv_file", help="Path to the input CSV file")
    parser.add_argument("-o", "--output", help="Path to save the output JSON file (optional)")

    args = parser.parse_args()

    converter = SimpleConverter()
    try:
        json_output = converter.read_csv(args.csv_file)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_output)
            print(f"Successfully converted and saved to: {args.output}")
        else:
            print(json_output)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
