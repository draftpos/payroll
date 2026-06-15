frappe.query_reports["Salary Register"] = {
	"filters": [
		{
			"fieldname": "employee_id",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "havano_employee"
		}
	]
};
