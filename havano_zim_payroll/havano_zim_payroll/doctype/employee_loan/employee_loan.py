# Copyright (c) 2026, Havano and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeLoan(Document):
    def before_save(self):
        interest_amount = self.current_bank_interest_rate * self.company_interest_rate
        self.total_amount_to_be_paid = self.loan_principal_amount + self.loan_principal_amount * (interest_amount / 100)
        self.monthly_amount_to_be_paid = (self.total_amount_to_be_paid / self.payment_span) / 12

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






