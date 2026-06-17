import frappe
from frappe import _
from datetime import date
import calendar

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	
	filtered_columns = []
	for col in columns:
		if col.get("fieldtype") in ["Currency", "Float", "Int"]:
			col_total = sum(flt(row.get(col.get("fieldname"))) for row in data)
			if col_total == 0:
				continue
		filtered_columns.append(col)

	return filtered_columns, data

def get_columns():
	columns = [
		{"label": _("Surname"), "fieldname": "surname", "fieldtype": "Data", "width": 120},
		{"label": _("First Names"), "fieldname": "first_names", "fieldtype": "Data", "width": 120},
		{"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Date", "width": 120},
		{"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Date", "width": 120},
		{"label": _("Total Insurable Earnings (USD)"), "fieldname": "total_insurable_earnings_usd", "fieldtype": "Currency", "width": 180},
		{"label": _("Current Contributions (USD)"), "fieldname": "current_contributions_usd", "fieldtype": "Currency", "width": 180},
		{"label": _("Arrears (USD)"), "fieldname": "arrears_usd", "fieldtype": "Currency", "width": 120},
		{"label": _("Prepayments (USD)"), "fieldname": "prepayments_usd", "fieldtype": "Currency", "width": 140},
		{"label": _("Surcharge (USD)"), "fieldname": "surcharge_usd", "fieldtype": "Currency", "width": 120},
		{"label": _("Total Payment (USD)"), "fieldname": "total_payment_usd", "fieldtype": "Currency", "width": 150},
		{"label": _("Employer Payment (USD)"), "fieldname": "employer_payment_usd", "fieldtype": "Currency", "width": 160},
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
		
		nssa_usd = 0.0

		for d in doc.employee_deductions:
			if d.components and d.components.upper() == "NSSA":
				nssa_usd += flt(d.amount_usd)

		row = {
			"surname": emp.last_name,
			"first_names": emp.first_name,
			"start_date": start_dt,
			"end_date": end_dt,
			"total_insurable_earnings_usd": flt(emp.total_taxable_income_usd),
			"current_contributions_usd": nssa_usd,
			"arrears_usd": 0.0,
			"prepayments_usd": 0.0,
			"surcharge_usd": 0.0,
			"total_payment_usd": nssa_usd,
			"employer_payment_usd": nssa_usd,  # Assuming employer payment is the same
		}
		
		if nssa_usd > 0 or row["total_insurable_earnings_usd"] > 0:
			data.append(row)

	return data

def flt(val):
	try:
		return float(val or 0.0)
	except ValueError:
		return 0.0
