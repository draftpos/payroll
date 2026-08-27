import frappe
frappe.init(site="erp1038.havano.cloud")
frappe.connect()
logs = frappe.get_all("Error Log", fields=["method", "error"], limit=10, order_by="creation desc")
for log in logs:
    print(log.method)
    print(log.error)
