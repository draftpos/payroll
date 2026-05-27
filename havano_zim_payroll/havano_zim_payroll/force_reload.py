import frappe
def execute():
    frappe.reload_doc("havano_zim_payroll", "doctype", "havano_employee", force=True)
    print("Reloaded havano_employee successfully!")
