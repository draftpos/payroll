import frappe

def create_report():
    if frappe.db.exists('Report', 'Havano Leave Balance Report'):
        print('Report already exists')
        return

    doc = frappe.get_doc({
        'doctype': 'Report',
        'report_name': 'Havano Leave Balance Report',
        'ref_doctype': 'Havano Leave Ledger Entry',
        'report_type': 'Script Report',
        'is_standard': 'Yes',
        'module': 'Havano Zim Payroll',
        'roles': [{'role': 'System Manager'}, {'role': 'HR User'}, {'role': 'HR Manager'}]
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print('Report created successfully.')
