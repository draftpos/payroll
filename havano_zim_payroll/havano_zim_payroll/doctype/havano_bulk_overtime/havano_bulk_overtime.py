	# In havano_bulk_overtime.py
import frappe
from frappe.utils import flt
from frappe.model.document import Document


class HavanoBulkOvertime(Document):


	def before_save(self):
		basic_salary=0
		
		days=self.number_of_days
		for emp_row in self.employees:  # child table in Bulk Overtime
			emp_doc = frappe.get_doc("havano_employee", emp_row.employee)

			# Look for existing overtime row
			overtime_row = None
			for e in emp_doc.employee_earnings:		
				if e.components.strip().lower() == self.salary_component.strip().lower():
					overtime_row = e
					
				if e.components == "Basic Salary":  # or dynamically based on type
					basic_salary = e.amount_usd
					
			amount = round(flt(basic_salary / 26 * days), 2)
			if overtime_row:
				# Increment existing values
				overtime_row.amount_zwg = 0
				overtime_row.amount_usd += amount
			else:
				# Append new row
				new_row = emp_doc.append("employee_earnings", {})
				new_row.components = self.salary_component
				new_row.amount_zwg = 0
				new_row.amount_usd = amount
				# new_row.exchange_rate = flt(emp_row.exchange_rate)
				new_row.is_tax_applicable =True

			emp_doc.save(ignore_permissions=True)

