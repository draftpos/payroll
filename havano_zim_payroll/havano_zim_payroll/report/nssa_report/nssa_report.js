frappe.query_reports["NSSA Report"] = {
	"filters": [
		{
			"fieldname": "employee_id",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "havano_employee"
		}
	]
};
