## System Architecture Overview

The system is designed with a clean architecture approach, separating user interface, business calculation logic, and file storage operations. It consists of three main modules:

1. **UI Module**: Handles Tkinter graphical user interface interactions, input gathering, validation, and calling calculations/storage.
2. **Math Module**: Performs mathematical simple interest calculations.
3. **Storage Module**: Manages file storage, outputting reports as TXT or PDF formats.

### Class Specifications

#### 1. UI Module
- **Class Name**: `CalculatorUI`
- **Methods**:
  - `__init__(root)`: Sets up the main window, labels, entry fields, and buttons.
  - `_build_ui()`: Creates and packs Tkinter widgets.
  - `perform_calculation()`: Retrieves inputs, validates them, invokes `CalculatorMath`, updates output labels, and enables action buttons.
  - `save_txt()`: Prompts user for location and calls `DataStorage.store_result_text` to save text report.
  - `save_pdf()`: Prompts user for location and calls `DataStorage.store_result_pdf` to save PDF report.

#### 2. Math Module
- **Class Name**: `CalculatorMath`
- **Methods**:
  - `calculate_simple_interest(principal, rate, time)`: Computes interest using formula `(P * R * T) / 100`. Raises `ValueError` for negative values.

#### 3. Storage Module
- **Class Name**: `DataStorage`
- **Methods**:
  - `store_result_text(file_path, principal, rate, time, interest)`: Writes a formatted text summary report of the calculation to the filesystem.
  - `store_result_pdf(file_path, principal, rate, time, interest)`: Generates a high-quality PDF report using PyMuPDF containing styled calculations and summaries.