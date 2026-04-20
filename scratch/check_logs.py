import frappe
frappe.init(site="v15.local")
frappe.connect()
logs = frappe.get_all("Error Log", fields=["title", "message", "creation"], order_by="creation desc", limit=5)
for log in logs:
    print(f"--- {log.creation} ---\n{log.title}\n{log.message}\n")
