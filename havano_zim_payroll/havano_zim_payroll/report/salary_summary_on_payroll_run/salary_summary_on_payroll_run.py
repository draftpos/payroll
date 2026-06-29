import frappe
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	
	columns = []
	data = []

	# Fetch Payroll Entries
	entry_filters = {}
	if filters.get("from_date") and filters.get("to_date"):
		entry_filters["date"] = ["between", [filters.get("from_date"), filters.get("to_date")]]

	if filters.get("employee"):
		emp_doc = frappe.get_doc("havano_employee", filters.get("employee"))
		entry_filters["first_name"] = emp_doc.first_name
		if emp_doc.last_name:
			entry_filters["last_name"] = emp_doc.last_name

	payroll_entries = frappe.get_all(
		"Havano Payroll Entry",
		filters=entry_filters,
		fields=["name", "first_name", "last_name", "payroll_period", "date"]
	)

	if not payroll_entries:
		return get_columns([], []), []

	entry_names = [e.name for e in payroll_entries]

	# Fetch Earnings
	earnings = frappe.get_all(
		"havano_payroll_earnings",
		filters={"parent": ["in", entry_names], "parenttype": "Havano Payroll Entry"},
		fields=["parent", "components", "amount_usd", "amount_zwg"]
	)

	# Fetch Deductions
	deductions = frappe.get_all(
		"havano_payroll_deductions",
		filters={"parent": ["in", entry_names], "parenttype": "Havano Payroll Entry"},
		fields=["parent", "components", "amount_usd", "amount_zwg"]
	)

	# Fetch employees to get National ID
	employees = frappe.get_all("havano_employee", fields=["name", "first_name", "last_name", "national_id"])
	emp_map = {}
	for emp in employees:
		key = (emp.first_name or "").strip().lower() + "|" + (emp.last_name or "").strip().lower()
		emp_map[key] = emp

	# Determine distinct components for columns
	distinct_earnings = []
	distinct_deductions = []
	
	# Explicitly requested columns
	explicit_earnings = ["Basic Salary", "Overtime"]
	explicit_deductions = ["Medical Aid", "Funeral", "NSSA", "PAYE", "Aids Levy"]
	
	for e in explicit_earnings:
		if e not in distinct_earnings:
			distinct_earnings.append(e)
			
	for e in earnings:
		if e.components and e.components not in distinct_earnings:
			distinct_earnings.append(e.components)

	for d in explicit_deductions:
		if d not in distinct_deductions:
			distinct_deductions.append(d)
			
	for d in deductions:
		if d.components and d.components not in distinct_deductions:
			distinct_deductions.append(d.components)

	columns = get_columns(distinct_earnings, distinct_deductions)

	# Map data
	entry_data_map = {e.name: {"earnings": {}, "deductions": {}} for e in payroll_entries}
	
	for e in earnings:
		amt = frappe.utils.flt(e.amount_usd) + frappe.utils.flt(e.amount_zwg)
		entry_data_map[e.parent]["earnings"][e.components] = entry_data_map[e.parent]["earnings"].get(e.components, 0.0) + amt

	for d in deductions:
		amt = frappe.utils.flt(d.amount_usd) + frappe.utils.flt(d.amount_zwg)
		entry_data_map[d.parent]["deductions"][d.components] = entry_data_map[d.parent]["deductions"].get(d.components, 0.0) + amt

	for entry in payroll_entries:
		key = (entry.first_name or "").strip().lower() + "|" + (entry.last_name or "").strip().lower()
		emp = emp_map.get(key, {})
		
		row = {
			"employee": emp.get("name"),
			"employee_name": f"{entry.first_name or ''} {entry.last_name or ''}".strip(),
			"national_id": emp.get("national_id"),
			"period": entry.payroll_period,
			"date": entry.date,
			"total_earnings": 0.0,
			"total_deductions": 0.0,
			"net_pay": 0.0
		}
		
		# Earnings
		for comp in distinct_earnings:
			val = entry_data_map[entry.name]["earnings"].get(comp, 0.0)
			row[frappe.scrub(comp)] = val
			row["total_earnings"] += val
			
		# Deductions
		for comp in distinct_deductions:
			val = entry_data_map[entry.name]["deductions"].get(comp, 0.0)
			row[frappe.scrub(comp)] = val
			row["total_deductions"] += val
			
		row["net_pay"] = row["total_earnings"] - row["total_deductions"]
		data.append(row)

	return columns, data

def get_columns(earnings, deductions):
	columns = [
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "havano_employee", "width": 120},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
		{"label": _("National ID"), "fieldname": "national_id", "fieldtype": "Data", "width": 120},
		{"label": _("Period"), "fieldname": "period", "fieldtype": "Data", "width": 120},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
	]

	for e in earnings:
		columns.append({
			"label": e,
			"fieldname": frappe.scrub(e),
			"fieldtype": "Currency",
			"width": 120
		})

	columns.append({
		"label": _("Total Earnings"),
		"fieldname": "total_earnings",
		"fieldtype": "Currency",
		"width": 130
	})

	for d in deductions:
		columns.append({
			"label": d,
			"fieldname": frappe.scrub(d),
			"fieldtype": "Currency",
			"width": 120
		})

	columns.append({
		"label": _("Total Deductions"),
		"fieldname": "total_deductions",
		"fieldtype": "Currency",
		"width": 130
	})

	columns.append({
		"label": _("Net Pay"),
		"fieldname": "net_pay",
		"fieldtype": "Currency",
		"width": 130
	})

	return columns
