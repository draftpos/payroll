frappe.ui.form.on('Havano Employee', {
    onload: function(frm) {
        frm.set_df_property('employee_category', 'hidden', 1);
        frm.set_df_property('usd_percentage', 'hidden', 1);
        frm.set_df_property('zig_percentage', 'hidden', 1);
    },
    refresh: function(frm) {
        // Fetch Payroll Settings to see if dual currency is enabled
        frappe.db.get_single_value('Havano Payroll Settings', 'dual_currency_with_conversions')
            .then(enabled => {
                if (enabled == 1 || enabled === "1" || enabled === true) {
                    frm.set_df_property('employee_category', 'hidden', 0);
                    // The depends_on condition handles the percentage fields visibility
                } else {
                    frm.set_df_property('employee_category', 'hidden', 1);
                    frm.set_df_property('usd_percentage', 'hidden', 1);
                    frm.set_df_property('zig_percentage', 'hidden', 1);
                }
            });
    },
    employee_category: function(frm) {
        // Just in case depends_on doesn't trigger immediately
        if (frm.doc.employee_category === 'Both (Zig and USD)') {
            frm.set_df_property('usd_percentage', 'hidden', 0);
            frm.set_df_property('zig_percentage', 'hidden', 0);
        } else {
            frm.set_df_property('usd_percentage', 'hidden', 1);
            frm.set_df_property('zig_percentage', 'hidden', 1);
        }
    }
});
