# Copyright (c) 2025, Havano and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeLedger(Document):
	def before_save(self):
		# Ensure employee exists
		if not self.employee:
			frappe.throw("Employee is required before saving.")

		# Get the current balance owing
		current_balance = self.current_balance_owing or 0

		# Update the related employee record in havano_employee
		employee_doc = frappe.get_doc("havano_employee", self.employee)
		employee_doc.backpay = current_balance
		employee_doc.save(ignore_permissions=True)
