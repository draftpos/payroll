frappe.query_reports["SDL Report"] = {
	"filters": [
		{
			"fieldname": "payroll_period",
			"label": __("Payroll Period"),
			"fieldtype": "Link",
			"options": "Payroll Period",
			"default": ""
		},
		{
			"fieldname": "employee_id",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "havano_employee"
		}
	]
};
