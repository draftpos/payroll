import frappe
import json

def get_tax_credits():
    frappe.init(site="v15.local")
    frappe.connect()
    try:
        credits = frappe.get_all("Havano Tax Credits", fields=["*"])
        print(json.dumps(credits, indent=2))
    except Exception as e:
        print(str(e))

if __name__ == "__main__":
    get_tax_credits()
