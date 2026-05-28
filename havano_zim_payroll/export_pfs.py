import frappe
def main():
    pfs = frappe.get_all('Print Format', filters={'name': ('in', ['havano payslip single currency', 'Havano Employee Payslip'])})
    for pf in pfs:
        doc = frappe.get_doc('Print Format', pf.name)
        doc.custom = 0
        doc.standard = 'Yes'
        doc.module = 'Havano Zim Payroll'
        doc.save(ignore_permissions=True)
        print(f'Exported {pf.name} to codebase!')
    frappe.db.commit()
