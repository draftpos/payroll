frappe.query_reports["Payroll Summary"] = {
	"filters": [
		{
			"fieldname": "group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"options": "Employee\nSalary Component",
			"default": "Employee"
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
