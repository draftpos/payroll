import frappe
import json

def get_slabs():
    slabs = frappe.get_all("Havano Tax Brackets", fields=["parent", "lower_limit", "upper_limit", "percent", "fixed_amount"], order_by="parent, lower_limit")
    print(json.dumps(slabs, indent=2))
