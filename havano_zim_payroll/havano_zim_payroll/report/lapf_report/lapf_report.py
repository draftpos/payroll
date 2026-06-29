import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	
	filtered_columns = []
	for col in columns:
		if col.get("fieldtype") in ["Currency", "Float", "Int"]:
			col_total = sum(flt(row.get(col.get("fieldname"))) for row in data if not row.get("is_total"))
			if col_total == 0:
				continue
		filtered_columns.append(col)

	return filtered_columns, data

def get_columns():
	columns = [
		{"label": _("Employee Number"), "fieldname": "employee_number", "fieldtype": "Data", "width": 120},
		{"label": _("First Name"), "fieldname": "first_name", "fieldtype": "Data", "width": 120},
		{"label": _("Surname"), "fieldname": "surname", "fieldtype": "Data", "width": 120},
		{"label": _("ID Number"), "fieldname": "national_id", "fieldtype": "Data", "width": 120},
		{"label": _("Payroll Period"), "fieldname": "payroll_period", "fieldtype": "Data", "width": 120},
		{"label": _("Date Started"), "fieldname": "date_started", "fieldtype": "Date", "width": 100},
		{"label": _("Date of Birth"), "fieldname": "date_of_birth", "fieldtype": "Date", "width": 100},
		{"label": _("Salary (US$)"), "fieldname": "salary", "fieldtype": "Currency", "width": 120},
		{"label": _("Employee Pension"), "fieldname": "employee_pension", "fieldtype": "Currency", "width": 130},
		{"label": _("Company Pension"), "fieldname": "company_pension", "fieldtype": "Currency", "width": 130},
		{"label": _("Total Pension"), "fieldname": "total_pension", "fieldtype": "Currency", "width": 130},
		{"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Date", "width": 100},
		{"label": _("Pay Point"), "fieldname": "pay_point", "fieldtype": "Data", "width": 150, "hidden": 1},
	]
	return columns

def get_data(filters):
	data = []
	
	query_filters = {"status": "Active"}
	if filters and filters.get("department"):
		query_filters["department"] = filters.get("department")

	employees = frappe.get_all(
		"havano_employee",
		filters=query_filters,
		fields=[
			"name", "first_name", "last_name", "national_id", "date_of_joining", 
			"date_of_birth", "contract_end_date", "department", "lapf_employee", "lapf_employer",
			"total_taxable_income_usd", "total_taxable_income_zwg"
		]
	)

	payroll_period = filters.get("payroll_period") if filters and filters.get("payroll_period") else ""

	# Group by department (Pay Point)
	departments = {}
	for emp in employees:
		doc = frappe.get_doc("havano_employee", emp.name)
		
		# Find LAPF values explicitly from tables if lapf_employee is 0 or to be safe
		lapf_emp = flt(emp.lapf_employee)
		lapf_comp = flt(emp.lapf_employer)
		
		# If they don't have LAPF, skip
		if lapf_emp == 0 and lapf_comp == 0:
			continue
			
		basic_usd = 0.0
		for e in doc.employee_earnings:
			if e.components and "basic" in e.components.lower():
				basic_usd += flt(e.amount_usd)

		dept = emp.department or "Unknown Pay Point"
		if dept not in departments:
			departments[dept] = []
			
		row = {
			"employee_number": emp.name,
			"first_name": emp.first_name,
			"surname": emp.last_name,
			"national_id": emp.national_id,
			"payroll_period": payroll_period,
			"date_started": emp.date_of_joining,
			"date_of_birth": emp.date_of_birth,
			"salary": basic_usd,
			"employee_pension": lapf_emp,
			"company_pension": lapf_comp,
			"total_pension": lapf_emp + lapf_comp,
			"end_date": emp.contract_end_date,
			"pay_point": dept,
			"is_total": 0
		}
		
		departments[dept].append(row)

	# Format grouped data
	for dept, emps in departments.items():
		# Add department header or simply rely on row grouping
		data.append({"employee_number": frappe.bold(dept), "is_total": 1})
		
		total_salary = 0.0
		total_emp_pension = 0.0
		total_comp_pension = 0.0
		total_pension = 0.0
		
		for emp in emps:
			data.append(emp)
			total_salary += emp["salary"]
			total_emp_pension += emp["employee_pension"]
			total_comp_pension += emp["company_pension"]
			total_pension += emp["total_pension"]
			
		# Add department totals
		data.append({
			"first_name": frappe.bold("Pay Point Totals"),
			"employee_number": frappe.bold(f"{len(emps)} Employees Printed"),
			"salary": total_salary,
			"employee_pension": total_emp_pension,
			"company_pension": total_comp_pension,
			"total_pension": total_pension,
			"is_total": 1
		})
		
		# Add empty row for spacing
		data.append({"is_total": 1})

	return data

def flt(val):
	try:
		return float(val or 0.0)
	except ValueError:
		return 0.0
