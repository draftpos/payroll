import frappe

def get_logs():
    logs = frappe.get_all("Error Log", fields=["method", "error"], limit=3, order_by="creation desc")
    for log in logs:
        print(log.method)
        print(log.error)
