// Copyright (c) 2025, Havano and contributors
// For license information, please see license.txt

frappe.ui.form.on("havano_leave_encashment", {

        refresh(frm) {
                // Always re-fetch live balance from DB on every form open
                if (frm.doc.employee && frm.doc.leave_type && !frm.doc.docstatus) {
                        fetch_leave_balance(frm);
                }
        },

	employee(frm) {
		if (frm.doc.employee) {
			frappe.db.get_value("havano_employee", frm.doc.employee,
				["employee_name", "department", "company"],
				function(r) {
					if (r) {
						frm.set_value("employee_name", r.employee_name);
						frm.set_value("department", r.department);
						frm.set_value("company", r.company);
					}
				}
			);
			// Always reset balance - it must come from Havano Leave Balances via leave_type
			frm.set_value("current_leave_balance", 0);
			frm.set_value("days_being_encashed", 0);
			frm.set_value("encashment_amount", 0);
		} else {
			frm.set_value("employee_name", "");
			frm.set_value("department", "");
			frm.set_value("company", "");
			frm.set_value("current_leave_balance", 0);
			frm.set_value("days_being_encashed", 0);
			frm.set_value("encashment_amount", 0);
		}
	},

	leave_type(frm) {
		// Reset days and amount when leave type changes
		frm.set_value("days_being_encashed", 0);
		frm.set_value("encashment_amount", 0);
		frm.set_value("current_leave_balance", 0);

		if (frm.doc.leave_type && frm.doc.employee) {
			fetch_leave_balance(frm);
		}
	},

	days_being_encashed(frm) {
		const days = flt(frm.doc.days_being_encashed) || 0;
		const balance = flt(frm.doc.current_leave_balance) || 0;

		if (balance === 0) {
			frappe.msgprint({ title: __("No Balance"), message: __("Please select an employee and leave type first."), indicator: "orange" });
			frm.set_value("days_being_encashed", 0);
			return;
		}

		if (days > balance) {
			frappe.msgprint({ title: __("Insufficient Balance"), message: __("Days ({0}) exceeds balance ({1}). Resetting.", [days, balance]), indicator: "red" });
			frm.set_value("days_being_encashed", balance);
			return;
		}
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
		{ employee: frm.doc.employee, havano_leave_type: frm.doc.leave_type },
		"leave_balance",
		function(r) {
			if (r && r.leave_balance !== undefined && r.leave_balance !== null) {
				frm.set_value("current_leave_balance", r.leave_balance);
			} else {
				frm.set_value("current_leave_balance", 0);
				frappe.msgprint({ title: __("No Leave Balance Found"), message: __("No leave balance record found for this employee and leave type."), indicator: "orange" });
			}
		}
	);
}

function calculate_encashment(frm) {
	const days = flt(frm.doc.days_being_encashed) || 0;
	const rate = flt(frm.doc.rate_per_day) || 0;
	frm.set_value("encashment_amount", days * rate);
}
