# User Manual: Simple Interest Calculator

## Introduction
The Simple Interest Calculator is a user-friendly application designed to calculate simple interest based on user inputs. Users can also export reports as PDF and TXT files.

## Getting Started

### 1. Launching the App
Run the following command from the project root:
```bash
python simple_interest.py
```

### 2. Interface Elements
- **Principal Amount ($)**: Input the initial amount of money.
- **Rate of Interest (%)**: Input the annual interest rate (e.g., 5 for 5%).
- **Time Period (Years)**: Input the duration of interest accumulation.
- **Calculate Interest Button**: Performs the calculation.
- **Result Summary Frame**: Displays the interest amount and final total.
- **Save TXT / Save PDF Buttons**: Export functions (enabled after a successful calculation).

## Steps to Compute Interest
1. Enter numeric values in the three fields: Principal, Rate, and Time.
2. Click **Calculate Interest**.
3. View the computed interest and total amount.
4. Export the calculation to a TXT or PDF file using the save buttons.

## Troubleshooting
- **Numeric Error**: If any inputs are non-numeric, a popup will notify you to enter valid numbers.
- **Negative Value Error**: The calculator checks for negative values and displays an error box.
- **Required Fields**: Ensure all fields are filled before clicking calculate.
