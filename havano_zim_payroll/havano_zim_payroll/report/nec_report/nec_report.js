frappe.query_reports["NEC Report"] = {
	"filters": [
		{
			"fieldname": "employee_id",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "havano_employee"
		}
	]
};
