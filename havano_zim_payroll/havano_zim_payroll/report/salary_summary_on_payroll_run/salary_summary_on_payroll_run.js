frappe.query_reports["Salary Summary On Payroll Run"] = {
	"filters": [
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"default": ""
		},
		{
			"fieldname": "payroll_period",
			"label": __("Payroll Period (e.g. January 2026)"),
			"fieldtype": "Link",
			"options": "Payroll Period",
			"default": ""
		},
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "havano_employee"
		}
	]
};
