// Copyright (c) 2025, Havano and contributors
// For license information, please see license.txt

function fetch_leave_data(frm) {
	if (frm.doc.first_name) {
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "havano_employee",
				filters: {
					first_name: frm.doc.first_name
				},
				fields: ["name", "middle_name", "last_name", "total_leave_taken"]
			},
			callback: function(r) {
				if (r.message && r.message.length > 0) {
					let emp = r.message[0];
					if (emp.middle_name) frm.set_value('middle_name', emp.middle_name);
					if (emp.last_name) frm.set_value('last_name', emp.last_name);
					frm.set_value('total_leave_taken', emp.total_leave_taken);
					
					frappe.call({
						method: "frappe.client.get_value",
						args: {
							doctype: "Havano Leave Balances",
							filters: { "employee": emp.name },
							fieldname: "leave_balance"
						},
						callback: function(res) {
							if (res.message && res.message.leave_balance !== undefined) {
								frm.set_value('leave_balances', res.message.leave_balance);
							}
						}
					});
				}
			}
		});
	}
}

frappe.ui.form.on("Havano Payroll Entry", {
	refresh: function(frm) {
		fetch_leave_data(frm);
	},
	first_name: function(frm) {
		fetch_leave_data(frm);
	},
	last_name: function(frm) {
		fetch_leave_data(frm);
	}
});
