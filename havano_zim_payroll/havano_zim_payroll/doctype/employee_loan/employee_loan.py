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







