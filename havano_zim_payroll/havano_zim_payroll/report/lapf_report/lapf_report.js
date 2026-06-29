frappe.query_reports["LAPF Report"] = {
	"filters": [
		{
			"fieldname": "payroll_period",
			"label": __("Payroll Period"),
			"fieldtype": "Link",
			"options": "Payroll Period",
			"default": ""
		},
		{
			"fieldname": "department",
			"label": __("Pay Point (Department)"),
			"fieldtype": "Link",
			"options": "Department"
		}
	]
};
