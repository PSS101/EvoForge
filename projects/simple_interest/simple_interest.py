import os
import sys
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
import fitz  # PyMuPDF

class CalculatorMath:
    @staticmethod
    def calculate_simple_interest(principal, rate, time):
        """Calculates simple interest using formula: SI = P * R * T / 100"""
        if principal < 0 or rate < 0 or time < 0:
            raise ValueError("All inputs must be non-negative.")
        return (principal * rate * time) / 100.0

class DataStorage:
    @staticmethod
    def store_result_text(file_path, principal, rate, time, interest):
        """Stores the calculation results to a text file."""
        total = principal + interest
        content = (
            f"=== Simple Interest Calculation Report ===\n"
            f"Principal Amount: {principal:.2f}\n"
            f"Annual Interest Rate: {rate:.2f}%\n"
            f"Time Period: {time:.2f} years\n"
            f"-----------------------------------------\n"
            f"Calculated Simple Interest: {interest:.2f}\n"
            f"Total Amount (Principal + Interest): {total:.2f}\n"
            f"=========================================\n"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def store_result_pdf(file_path, principal, rate, time, interest):
        """Generates a PDF report using PyMuPDF (fitz)."""
        total = principal + interest
        doc = fitz.open()
        page = doc.new_page()
        
        # Define layout coordinates
        title_rect = fitz.Rect(50, 50, 550, 100)
        content_rect = fitz.Rect(50, 120, 550, 400)
        
        # Design PDF content
        title_text = "Simple Interest Calculation Report"
        content_text = (
            f"Principal Amount: ${principal:,.2f}\n\n"
            f"Annual Interest Rate: {rate:.2f}%\n\n"
            f"Time Period: {time:.2f} Years\n\n"
            f"--------------------------------------------------\n\n"
            f"Calculated Simple Interest: ${interest:,.2f}\n\n"
            f"Total Future Value: ${total:,.2f}\n\n"
            f"--------------------------------------------------\n"
            f"Generated on behalf of Simple Interest Calculator Utility."
        )
        
        # Draw on page
        page.insert_textbox(title_rect, title_text, fontsize=20, fontname="hebo", color=(0.1, 0.3, 0.6))
        page.insert_textbox(content_rect, content_text, fontsize=12, fontname="helv", color=(0.2, 0.2, 0.2))
        
        doc.save(file_path)
        doc.close()

class CalculatorUI:
    def __init__(self, root=None):
        self.root = root
        if self.root:
            self.root.title("Simple Interest Calculator")
            self.root.geometry("450x450")
            self.root.configure(bg="#f4f6f9")
            self._build_ui()

    def _build_ui(self):
        # Title Label
        title_label = tk.Label(
            self.root, 
            text="Simple Interest Calculator", 
            font=("Helvetica", 16, "bold"), 
            bg="#f4f6f9", 
            fg="#1a365d"
        )
        title_label.pack(pady=20)

        # Input Frame
        input_frame = tk.Frame(self.root, bg="#f4f6f9")
        input_frame.pack(pady=10)

        # Principal Label and Entry
        tk.Label(input_frame, text="Principal Amount ($):", font=("Helvetica", 10), bg="#f4f6f9", fg="#2d3748").grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.entry_principal = tk.Entry(input_frame, font=("Helvetica", 10), width=20)
        self.entry_principal.grid(row=0, column=1, pady=5, padx=5)

        # Rate Label and Entry
        tk.Label(input_frame, text="Rate of Interest (%):", font=("Helvetica", 10), bg="#f4f6f9", fg="#2d3748").grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.entry_rate = tk.Entry(input_frame, font=("Helvetica", 10), width=20)
        self.entry_rate.grid(row=1, column=1, pady=5, padx=5)

        # Time Label and Entry
        tk.Label(input_frame, text="Time Period (Years):", font=("Helvetica", 10), bg="#f4f6f9", fg="#2d3748").grid(row=2, column=0, sticky="w", pady=5, padx=5)
        self.entry_time = tk.Entry(input_frame, font=("Helvetica", 10), width=20)
        self.entry_time.grid(row=2, column=1, pady=5, padx=5)

        # Calculate Button
        self.btn_calculate = tk.Button(
            self.root, 
            text="Calculate Interest", 
            command=self.perform_calculation,
            font=("Helvetica", 10, "bold"),
            bg="#3182ce", 
            fg="white", 
            activebackground="#2b6cb0", 
            activeforeground="white",
            padx=10, 
            pady=5,
            bd=0
        )
        self.btn_calculate.pack(pady=15)

        # Result Display Area
        self.result_frame = tk.LabelFrame(self.root, text="Result Summary", font=("Helvetica", 10, "bold"), bg="#f4f6f9", fg="#2d3748", padx=10, pady=10)
        self.result_frame.pack(pady=10, fill="x", padx=30)

        self.label_interest = tk.Label(self.result_frame, text="Simple Interest: $0.00", font=("Helvetica", 10), bg="#f4f6f9", fg="#2d3748")
        self.label_interest.pack(anchor="w")

        self.label_total = tk.Label(self.result_frame, text="Total Amount: $0.00", font=("Helvetica", 10), bg="#f4f6f9", fg="#2d3748")
        self.label_total.pack(anchor="w")

        # Action Buttons Frame
        self.action_frame = tk.Frame(self.root, bg="#f4f6f9")
        self.action_frame.pack(pady=15)

        self.btn_save_txt = tk.Button(
            self.action_frame, 
            text="Save TXT", 
            command=self.save_txt,
            state="disabled",
            font=("Helvetica", 9),
            bg="#48bb78",
            fg="white",
            bd=0,
            padx=8,
            pady=4
        )
        self.btn_save_txt.grid(row=0, column=0, padx=10)

        self.btn_save_pdf = tk.Button(
            self.action_frame, 
            text="Save PDF", 
            command=self.save_pdf,
            state="disabled",
            font=("Helvetica", 9),
            bg="#e53e3e",
            fg="white",
            bd=0,
            padx=8,
            pady=4
        )
        self.btn_save_pdf.grid(row=0, column=1, padx=10)

        self.calculated_principal = 0.0
        self.calculated_rate = 0.0
        self.calculated_time = 0.0
        self.calculated_interest = 0.0

    def perform_calculation(self):
        try:
            # Retrieve and validate inputs
            principal_str = self.entry_principal.get()
            rate_str = self.entry_rate.get()
            time_str = self.entry_time.get()

            if not principal_str or not rate_str or not time_str:
                raise ValueError("All input fields are required.")

            try:
                principal = float(principal_str)
                rate = float(rate_str)
                time = float(time_str)
            except ValueError:
                raise ValueError("Inputs must be numeric values.")

            if principal < 0 or rate < 0 or time < 0:
                raise ValueError("Input values cannot be negative.")

            # Perform calculation
            interest = CalculatorMath.calculate_simple_interest(principal, rate, time)
            total = principal + interest

            # Cache results
            self.calculated_principal = principal
            self.calculated_rate = rate
            self.calculated_time = time
            self.calculated_interest = interest

            # Update Labels
            self.label_interest.config(text=f"Simple Interest: ${interest:,.2f}")
            self.label_total.config(text=f"Total Amount: ${total:,.2f}")

            # Enable saving buttons
            self.btn_save_txt.config(state="normal")
            self.btn_save_pdf.config(state="normal")

            return True

        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
            self.btn_save_txt.config(state="disabled")
            self.btn_save_pdf.config(state="disabled")
            return False

    def save_txt(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            title="Save Report as TXT"
        )
        if file_path:
            try:
                DataStorage.store_result_text(
                    file_path, 
                    self.calculated_principal, 
                    self.calculated_rate, 
                    self.calculated_time, 
                    self.calculated_interest
                )
                messagebox.showinfo("Success", f"Report saved successfully to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save text file: {e}")

    def save_pdf(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Save Report as PDF"
        )
        if file_path:
            try:
                DataStorage.store_result_pdf(
                    file_path, 
                    self.calculated_principal, 
                    self.calculated_rate, 
                    self.calculated_time, 
                    self.calculated_interest
                )
                messagebox.showinfo("Success", f"PDF saved successfully to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save PDF file: {e}")

def main():
    root = tk.Tk()
    app = CalculatorUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
