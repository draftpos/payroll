frappe.ui.form.on('havano_leave_application', {
    refresh: function(frm) {
        // Optional: Filter leave approver based on something
    },
    employee: function(frm) {
        if (frm.doc.employee) {
            frappe.db.get_value('havano_employee', frm.doc.employee, ['leave_approver', 'employee_name'], (r) => {
                if (r) {
                    if (r.leave_approver) {
                        frm.set_value('leave_approver', r.leave_approver);
                    }
                    if (r.employee_name) {
                        frm.set_value('employee_name', r.employee_name);
                    }
                    frm.refresh_field('leave_approver');
                    frm.refresh_field('employee_name');
                }
            });
            fetch_leave_balance(frm);
        }
    },
    leave_type: function(frm) {
        fetch_leave_balance(frm);
    },
    from_date: function(frm) {
        calculate_total_days(frm);
    },
    to_date: function(frm) {
        calculate_total_days(frm);
    },
    half_day: function(frm) {
        calculate_total_days(frm);
    }
});

function fetch_leave_balance(frm) {
    if (frm.doc.employee) {
        // Fetch specific balance for selected leave type
        if (frm.doc.leave_type) {
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

        // Fetch all balances for the table preview
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Havano Leave Balances',
                filters: {'employee': frm.doc.employee},
                fields: ['havano_leave_type', 'leave_balance', 'from_date', 'to_date']
            },
            callback: function(r) {
                if (r.message) {
                    let html = `
                        <table class="table table-bordered table-hover" style="margin-top: 10px; font-size: 13px;">
                            <thead>
                                <tr class="text-muted">
                                    <th>Leave Type</th>
                                    <th class="text-right">Balance</th>
                                    <th>Period</th>
                                </tr>
                            </thead>
                            <tbody>`;
                    
                    r.message.forEach(row => {
                        html += `
                            <tr>
                                <td>${row.havano_leave_type}</td>
                                <td class="text-right"><b>${row.leave_balance}</b></td>
                                <td class="text-muted small">${row.from_date || ''} to ${row.to_date || ''}</td>
                            </tr>`;
                    });

                    html += `</tbody></table>`;
                    frm.set_df_property('leave_balance_html', 'options', html);
                    frm.refresh_field('leave_balance_html');
                }
            }
        });
    }
}

function calculate_total_days(frm) {
    if (frm.doc.from_date && frm.doc.to_date) {
        let days = frappe.datetime.get_day_diff(frm.doc.to_date, frm.doc.from_date) + 1;
        if (frm.doc.half_day) {
            days -= 0.5;
        }
        frm.set_value('total_leave_days', days);
    }
}
