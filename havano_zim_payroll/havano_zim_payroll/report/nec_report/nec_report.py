import frappe
from frappe import _
from datetime import date
import calendar

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	columns = [
		{"label": _("Surname"), "fieldname": "surname", "fieldtype": "Data", "width": 120},
		{"label": _("First Names"), "fieldname": "first_names", "fieldtype": "Data", "width": 120},
		{"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Date", "width": 120},
		{"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Date", "width": 120},
		{"label": _("NEC Earnings (USD)"), "fieldname": "nec_earnings_usd", "fieldtype": "Currency", "width": 150},
		{"label": _("Employee Contribution (USD)"), "fieldname": "employee_contribution_usd", "fieldtype": "Currency", "width": 200},
		{"label": _("Employer Contribution (USD)"), "fieldname": "employer_contribution_usd", "fieldtype": "Currency", "width": 200},
		{"label": _("Total NEC (USD)"), "fieldname": "total_nec_usd", "fieldtype": "Currency", "width": 150},
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
			"name", "first_name", "last_name", "total_taxable_income_usd"
		]
	)

	today = date.today()
	_, last_day = calendar.monthrange(today.year, today.month)
	start_dt = date(today.year, today.month, 1)
	end_dt = date(today.year, today.month, last_day)

	for emp in employees:
		doc = frappe.get_doc("havano_employee", emp.name)
		
		nec_usd = 0.0

		for d in doc.employee_deductions:
			if d.components and "nec" in d.components.lower():
				nec_usd += flt(d.amount_usd)

		row = {
			"surname": emp.last_name,
			"first_names": emp.first_name,
			"start_date": start_dt,
			"end_date": end_dt,
			"nec_earnings_usd": flt(emp.total_taxable_income_usd),
			"employee_contribution_usd": nec_usd,
			"employer_contribution_usd": nec_usd,  # Assuming match
			"total_nec_usd": nec_usd * 2,
		}
		
		if nec_usd > 0:
			data.append(row)

	return data

def flt(val):
	try:
		return float(val or 0.0)
	except ValueError:
		return 0.0
