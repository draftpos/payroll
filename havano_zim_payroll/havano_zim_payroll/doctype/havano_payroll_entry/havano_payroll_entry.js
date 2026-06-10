// Copyright (c) 2025, Havano and contributors
// For license information, please see license.txt

frappe.ui.form.on("Havano Payroll Entry", {
	employee: function(frm) {
		if (frm.doc.employee) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Havano Leave Balances",
					filters: { "employee": frm.doc.employee },
					fieldname: "leave_balance"
				},
				callback: function(r) {
					if (r.message && r.message.leave_balance !== undefined) {
						frm.set_value('leave_balances', r.message.leave_balance);
					} else {
						frm.set_value('leave_balances', 0);
					}
				}
			});
		} else {
			frm.set_value('leave_balances', 0);
		}
	}
});
