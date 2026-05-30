# Copyright (c) 2026, Havano and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class EmployeeLoan(Document):
    def before_save(self):
        # total amount to be paid without interest
        self.total_amount_to_be_paid = self.loan_principal_amount

        # Calculate monthly amount to be paid
        if self.payment_span:
            self.monthly_amount_to_be_paid = self.loan_principal_amount / (self.payment_span * 12)
        else:
            self.monthly_amount_to_be_paid = 0

        # Initialize current loan balance for new loans
        if not self.current_loan_balance and not getattr(self, "loan_paid", 0):
            self.current_loan_balance = self.loan_principal_amount

        # Update Employee Master Record
        if self.employee and not getattr(self.flags, "ignore_employee_update", False):
            emp_doc = frappe.get_doc("havano_employee", self.employee)
            
            # 1. Handle Loan Amount (Earnings)
            earning_found = False
            for earn in getattr(emp_doc, "employee_earnings", []):
                if earn.components == "Loan Amount":
                    earning_found = True
                    if self.currency == "USD":
                        earn.amount_usd = self.loan_principal_amount
                        earn.amount_zwg = 0
                    else:
                        earn.amount_zwg = self.loan_principal_amount
                        earn.amount_usd = 0
                    break
            
            if not earning_found:
                emp_doc.append("employee_earnings", {
                    "components": "Loan Amount",
                    "amount_usd": self.loan_principal_amount if self.currency == "USD" else 0,
                    "amount_zwg": self.loan_principal_amount if self.currency != "USD" else 0
                })

            # Save employee doc so changes persist
            emp_doc.save(ignore_permissions=True)
