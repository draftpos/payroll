// Copyright (c) 2026, Havano and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Loan", {
	refresh(frm) {
        frm.fields_dict.repayment_start_date.$wrapper
            .on('click', function () {
                frappe.prompt([
                    {
                        fieldname: 'month',
                        fieldtype: 'Select',
                        label: 'Month',
                        options: [
                            'January','February','March','April','May','June',
                            'July','August','September','October','November','December'
                        ],
                        reqd: 1
                    },
                    {
                        fieldname: 'year',
                        fieldtype: 'Int',
                        label: 'Year',
                        default: new Date().getFullYear(),
                        reqd: 1
                    }
                ],
                function (values) {
                    frm.set_value(
                        'repayment_start_date',
                        `${values.month} ${values.year}`
                    );
                },
                'Select Repayment Start Date',
                'Set'
                );
            });
	},
});
