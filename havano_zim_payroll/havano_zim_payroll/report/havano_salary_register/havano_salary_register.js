frappe.query_reports["Havano Salary Register"] = {
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
	],
	"onload": function(report) {
		report.page.add_inner_button(__("Add New Employee"), function() {
			frappe.new_doc("havano_employee");
		});
	}
};
