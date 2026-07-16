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
To launch the application:
```bash
python simple_interest.py
```

## Running Tests
To execute the unit tests:
```bash
pytest
```
