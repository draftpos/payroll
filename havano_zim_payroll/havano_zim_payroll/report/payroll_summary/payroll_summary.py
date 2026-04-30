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
