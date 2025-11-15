# Copyright (c) 2025, Havano and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class HavanoLeaveEncashment(Document):
	def before_save(self):
		employee=self.employee
		amount=self.paid_amount
		days=self.encashment_days
		print(f"jjjjjjjjjjjjjjj{amount} {days}")

		leave_balance_data = frappe.db.get_value(
			"Havano Leave Balances",
			{"employee": employee, "havano_leave_type": "Annual Leave"},
			["name", "employee", "employee_name", "havano_leave_type", "leave_balance"],
			as_dict=True
		)

		if leave_balance_data:

			if leave_balance_data.leave_balance < self.encashment_days:
				frappe.throw(
					f"Days to be encashed cannot be greater than available days: {leave_balance_data.leave_balance}"
				)

			# Load full document
			leave_balance_doc = frappe.get_doc("Havano Leave Balances", leave_balance_data.name)
			# Deduct encashment days
			leave_balance_doc.leave_balance = leave_balance_doc.leave_balance - self.encashment_days
			leave_balance_doc.save(ignore_permissions=True)

			emp = frappe.get_doc("havano_employee", employee)

			# 3. Check if "Cash In Lieu" already exists in employee_earnings table
			existing_row = None
			for row in emp.employee_earnings:
				if row.components.upper() == "CASH IN LIEU":
					existing_row = row
					print("existsssssssssssssssssssssssssssssssssssssssss")
					break

			if existing_row:
				existing_row.amount_usd += self.paid_amount
				existing_row.amount_zwg += 0
			else:
				# Add new row
				emp.append("employee_earnings", {
					"components": "Cash In Lieu",
					"item_code": "Cash In Lieu",
					"amount_usd": self.paid_amount,
					"amount_zwg": 0,
					"exchange_rate": 1,
					"is_tax_applicable": 1
				})

			# 4. Save the employee doc
			emp.save()


		else:
			print("No leave balance record found.")

