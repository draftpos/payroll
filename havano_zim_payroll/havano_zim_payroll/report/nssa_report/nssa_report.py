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
		{"label": _("First Name"), "fieldname": "first_name", "fieldtype": "Data", "width": 120},
		{"label": _("Surname"), "fieldname": "surname", "fieldtype": "Data", "width": 120},
		{"label": _("Payroll Period"), "fieldname": "payroll_period", "fieldtype": "Data", "width": 140},
		{"label": _("NSSA (ZIG) Employee"), "fieldname": "nssa_zig_employee", "fieldtype": "Currency", "width": 160},
		{"label": _("NSSA (ZIG) Employer"), "fieldname": "nssa_zig_employer", "fieldtype": "Currency", "width": 160},
		{"label": _("NSSA (USD) Employee"), "fieldname": "nssa_usd_employee", "fieldtype": "Currency", "width": 160},
		{"label": _("NSSA (USD) Employer"), "fieldname": "nssa_usd_employer", "fieldtype": "Currency", "width": 160},
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
			"name", "first_name", "last_name"
		]
	)

	today = date.today()
	month_name = calendar.month_name[today.month]
	payroll_period = f"{month_name} {today.year}"

	for emp in employees:
		doc = frappe.get_doc("havano_employee", emp.name)
		
		nssa_usd = 0.0
		nssa_zwg = 0.0

		for d in doc.employee_deductions:
			if d.components and d.components.upper() == "NSSA":
				nssa_usd += flt(d.amount_usd)
				nssa_zwg += flt(d.amount_zwg)

		row = {
			"first_name": emp.first_name,
			"surname": emp.last_name,
			"payroll_period": payroll_period,
			"nssa_zig_employee": nssa_zwg,
			"nssa_zig_employer": nssa_zwg,
			"nssa_usd_employee": nssa_usd,
			"nssa_usd_employer": nssa_usd,
		}
		
		if nssa_usd > 0 or nssa_zwg > 0:
			data.append(row)

	return data

def flt(val):
	try:
		return float(val or 0.0)
	except ValueError:
		return 0.0
