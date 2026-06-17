def execute():
	import frappe
	with open("apps/havano_zim_payroll/havano_zim_payroll/report/payroll_summary/payroll_summary.html") as f:
		template = f.read()
	data = [{'earnings': 'Basic', 'earnings_amount_usd': 1000.0, 'deductions': 'PAYE', 'deductions_amount_usd': 50.0}]
	filters = {'month': 'January'}
	out = frappe.render_template(template, {'data': data, 'filters': filters})
	print(out)
