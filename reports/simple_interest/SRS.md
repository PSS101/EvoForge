# Software Requirements Specification (SRS)

## Functional Requirements

- [UNCHANGED] The system shall provide a graphical user interface (GUI) that allows users to input principal amount, time period in years, and rate of interest. 
- [NEW] The system shall store the calculated simple interest value as an output file for future reference or use by another application.
- [REMOVED] The system shall validate user inputs to ensure they are within acceptable ranges (e.g., non-negative numbers).
- [UNCHANGED] The system shall display a clear and concise error message if any input is invalid, preventing the calculation from proceeding further.
- [NEW] The system shall provide an option for users to save their calculations as a PDF file for easy sharing or printing.
- [UNCHANGED] The system shall calculate simple interest using the formula: Simple Interest = Principal × Rate of Interest × Time Period in Years
- [REMOVED] The system shall generate a detailed report that includes all input values and calculated results, which can be further analyzed by users.

## Non-functional Requirements

- [UNCHANGED] The system shall ensure data integrity.
- [NEW] The system shall support concurrent access from multiple users without conflicts.
- [REMOVED] The system shall provide real-time updates to the user interface.