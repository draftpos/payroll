import frappe
def main():
    print(frappe.get_doc('Print Format', 'havano payslip single currency').html)
