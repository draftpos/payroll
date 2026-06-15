import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_columns(filters=None):
	group_by = filters.get("group_by") if filters else "Employee"

	if group_by == "Salary Component":
		columns = [
			{"label": _("Salary Component"), "fieldname": "salary_component", "fieldtype": "Link", "options": "havano_salary_component", "width": 250},
			{"label": _("Type"), "fieldname": "type", "fieldtype": "Data", "width": 120},
			{"label": _("Total Amount (USD)"), "fieldname": "amount_usd", "fieldtype": "Currency", "width": 150},
			{"label": _("Total Amount (ZWG)"), "fieldname": "amount_zwg", "fieldtype": "Currency", "width": 150},
		]
		return columns

	# Default view: Grouped by Employee (Original Code)
	columns = [
		{"label": _("Employee ID"), "fieldname": "employee_id", "fieldtype": "Link", "options": "havano_employee", "width": 120},
		{"label": _("First Name"), "fieldname": "first_name", "fieldtype": "Data", "width": 120},
		{"label": _("Full Name"), "fieldname": "full_name", "fieldtype": "Data", "width": 150},
	]
	# Fetch all salary components defined in the system
	components = frappe.get_all("havano_salary_component", fields=["salary_component", "type"], order_by="type desc, salary_component asc")
	
	for comp in components:
		# Add USD column
		columns.append({
			"label": f"{comp.salary_component} (USD)",
			"fieldname": frappe.scrub(f"{comp.salary_component}_usd"),
			"fieldtype": "Currency",
			"width": 100
		})
		# Add ZWG column immediately after
		columns.append({
			"label": f"{comp.salary_component} (ZWG)",
			"fieldname": frappe.scrub(f"{comp.salary_component}_zwg"),
			"fieldtype": "Currency",
			"width": 100
		})

	# Add Totals at the end
	columns.extend([
		{"label": _("Total Earnings (USD)"), "fieldname": "total_earnings_usd", "fieldtype": "Currency", "width": 120},
		{"label": _("Total Deductions (USD)"), "fieldname": "total_deductions_usd", "fieldtype": "Currency", "width": 120},
		{"label": _("Net Income (USD)"), "fieldname": "net_income_usd", "fieldtype": "Currency", "width": 120},
		{"label": _("Total Earnings (ZWG)"), "fieldname": "total_earnings_zwg", "fieldtype": "Currency", "width": 120},
		{"label": _("Total Deductions (ZWG)"), "fieldname": "total_deductions_zwg", "fieldtype": "Currency", "width": 120},
		{"label": _("Net Income (ZWG)"), "fieldname": "net_income_zwg", "fieldtype": "Currency", "width": 120},
	])

	return columns

def get_data(filters):
	group_by = filters.get("group_by") if filters else "Employee"
	
	if group_by == "Salary Component":
		return get_data_by_component(filters)

	# Default view: Grouped by Employee (Original Code)
	data = []
	
	query_filters = {"status": "Active"}
	if filters and filters.get("employee_id"):
		query_filters["name"] = filters.get("employee_id")

	# Fetch all matching employees
	employees = frappe.get_all(
		"havano_employee",
		filters=query_filters,
		fields=["name", "first_name", "employee_name", "total_earnings_usd", "total_deduction_usd", "total_net_income_usd", "total_earnings_zwg", "total_deduction_zwg", "total_net_income_zwg"]
	)

	for emp in employees:
		row = {
			"employee_id": emp.name,
			"first_name": emp.first_name,
			"full_name": emp.employee_name,
			"total_earnings_usd": emp.total_earnings_usd,
			"total_deductions_usd": emp.total_deduction_usd,
			"net_income_usd": emp.total_net_income_usd,
			"total_earnings_zwg": emp.total_earnings_zwg,
			"total_deductions_zwg": emp.total_deduction_zwg,
			"net_income_zwg": emp.total_net_income_zwg,
		}

		# Fetch earnings and deductions for this employee
		doc = frappe.get_doc("havano_employee", emp.name)
		
		for e in doc.employee_earnings:
			field_usd = frappe.scrub(f"{e.components}_usd")
			field_zwg = frappe.scrub(f"{e.components}_zwg")
			row[field_usd] = row.get(field_usd, 0) + (e.amount_usd or 0)
			row[field_zwg] = row.get(field_zwg, 0) + (e.amount_zwg or 0)

		for d in doc.employee_deductions:
			field_usd = frappe.scrub(f"{d.components}_usd")
			field_zwg = frappe.scrub(f"{d.components}_zwg")
			row[field_usd] = row.get(field_usd, 0) + (d.amount_usd or 0)
			row[field_zwg] = row.get(field_zwg, 0) + (d.amount_zwg or 0)

		data.append(row)

	return data

def get_data_by_component(filters):
	data = []
	totals = {}
	
	query_filters = {"status": "Active"}
	if filters and filters.get("employee_id"):
		query_filters["name"] = filters.get("employee_id")

	# Fetch all matching employees
	employees = frappe.get_all(
		"havano_employee",
		filters=query_filters,
		pluck="name"
	)

	for emp_name in employees:
		doc = frappe.get_doc("havano_employee", emp_name)
		
		for e in doc.employee_earnings:
			if not e.components: continue
			comp = e.components
			if comp not in totals:
				totals[comp] = {"type": "Earning", "usd": 0.0, "zwg": 0.0}
			totals[comp]["usd"] += (e.amount_usd or 0.0)
			totals[comp]["zwg"] += (e.amount_zwg or 0.0)

		for d in doc.employee_deductions:
			if not d.components: continue
			comp = d.components
			if comp not in totals:
				totals[comp] = {"type": "Deduction", "usd": 0.0, "zwg": 0.0}
			totals[comp]["usd"] += (d.amount_usd or 0.0)
			totals[comp]["zwg"] += (d.amount_zwg or 0.0)

	# Sort earnings first, then deductions, then alphabetically by component name
	sorted_comps = sorted(totals.keys(), key=lambda x: (1 if totals[x]["type"] == "Deduction" else 0, x))
	
	for comp in sorted_comps:
		data.append({
			"salary_component": comp,
			"type": totals[comp]["type"],
			"amount_usd": totals[comp]["usd"],
			"amount_zwg": totals[comp]["zwg"]
		})

	return data
