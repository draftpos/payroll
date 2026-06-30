import frappe
def execute():
    try:
        scripts = frappe.get_all("Webhook", fields=["name", "webhook_docevent", "webhook_doctype"])
        for s in scripts:
            print(s.name, s.webhook_doctype, s.webhook_docevent)
    except Exception as e:
        print("Error:", e)
