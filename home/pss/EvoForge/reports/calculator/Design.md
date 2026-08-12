# System Architecture Overview

The calculator system is designed using a clean architecture approach, which separates concerns into distinct layers to ensure scalability and maintainability.

## Layers

1. **User Interface (UI) Layer**
   - Handles user interactions and displays results.
2. **Application Layer**
   - Contains the business logic for performing arithmetic operations.
3. **Data Access Layer**
   - Manages data storage, though in this case, it's minimal as we don't maintain a history of operations.

## Module and Class Specifications

### 1. User Interface (UI) Layer

- **Class Name**: CalculatorUI
- **Methods**:
  - `displayResult(result: string)`
  - `getUserInput(): string`

### 2. Application Layer

- **Class Name**: CalculatorApp
- **Methods**:
  - `add(a: number, b: number): number`
  - `subtract(a: number, b: number): number`
  - `multiply(a: number, b: number): number`
  - `divide(a: number, b: number): number`
  - `modulo(a: number, b: number): number`

### 3. Data Access Layer

- **Class Name**: CalculatorDataAccess
- **Methods**:
  - `saveOperation(operation: string)`: Not implemented as history is removed.
  - `getOperationsHistory()`: Not implemented as history is removed.

## Structural & Sequence Flow

```mermaid
graph TD
    UI[User Interface] -->|getUserInput()| App[Application]
    App -->|add, subtract, multiply, divide, modulo| Data[Data Access]
    Data -->|saveOperation, getOperationsHistory| UI
```