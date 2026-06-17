import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	
	filtered_columns = []
	for col in columns:
		if col.get("fieldtype") in ["Currency", "Float", "Int"]:
			col_total = sum(flt(row.get(col.get("fieldname"))) for row in data)
			if col_total == 0:
				continue
		filtered_columns.append(col)

	return filtered_columns, data

def get_columns(filters=None):
	columns = [
		{"label": _("Earnings"), "fieldname": "earnings", "fieldtype": "Data", "width": 250},
		{"label": _("Amount (USD)"), "fieldname": "earnings_amount_usd", "fieldtype": "Currency", "width": 180},
		{"label": _("Deductions"), "fieldname": "deductions", "fieldtype": "Data", "width": 250},
		{"label": _("Amount (USD)"), "fieldname": "deductions_amount_usd", "fieldtype": "Currency", "width": 180},
	]
	return columns

def get_data(filters):
	query_filters = {"status": "Active"}
	if filters and filters.get("employee_id"):
		query_filters["name"] = filters.get("employee_id")

	employees = frappe.get_all(
		"havano_employee",
		filters=query_filters,
		pluck="name"
	)

	earnings = {}
	deductions = {}
	
	total_earnings = 0.0
	total_deductions = 0.0

	for emp_name in employees:
		doc = frappe.get_doc("havano_employee", emp_name)
		
		for e in doc.employee_earnings:
			if not e.components: continue
			comp = e.components
			earnings[comp] = earnings.get(comp, 0.0) + flt(e.amount_usd)
			total_earnings += flt(e.amount_usd)

		for d in doc.employee_deductions:
			if not d.components: continue
			comp = d.components
			deductions[comp] = deductions.get(comp, 0.0) + flt(d.amount_usd)
			total_deductions += flt(d.amount_usd)

	earning_items = sorted(earnings.items(), key=lambda x: x[0])
	deduction_items = sorted(deductions.items(), key=lambda x: x[0])

	max_rows = max(len(earning_items), len(deduction_items))
	data = []

	for i in range(max_rows):
		e_name, e_amt = earning_items[i] if i < len(earning_items) else ("", 0.0)
		d_name, d_amt = deduction_items[i] if i < len(deduction_items) else ("", 0.0)
		
		data.append({
			"earnings": e_name,
			"earnings_amount_usd": e_amt if e_name else "",
			"deductions": d_name,
			"deductions_amount_usd": d_amt if d_name else "",
		})

	# Add Total Row
	data.append({
		"earnings": "Total Earnings",
		"earnings_amount_usd": total_earnings,
		"deductions": "Total Deductions",
		"deductions_amount_usd": total_deductions,
	})

	return data

def flt(val):
	try:
		return float(val or 0.0)
	except ValueError:
		return 0.0
