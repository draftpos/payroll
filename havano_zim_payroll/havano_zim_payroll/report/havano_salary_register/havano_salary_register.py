import frappe
from frappe import _

def execute(filters=None):
	if not filters:
		filters = {}

	columns, data = get_columns_and_data(filters)
	return columns, data

def get_columns_and_data(filters):
	# If payroll_period not selected, get the latest
	period = filters.get("payroll_period")
	if not period:
		latest = frappe.db.sql("""
			SELECT payroll_period 
			FROM `tabHavano Payroll Entry` 
			WHERE payroll_period IS NOT NULL AND payroll_period != ''
			ORDER BY date DESC LIMIT 1
		""")
		if latest:
			period = latest[0][0]

	entry_filters = {}
	if period:
		entry_filters["payroll_period"] = period

	if filters.get("employee_id"):
		# Could be link to havano_employee or employee code
		emp = filters.get("employee_id")
		emp_doc = frappe.db.get_value("havano_employee", emp, ["first_name", "last_name"], as_dict=True)
		if emp_doc:
			entry_filters["first_name"] = emp_doc.first_name
			if emp_doc.last_name:
				entry_filters["last_name"] = emp_doc.last_name
		else:
			entry_filters["first_name"] = emp

	payroll_entries = frappe.get_all(
		"Havano Payroll Entry",
		filters=entry_filters,
		fields=["name", "first_name", "last_name", "employee", "payroll_period", "date", "leave_balances", "total_leave_taken"],
		order_by="first_name, last_name"
	)

	if not payroll_entries:
		return get_empty_columns(), []

	entry_names = [e.name for e in payroll_entries]

	# Fetch Earnings from tabhavano_payroll_earnings
	earnings = frappe.get_all(
		"havano_payroll_earnings",
		filters={"parent": ["in", entry_names], "parenttype": "Havano Payroll Entry", "parentfield": "employee_earnings"},
		fields=["parent", "components", "amount_usd", "amount_zwg"],
		order_by="idx"
	)

	# Fetch Deductions from tabhavano_payroll_earnings
	deductions = frappe.get_all(
		"havano_payroll_earnings",
		filters={"parent": ["in", entry_names], "parenttype": "Havano Payroll Entry", "parentfield": "employee_deductions"},
		fields=["parent", "components", "amount_usd", "amount_zwg"],
		order_by="idx"
	)

	# Fetch employee details (National ID, department)
	emp_filters = {}
	if filters.get("department"):
		emp_filters["department"] = filters.get("department")
		
	employees = frappe.get_all("havano_employee", filters=emp_filters, fields=["name", "first_name", "last_name", "national_id", "department"])
	emp_map = {}
	for emp in employees:
		key = (emp.first_name or "").strip().lower() + "|" + (emp.last_name or "").strip().lower()
		emp_map[key] = emp

	# Determine component order:
	explicit_earnings = ["Basic Salary"]
	distinct_earnings = []
	for e in explicit_earnings:
		distinct_earnings.append(e)
	for e in earnings:
		if e.components and e.components not in distinct_earnings:
			distinct_earnings.append(e.components)

	explicit_deductions = ["NSSA", "PAYE", "Aids Levy", "SDL", "Medical Aid"]
	distinct_deductions = []
	for d in explicit_deductions:
		distinct_deductions.append(d)
	for d in deductions:
		if d.components and d.components not in distinct_deductions:
			distinct_deductions.append(d.components)

	# Build data map
	entry_data_map = {e.name: {"earnings": {}, "deductions": {}} for e in payroll_entries}
	for e in earnings:
		amt = flt(e.amount_usd) + flt(e.amount_zwg)
		entry_data_map[e.parent]["earnings"][e.components] = entry_data_map[e.parent]["earnings"].get(e.components, 0.0) + amt

	for d in deductions:
		amt = flt(d.amount_usd) + flt(d.amount_zwg)
		entry_data_map[d.parent]["deductions"][d.components] = entry_data_map[d.parent]["deductions"].get(d.components, 0.0) + amt

	data = []
	for entry in payroll_entries:
		key = (entry.first_name or "").strip().lower() + "|" + (entry.last_name or "").strip().lower()
		emp_info = emp_map.get(key, {})
		
		if filters.get("department") and not emp_info:
			continue

		full_name = f"{entry.first_name or ''} {entry.last_name or ''}".strip()
		row = {
			"employee_id": emp_info.get("name") or entry.employee or entry.name,
			"first_name": entry.first_name,
			"full_name": full_name,
			"payroll_period": entry.payroll_period,
			"date": entry.date,
			"national_id": emp_info.get("national_id") or "",
			"department": emp_info.get("department") or "",
			"total_earnings_usd": 0.0,
			"total_deduction_usd": 0.0,
			"net_pay_usd": 0.0
		}

		for comp in distinct_earnings:
			val = entry_data_map[entry.name]["earnings"].get(comp, 0.0)
			fname = frappe.scrub(comp) + "_earn_usd"
			row[fname] = val
			row["total_earnings_usd"] += val

		for comp in distinct_deductions:
			val = entry_data_map[entry.name]["deductions"].get(comp, 0.0)
			fname = frappe.scrub(comp) + "_ded_usd"
			row[fname] = val
			# SDL is an employer contribution, display it on payslip/register but do NOT deduct from employee net pay
			if comp.upper() != "SDL":
				row["total_deduction_usd"] += val

		row["net_pay_usd"] = row["total_earnings_usd"] - row["total_deduction_usd"]
		data.append(row)

	# Columns
	columns = [
		{"label": _("Employee ID"), "fieldname": "employee_id", "fieldtype": "Link", "options": "havano_employee", "width": 120},
		{"label": _("Full Name"), "fieldname": "full_name", "fieldtype": "Data", "width": 150},
		{"label": _("Payroll Period"), "fieldname": "payroll_period", "fieldtype": "Data", "width": 120},
	]

	for comp in distinct_earnings:
		columns.append({
			"label": f"{comp} (USD)",
			"fieldname": frappe.scrub(comp) + "_earn_usd",
			"fieldtype": "Currency",
			"width": 120
		})

	columns.append({
		"label": _("Total Earnings (USD)"),
		"fieldname": "total_earnings_usd",
		"fieldtype": "Currency",
		"width": 130
	})

	for comp in distinct_deductions:
		columns.append({
			"label": f"{comp} (USD)",
			"fieldname": frappe.scrub(comp) + "_ded_usd",
			"fieldtype": "Currency",
			"width": 120
		})

	columns.extend([
		{"label": _("Total Deductions (USD)"), "fieldname": "total_deduction_usd", "fieldtype": "Currency", "width": 130},
		{"label": _("Net Pay (USD)"), "fieldname": "net_pay_usd", "fieldtype": "Currency", "width": 130},
	])

	# Filter out columns that have 0 for all rows except core fields
	always_keep = ["employee_id", "full_name", "payroll_period", "basic_salary_earn_usd", "total_earnings_usd", "nssa_ded_usd", "paye_ded_usd", "aids_levy_ded_usd", "total_deduction_usd", "net_pay_usd"]
	filtered_cols = []
	for col in columns:
		fn = col.get("fieldname")
		if fn in always_keep:
			filtered_cols.append(col)
		elif col.get("fieldtype") == "Currency":
			col_total = sum(flt(r.get(fn)) for r in data)
			if col_total > 0:
				filtered_cols.append(col)
		else:
			filtered_cols.append(col)

	return filtered_cols, data

def get_empty_columns():
	return [
		{"label": _("Employee ID"), "fieldname": "employee_id", "fieldtype": "Link", "options": "havano_employee", "width": 120},
		{"label": _("Full Name"), "fieldname": "full_name", "fieldtype": "Data", "width": 150},
		{"label": _("Payroll Period"), "fieldname": "payroll_period", "fieldtype": "Data", "width": 120},
		{"label": _("Basic Salary (USD)"), "fieldname": "basic_salary_earn_usd", "fieldtype": "Currency", "width": 120},
		{"label": _("Total Earnings (USD)"), "fieldname": "total_earnings_usd", "fieldtype": "Currency", "width": 130},
		{"label": _("Total Deductions (USD)"), "fieldname": "total_deduction_usd", "fieldtype": "Currency", "width": 130},
		{"label": _("Net Pay (USD)"), "fieldname": "net_pay_usd", "fieldtype": "Currency", "width": 130},
	]

def flt(val):
	try:
		return float(val or 0.0)
	except ValueError:
		return 0.0
