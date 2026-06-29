import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns_and_data(filters)
	
	filtered_columns = []
	for col in columns:
		if col.get("fieldtype") in ["Currency", "Float", "Int"]:
			col_total = sum(flt(row.get(col.get("fieldname"))) for row in data)
			if col_total == 0:
				continue
		filtered_columns.append(col)

	return filtered_columns, data

def get_columns_and_data(filters):
	query_filters = {"status": "Active"}
	if filters and filters.get("department"):
		query_filters["department"] = filters.get("department")

	if filters and filters.get("employee_id"):
		query_filters["name"] = filters.get("employee_id")

	employees = frappe.get_all(
		"havano_employee",
		filters=query_filters,
		fields=[
			"name", "first_name", "last_name", "employee_name", 
			"basic_salary_calculated", "salary_currency",
			"total_earnings_usd", "total_deduction_usd", "total_net_income_usd",
			"total_earnings_zwg", "total_deduction_zwg", "total_net_income_zwg"
		]
	)

	# Collect all distinct components across all matching employees
	earning_components = set()
	deduction_components = set()
	
	data = []
	
	for emp in employees:
		doc = frappe.get_doc("havano_employee", emp.name)
		
		full_name = emp.employee_name or f"{emp.first_name or ''} {emp.last_name or ''}".strip()

		row = {
			"employee_id": emp.name,
			"first_name": emp.first_name,
			"full_name": full_name,
			"total_earnings_usd": flt(emp.total_earnings_usd),
			"total_deduction_usd": flt(emp.total_deduction_usd),
			"net_pay_usd": flt(emp.total_net_income_usd),
			"total_earnings_zwg": flt(emp.total_earnings_zwg),
			"total_deduction_zwg": flt(emp.total_deduction_zwg),
			"net_pay_zwg": flt(emp.total_net_income_zwg),
		}

		basic_usd = 0.0
		basic_zwg = 0.0

		for e in doc.employee_earnings:
			if not e.components: continue
			comp = e.components
			if "basic" in comp.lower():
				basic_usd += flt(e.amount_usd)
				basic_zwg += flt(e.amount_zwg)
			else:
				earning_components.add(comp)
				# Store amount under dynamic fieldname
				fname_usd = frappe.scrub(comp) + "_earn_usd"
				fname_zwg = frappe.scrub(comp) + "_earn_zwg"
				row[fname_usd] = row.get(fname_usd, 0.0) + flt(e.amount_usd)
				row[fname_zwg] = row.get(fname_zwg, 0.0) + flt(e.amount_zwg)

		for d in doc.employee_deductions:
			if not d.components: continue
			comp = d.components
			deduction_components.add(comp)
			fname_usd = frappe.scrub(comp) + "_ded_usd"
			fname_zwg = frappe.scrub(comp) + "_ded_zwg"
			row[fname_usd] = row.get(fname_usd, 0.0) + flt(d.amount_usd)
			row[fname_zwg] = row.get(fname_zwg, 0.0) + flt(d.amount_zwg)

		row["basic_salary_usd"] = basic_usd
		row["basic_salary_zwg"] = basic_zwg
		
		data.append(row)

	# Build dynamic columns
	columns = [
		{"label": _("Employee ID"), "fieldname": "employee_id", "fieldtype": "Link", "options": "havano_employee", "width": 120},
		{"label": _("First Name"), "fieldname": "first_name", "fieldtype": "Data", "width": 120},
		{"label": _("Full Name"), "fieldname": "full_name", "fieldtype": "Data", "width": 150},
		{"label": _("Basic Salary (USD)"), "fieldname": "basic_salary_usd", "fieldtype": "Currency", "width": 120},
	]

	# Add earning columns
	for comp in sorted(earning_components):
		columns.append({"label": f"{comp} (USD)", "fieldname": frappe.scrub(comp) + "_earn_usd", "fieldtype": "Currency", "width": 120})
	
	columns.append({"label": _("Total Earnings (USD)"), "fieldname": "total_earnings_usd", "fieldtype": "Currency", "width": 130})

	# Add deduction columns
	for comp in sorted(deduction_components):
		columns.append({"label": f"{comp} (USD)", "fieldname": frappe.scrub(comp) + "_ded_usd", "fieldtype": "Currency", "width": 120})
	
	columns.extend([
		{"label": _("Total Deductions (USD)"), "fieldname": "total_deduction_usd", "fieldtype": "Currency", "width": 130},
		{"label": _("Net Pay (USD)"), "fieldname": "net_pay_usd", "fieldtype": "Currency", "width": 130},
	])

	# Add ZWG Columns if necessary
	columns.append({"label": _("Basic Salary (ZWG)"), "fieldname": "basic_salary_zwg", "fieldtype": "Currency", "width": 120})
	for comp in sorted(earning_components):
		columns.append({"label": f"{comp} (ZWG)", "fieldname": frappe.scrub(comp) + "_earn_zwg", "fieldtype": "Currency", "width": 120})
	columns.append({"label": _("Total Earnings (ZWG)"), "fieldname": "total_earnings_zwg", "fieldtype": "Currency", "width": 130})
	
	for comp in sorted(deduction_components):
		columns.append({"label": f"{comp} (ZWG)", "fieldname": frappe.scrub(comp) + "_ded_zwg", "fieldtype": "Currency", "width": 120})
	columns.extend([
		{"label": _("Total Deductions (ZWG)"), "fieldname": "total_deduction_zwg", "fieldtype": "Currency", "width": 130},
		{"label": _("Net Pay (ZWG)"), "fieldname": "net_pay_zwg", "fieldtype": "Currency", "width": 130},
	])

	return columns, data

def flt(val):
	try:
		return float(val or 0.0)
	except ValueError:
		return 0.0
