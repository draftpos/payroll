# Copyright (c) 2025, Havano and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class havano_leave_encashment(Document):

	def validate(self):
		days = float(self.days_being_encashed or 0)
		balance = float(self.current_leave_balance or 0)

		if days <= 0:
			frappe.throw("Days being encashed must be greater than zero.")

		if balance <= 0:
			frappe.throw("No leave balance found. Please select employee and leave type first.")

		if days > balance:
			frappe.throw(f"Cannot encash {days} days. Available balance is only {balance} days.")

	def on_submit(self):
		days = float(self.days_being_encashed or 0)

		# 1. Deduct from Havano Leave Balances
		leave_balance_name = frappe.db.get_value(
			"Havano Leave Balances",
			{"employee": self.employee, "havano_leave_type": self.leave_type},
			"name"
		)

		if not leave_balance_name:
			frappe.throw(f"No leave balance record found for employee {self.employee} and leave type {self.leave_type}.")

		lb = frappe.get_doc("Havano Leave Balances", leave_balance_name)
		lb.leave_balance = float(lb.leave_balance or 0) - days
		lb.save(ignore_permissions=True)

		# 2. Update total_leave_allocated on havano_employee
		if frappe.db.exists("havano_employee", self.employee):
			emp = frappe.get_doc("havano_employee", self.employee)
			emp.total_leave_allocated = float(emp.total_leave_allocated or 0) - days
			emp.save(ignore_permissions=True)

		frappe.db.commit()

	def on_cancel(self):
		days = float(self.days_being_encashed or 0)

		# 1. Restore Havano Leave Balances
		leave_balance_name = frappe.db.get_value(
			"Havano Leave Balances",
			{"employee": self.employee, "havano_leave_type": self.leave_type},
			"name"
		)

		if leave_balance_name:
			lb = frappe.get_doc("Havano Leave Balances", leave_balance_name)
			lb.leave_balance = float(lb.leave_balance or 0) + days
			lb.save(ignore_permissions=True)

		# 2. Restore total_leave_allocated on havano_employee
		if frappe.db.exists("havano_employee", self.employee):
			emp = frappe.get_doc("havano_employee", self.employee)
			emp.total_leave_allocated = float(emp.total_leave_allocated or 0) + days
			emp.save(ignore_permissions=True)

		frappe.db.commit()
