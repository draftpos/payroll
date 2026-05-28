import frappe
def main():
    pfs = frappe.get_all('Print Format', filters={'name': ('in', ['havano payslip single currency', 'Havano Employee Payslip'])})
    for pf in pfs:
        doc = frappe.get_doc('Print Format', pf.name)
        html = doc.html
        
        # Replace the strict 'doc.cimas_employee_ == 0' with a more robust check
        old_condition = "doc.cimas_employee_ == 0"
        new_condition = "(doc.cimas_employee_ in [0, None, ''] or doc.cimas_employer_ == 100)"
        
        if old_condition in html:
            html = html.replace(old_condition, new_condition)
            doc.html = html
            doc.save(ignore_permissions=True)
            print(f"Patched {pf.name} condition!")
        else:
            print(f"{pf.name} condition not found or already patched.")
    frappe.db.commit()
