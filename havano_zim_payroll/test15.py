import frappe

def run():
    print("\n--- SALARY SLIP FIELDS ---")
    slip_fields = [f.fieldname for f in frappe.get_meta("Salary Slip").fields]
    for f in slip_fields:
        if any(keyword in f.lower() for keyword in ["tax", "income", "deduct", "gross", "allowable"]):
            print("Salary Slip Field:", f)
            
    print("\n--- HAVANO PAYROLL ENTRY FIELDS ---")
    h_fields = [f.fieldname for f in frappe.get_meta("Havano Payroll Entry").fields]
    for f in h_fields:
        if any(keyword in f.lower() for keyword in ["tax", "income", "deduct", "gross", "allowable"]):
            print("Havano Payroll Entry Field:", f)
