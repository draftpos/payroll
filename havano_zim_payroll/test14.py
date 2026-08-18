import frappe

def run():
    meta = frappe.get_meta("Salary Slip")
    fields = [f.fieldname for f in meta.fields if "tax" in f.fieldname.lower() or "income" in f.fieldname.lower() or "amount" in f.fieldname.lower()]
    print("Relevant Fields in Salary Slip:", fields)
