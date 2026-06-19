import frappe
def execute():
    errors = frappe.get_all("Error Log", fields=["error", "method"], order_by="creation desc", limit=3)
    for e in errors:
        print("==========")
        print(e.error)
