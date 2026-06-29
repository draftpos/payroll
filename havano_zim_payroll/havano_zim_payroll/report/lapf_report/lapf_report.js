frappe.query_reports["LAPF Report"] = {
	"filters": [
		{
			"fieldname": "payroll_period",
			"label": __("Payroll Period"),
			"fieldtype": "Data",
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
