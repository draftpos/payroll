// Copyright (c) 2025, Havano and contributors
// For license information, please see license.txt

frappe.ui.form.on("havano_leave_encashment", {
	// Fetch leave balance when employee or leave_type changes
	employee(frm) {
		fetch_leave_balance(frm);
	},
	leave_type(frm) {
		fetch_leave_balance(frm);
	},
	// Recalculate encashment amount when days or rate changes
	days_being_encashed(frm) {
		calculate_encashment(frm);
	},
	rate_per_day(frm) {
		calculate_encashment(frm);
	}
});

function fetch_leave_balance(frm) {
	if (!frm.doc.employee || !frm.doc.leave_type) return;

	frappe.db.get_value(
		"Havano Leave Balances",
		{
			employee: frm.doc.employee,
			havano_leave_type: frm.doc.leave_type
		},
		"leave_balance",
		function(r) {
			if (r && r.leave_balance !== undefined) {
				frm.set_value("current_leave_balance", r.leave_balance);
			} else {
				frm.set_value("current_leave_balance", 0);
				frappe.msgprint({
					title: __("No Leave Balance Found"),
					message: __("No leave balance record found for this employee and leave type."),
					indicator: "orange"
				});
			}
		}
	);
}

function calculate_encashment(frm) {
	const days = flt(frm.doc.days_being_encashed) || 0;
	const rate = flt(frm.doc.rate_per_day) || 0;
	frm.set_value("encashment_amount", days * rate);
}
