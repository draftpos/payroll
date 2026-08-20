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
	entry_filters = {}
	if filters and filters.get("payroll_period"):
		entry_filters["payroll_period"] = filters.get("payroll_period")

	if filters and filters.get("employee_id"):
		emp_doc = frappe.get_doc("havano_employee", filters.get("employee_id"))
		entry_filters["first_name"] = emp_doc.first_name
		if emp_doc.last_name:
			entry_filters["last_name"] = emp_doc.last_name

	payroll_entries = frappe.get_all(
		"Havano Payroll Entry",
		filters=entry_filters,
		fields=["name"]
	)

	earnings = {}
	deductions = {}
	total_earnings = 0.0
	total_deductions = 0.0

	if not payroll_entries:
		pass
	else:
		entry_names = [e.name for e in payroll_entries]

		earnings_data = frappe.get_all(
			"havano_payroll_earnings",
			filters={"parent": ["in", entry_names], "parenttype": "Havano Payroll Entry", "parentfield": "employee_earnings"},
			fields=["components", "amount_usd", "amount_zwg"]
		)

		for e in earnings_data:
			if not e.components: continue
			comp = e.components
			amt = flt(e.amount_usd) + flt(e.amount_zwg)
			earnings[comp] = earnings.get(comp, 0.0) + amt
			total_earnings += amt

		deductions_data = frappe.get_all(
			"havano_payroll_earnings",
			filters={"parent": ["in", entry_names], "parenttype": "Havano Payroll Entry", "parentfield": "employee_deductions"},
			fields=["components", "amount_usd", "amount_zwg"]
		)

		for d in deductions_data:
			if not d.components: continue
			comp = d.components
			amt = flt(d.amount_usd) + flt(d.amount_zwg)
			deductions[comp] = deductions.get(comp, 0.0) + amt
			total_deductions += amt

	earning_items = sorted(earnings.items(), key=lambda x: x[0])
	deduction_items = sorted(deductions.items(), key=lambda x: x[0])

	max_rows = max(len(earning_items), len(deduction_items))
	data = []

	for i in range(max_rows):
		e_name, e_amt = earning_items[i] if i < len(earning_items) else ("", 0.0)
		d_name, d_amt = deduction_items[i] if i < len(deduction_items) else ("", 0.0)
		
		data.append({
			"earnings": e_name,
			"earnings_amount_usd": e_amt if e_name else None,
			"deductions": d_name,
			"deductions_amount_usd": d_amt if d_name else None,
		})

	data.append({
		"earnings": "Total Earnings",
		"earnings_amount_usd": total_earnings,
		"deductions": "Total Deductions",
		"deductions_amount_usd": total_deductions,
	})

	data.append({
		"earnings": "Net Balance",
		"earnings_amount_usd": total_earnings - total_deductions,
		"deductions": "",
		"deductions_amount_usd": None,
	})

	return data

def flt(val):
	try:
		return float(val or 0.0)
	except ValueError:
		return 0.0
