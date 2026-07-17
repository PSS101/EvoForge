# Simple Interest Calculator

A professional, desktop-based GUI application developed in Python to compute simple interest calculations, validate input values, and generate comprehensive reports in both TXT and PDF formats.

## Features
- **Interactive GUI**: Sleek Tkinter user interface with real-time feedback and validation.
- **Input Validation**: Prevents computation errors by ensuring values are numeric and non-negative.
- **Detailed Math**: Precision math computing Simple Interest based on Principal ($), Interest Rate (%), and Time Period (Years).
- **PDF Report Generation**: Exports beautifully formatted PDF reports including summaries of input data and computed interest.
- **TXT Report Generation**: Saves calculations to local text files.

## Directory Structure
```text
projects/simple_interest/
├── simple_interest.py     # Main application and GUI script
├── README.md              # Project documentation
├── User_Manual.md         # Detailed guide for end-users
└── tests/
    └── test_simple_interest.py  # Pytest suite
```

## Setup & Running
The application supports multiple execution modes:

### 1. Graphical User Interface (GUI) Mode
Launches a visual interface (Tkinter window) for inputting values:
```bash
python simple_interest.py
```

### 2. Interactive CLI Mode
Prompts you for inputs step-by-step in the terminal (runs completely offline):
```bash
python simple_interest.py --cli
```

### 3. CLI Argument Mode
Directly computes interest using command-line arguments:
```bash
python simple_interest.py -p 1000 -r 5 -t 2
```

To automatically save TXT and PDF reports:
```bash
python simple_interest.py -p 1000 -r 5 -t 2 -o my_report
```

## Running Tests
To execute the unit tests:
```bash
pytest
```
