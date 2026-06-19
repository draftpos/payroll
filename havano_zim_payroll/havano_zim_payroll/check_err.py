import frappe
def execute():
    errors = frappe.get_all("Error Log", fields=["error"], order_by="creation desc", limit=5)
    for e in errors:
        print(e.error)
