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
		
		{"label": _("Basic Salary (USD)"), "fieldname": "basic_usd", "fieldtype": "Currency", "width": 130},
		{"label": _("NEC Employee (USD)"), "fieldname": "nec_employee_usd", "fieldtype": "Currency", "width": 140},
		{"label": _("NEC Employer (USD)"), "fieldname": "nec_employer_usd", "fieldtype": "Currency", "width": 140},

		{"label": _("Basic Salary (ZWG)"), "fieldname": "basic_zwg", "fieldtype": "Currency", "width": 130},
		{"label": _("NEC Employee (ZWG)"), "fieldname": "nec_employee_zwg", "fieldtype": "Currency", "width": 140},
		{"label": _("NEC Employer (ZWG)"), "fieldname": "nec_employer_zwg", "fieldtype": "Currency", "width": 140},
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

	for emp in employees:
		doc = frappe.get_doc("havano_employee", emp.name)
		
		nec_usd = 0.0
		nec_zwg = 0.0
		basic_usd = 0.0
		basic_zwg = 0.0

		for e in doc.employee_earnings:
			if e.components and "basic" in e.components.lower():
				basic_usd += flt(e.amount_usd)
				basic_zwg += flt(e.amount_zwg)

		for d in doc.employee_deductions:
			if d.components and "nec" in d.components.lower():
				nec_usd += flt(d.amount_usd)
				nec_zwg += flt(d.amount_zwg)

		row = {
			"employee_id": emp.name,
			"first_name": emp.first_name,
			"last_name": emp.last_name,
			"basic_usd": basic_usd,
			"nec_employee_usd": nec_usd,
			"nec_employer_usd": nec_usd,  # Employer matches employee
			"basic_zwg": basic_zwg,
			"nec_employee_zwg": nec_zwg,
			"nec_employer_zwg": nec_zwg,
		}
		
		if basic_usd > 0 or basic_zwg > 0 or nec_usd > 0 or nec_zwg > 0:
			data.append(row)

	return data

def flt(val):
	try:
		return float(val or 0.0)
	except ValueError:
		return 0.0
