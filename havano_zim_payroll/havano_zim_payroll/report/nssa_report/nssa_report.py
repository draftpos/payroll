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
		{"label": _("Last Name"), "fieldname": "last_name", "fieldtype": "Data", "width": 120},
		
		{"label": _("Gross Salary (USD)"), "fieldname": "gross_usd", "fieldtype": "Currency", "width": 130},
		{"label": _("NSSA Employee (USD)"), "fieldname": "nssa_employee_usd", "fieldtype": "Currency", "width": 140},
		{"label": _("NSSA Employer (USD)"), "fieldname": "nssa_employer_usd", "fieldtype": "Currency", "width": 140},

		{"label": _("Gross Salary (ZWG)"), "fieldname": "gross_zwg", "fieldtype": "Currency", "width": 130},
		{"label": _("NSSA Employee (ZWG)"), "fieldname": "nssa_employee_zwg", "fieldtype": "Currency", "width": 140},
		{"label": _("NSSA Employer (ZWG)"), "fieldname": "nssa_employer_zwg", "fieldtype": "Currency", "width": 140},
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
			"name", "first_name", "last_name", 
			"total_earnings_usd", "total_earnings_zwg"
		]
	)

	for emp in employees:
		doc = frappe.get_doc("havano_employee", emp.name)
		
		nssa_usd = 0.0
		nssa_zwg = 0.0

		for d in doc.employee_deductions:
			if d.components and d.components.upper() == "NSSA":
				nssa_usd += flt(d.amount_usd)
				nssa_zwg += flt(d.amount_zwg)

		row = {
			"employee_id": emp.name,
			"first_name": emp.first_name,
			"last_name": emp.last_name,
			"gross_usd": emp.total_earnings_usd,
			"nssa_employee_usd": nssa_usd,
			"nssa_employer_usd": nssa_usd,  # In Zim, Employer contribution matches Employee
			"gross_zwg": emp.total_earnings_zwg,
			"nssa_employee_zwg": nssa_zwg,
			"nssa_employer_zwg": nssa_zwg,
		}
		
		# Only include employees who actually have NSSA or Gross
		if row["gross_usd"] > 0 or row["gross_zwg"] > 0 or row["nssa_employee_usd"] > 0 or row["nssa_employee_zwg"] > 0:
			data.append(row)

	return data

def flt(val):
	try:
		return float(val or 0.0)
	except ValueError:
		return 0.0
