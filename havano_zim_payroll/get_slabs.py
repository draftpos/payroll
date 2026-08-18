import frappe
import json
import os

def get_slabs():
    frappe.init(site="v15.local")
    frappe.connect()
    slabs = frappe.get_all("Havano Tax Bracket", fields=["parent", "lower_limit", "upper_limit", "percent", "fixed_amount"], order_by="parent, lower_limit")
    
    with open("slabs_output.json", "w") as f:
        json.dump(slabs, f, indent=2)

if __name__ == "__main__":
    get_slabs()
