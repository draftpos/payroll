import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	columns = [
		{"label": _("Employee ID"), "fieldname": "employee_id", "fieldtype": "Link", "options": "havano_employee", "width": 120},
		{"label": _("First Name"), "fieldname": "first_name", "fieldtype": "Data", "width": 120},
		{"label": _("Full Name"), "fieldname": "full_name", "fieldtype": "Data", "width": 150},
		
		{"label": _("Basic Salary (USD)"), "fieldname": "basic_salary_usd", "fieldtype": "Currency", "width": 120},
		{"label": _("Total Earnings (USD)"), "fieldname": "total_earnings_usd", "fieldtype": "Currency", "width": 130},
		{"label": _("Total Deductions (USD)"), "fieldname": "total_deduction_usd", "fieldtype": "Currency", "width": 130},
		{"label": _("Net Pay (USD)"), "fieldname": "net_pay_usd", "fieldtype": "Currency", "width": 130},

		{"label": _("Basic Salary (ZWG)"), "fieldname": "basic_salary_zwg", "fieldtype": "Currency", "width": 120},
		{"label": _("Total Earnings (ZWG)"), "fieldname": "total_earnings_zwg", "fieldtype": "Currency", "width": 130},
		{"label": _("Total Deductions (ZWG)"), "fieldname": "total_deduction_zwg", "fieldtype": "Currency", "width": 130},
		{"label": _("Net Pay (ZWG)"), "fieldname": "net_pay_zwg", "fieldtype": "Currency", "width": 130},
	]
	return columns

def get_data(filters):
	data = []
	
	query_filters = {"status": "Active"}
	if filters and filters.get("employee_id"):
		query_filters["name"] = filters.get("employee_id")

	employees = frappe.get_all(
		"havano_employee",
		filters=query_filters,
		fields=[
			"name", "first_name", "employee_name", 
			"basic_salary_calculated", "salary_currency",
			"total_earnings_usd", "total_deduction_usd", "total_net_income_usd",
			"total_earnings_zwg", "total_deduction_zwg", "total_net_income_zwg"
		]
	)

	for emp in employees:
		# Map basic salary to respective currency depending on primary currency, 
		# or fetch from child tables if we want exact splits.
		# For simplicity, we put the calculated basic salary in USD if primary is USD.
		doc = frappe.get_doc("havano_employee", emp.name)
		
		basic_usd = 0.0
		basic_zwg = 0.0
		for e in doc.employee_earnings:
			if e.components and "basic" in e.components.lower():
				basic_usd += flt(e.amount_usd)
				basic_zwg += flt(e.amount_zwg)

		row = {
			"employee_id": emp.name,
			"first_name": emp.first_name,
			"full_name": emp.employee_name,
			"basic_salary_usd": basic_usd,
			"total_earnings_usd": emp.total_earnings_usd,
			"total_deduction_usd": emp.total_deduction_usd,
			"net_pay_usd": emp.total_net_income_usd,
			"basic_salary_zwg": basic_zwg,
			"total_earnings_zwg": emp.total_earnings_zwg,
			"total_deduction_zwg": emp.total_deduction_zwg,
			"net_pay_zwg": emp.total_net_income_zwg,
		}
		data.append(row)

	return data

def flt(val):
	try:
		return float(val or 0.0)
	except ValueError:
		return 0.0
