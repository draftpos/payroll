frappe.ui.form.on('Leave Application', {
    employee: function(frm) {
        if (frm.doc.employee) {
            // Fetch Leave Approver
            frappe.db.get_value('havano_employee', frm.doc.employee, 'leave_approver', (r) => {
                if (r && r.leave_approver) {
                    frm.set_value('leave_approver', r.leave_approver);
                }
            });
            // Fetch Leave Balance
            fetch_leave_balance(frm);
        }
    },
    leave_type: function(frm) {
        fetch_leave_balance(frm);
    }
});

function fetch_leave_balance(frm) {
    if (frm.doc.employee && frm.doc.leave_type) {
        frappe.db.get_value('Havano Leave Balances', 
            {'employee': frm.doc.employee, 'havano_leave_type': frm.doc.leave_type}, 
            'leave_balance', (r) => {
                if (r) {
                    frm.set_value('leave_balance', r.leave_balance);
                } else {
                    frm.set_value('leave_balance', 0);
                }
            }
        );
    }
}
