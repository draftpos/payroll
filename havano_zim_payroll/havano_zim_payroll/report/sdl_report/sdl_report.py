import frappe
from frappe import _
from frappe.utils import flt

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
		{"label": _("Employee ID"), "fieldname": "employee_id", "fieldtype": "Link", "options": "havano_employee", "width": 120},
		{"label": _("First Name"), "fieldname": "first_name", "fieldtype": "Data", "width": 120},
		{"label": _("Last Name"), "fieldname": "last_name", "fieldtype": "Data", "width": 120},
		
		{"label": _("Gross Salary (USD)"), "fieldname": "gross_usd", "fieldtype": "Currency", "width": 130},
		{"label": _("SDL Amount (USD)"), "fieldname": "sdl_usd", "fieldtype": "Currency", "width": 130},

		{"label": _("Gross Salary (ZWG)"), "fieldname": "gross_zwg", "fieldtype": "Currency", "width": 130},
		{"label": _("SDL Amount (ZWG)"), "fieldname": "sdl_zwg", "fieldtype": "Currency", "width": 130},
	]
	return columns

def get_data(filters):
	data = []
	
	query_filters = {"status": "Active"}
	if filters and filters.get("department"):
		query_filters["department"] = filters.get("department")

	if filters and filters.get("employee_id"):
		query_filters["name"] = filters.get("employee_id")

	employees = frappe.get_all(
		"havano_employee",
		filters=query_filters,
		fields=[
			"name", "first_name", "last_name", 
			"total_earnings_usd", "total_earnings_zwg", "sdl"
		]
	)

	for emp in employees:
		gross_usd = flt(emp.total_earnings_usd)
		gross_zwg = flt(emp.total_earnings_zwg)

		# SDL is standard 1% of gross wage
		sdl_usd = round(gross_usd * 0.01, 2)
		sdl_zwg = round(gross_zwg * 0.01, 2)

		row = {
			"employee_id": emp.name,
			"first_name": emp.first_name,
			"last_name": emp.last_name,
			"gross_usd": gross_usd,
			"sdl_usd": sdl_usd,
			"gross_zwg": gross_zwg,
			"sdl_zwg": sdl_zwg,
		}
		
		if gross_usd > 0 or gross_zwg > 0:
			data.append(row)

	return data
