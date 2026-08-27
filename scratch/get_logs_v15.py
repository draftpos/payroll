import frappe
frappe.init(site="v15.local")
frappe.connect()
logs = frappe.get_all("Error Log", fields=["method", "error"], limit=10, order_by="creation desc")
for log in logs:
    print("Method: " + str(log.method))
    print("Error: " + str(log.error))
