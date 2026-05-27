import json
import os

filepath = "/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/havano_zim_payroll/havano_zim_payroll/doctype/havano_employee/havano_employee.json"

with open(filepath, "r") as f:
    data = json.load(f)

fields = data.get("fields", [])

# check if cimas_amount already exists
if any(f.get("fieldname") == "cimas_amount" for f in fields):
    print("cimas_amount already exists!")
else:
    # find index of funeral_and_cimas_section
    idx = 0
    for i, f in enumerate(fields):
        if f.get("fieldname") == "funeral_and_cimas_section":
            idx = i
            break
            
    # insert cimas_amount
    fields.insert(idx + 1, {
        "fieldname": "cimas_amount",
        "fieldtype": "Currency",
        "label": "CIMAS Amount"
    })
    
    data["fields"] = fields
    data["modified"] = "2026-05-27 15:00:00.000000"
    
    with open(filepath, "w") as f:
        json.dump(data, f, indent=1)
        
    print("Successfully added cimas_amount to havano_employee.json")
