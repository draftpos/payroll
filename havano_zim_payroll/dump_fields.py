import frappe

def execute():
    slip_fields = [f.fieldname for f in frappe.get_meta("Salary Slip").fields]
    detail_fields = [f.fieldname for f in frappe.get_meta("Salary Detail").fields]
    print("Salary Slip fields:", slip_fields)
    print("Salary Detail fields:", detail_fields)
