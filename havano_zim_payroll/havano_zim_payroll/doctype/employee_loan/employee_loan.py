# Copyright (c) 2026, Havano and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class EmployeeLoan(Document):
    def before_save(self):
        # effective interest rate for employee-friendly loan
        interest_amount = max(self.current_bank_interest_rate - self.company_interest_rate, 0)

        # total amount with monthly 
        self.total_amount_to_be_paid = self.loan_principal_amount + (self.loan_principal_amount * interest_amount * self.payment_span / 100)

        # total interest only
        self.total_interest_earning_amount = self.total_amount_to_be_paid - self.loan_principal_amount

        # monthly interest
        self.montly_loan_interest = self.total_interest_earning_amount / (self.payment_span * 12)

        employee = self.employee

        emp_doc = frappe.get_doc("havano_employee", employee)
        # Check if the deduction already exists, if not, add it
        deduction_found = False
        for ded in emp_doc.employee_deductions:
            if ded.components == "Loan Repayment":
                deduction_found = True
                # Update amounts based on currency
                if self.currency == "USD":
                    ded.amount_usd = self.monthly_amount_to_be_paid
                    ded.amount_zwg = 0
                else:
                    ded.amount_zwg = self.monthly_amount_to_be_paid
                    ded.amount_usd = 0
                break

        # If no existing deduction, append a new row
        if not deduction_found:
            emp_doc.append("employee_deductions", {
                "components": "Loan Repayment",
                "amount_usd": self.monthly_amount_to_be_paid if self.currency == "USD" else 0,
                "amount_zwg": self.monthly_amount_to_be_paid if self.currency != "USD" else 0
            })

        # Save employee doc so changes persist
        emp_doc.save()


        earning_found = False
        for e in emp_doc.employee_earnings:
            if e.components == "Loan Interest":
                earning_found = True
                # Update amounts based on currency
                if self.currency == "USD":
                    e.amount_usd = self.montly_loan_interest
                    e.amount_zwg = 0
                else:
                    e.amount_zwg = self.montly_loan_interest
                    e.amount_usd = 0
                break

        # If no existing deduction, append a new row
        if not earning_found:
            emp_doc.append("employee_earnings", {
                "components": "Loan Interest",
                "amount_usd": self.montly_loan_interest if self.currency == "USD" else 0,
                "amount_zwg": self.montly_loan_interest if self.currency != "USD" else 0
            })

        # Save employee doc so changes persist
        emp_doc.save()







