frappe.query_reports["Salary Summary On Payroll Run"] = {
	"filters": [
		{
			"fieldname": "payroll_period",
			"label": __("Payroll Period (e.g. January 2026)"),
			"fieldtype": "Data",
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
