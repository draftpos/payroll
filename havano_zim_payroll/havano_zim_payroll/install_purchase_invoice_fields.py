import frappe
import os
import json

@frappe.whitelist()
def add_payroll_fields_to_purchase_invoice():
    # Path to Purchase Invoice DocType JSON
    module_path = frappe.get_module_path("accounts")
    json_path = os.path.join(module_path, "doctype/purchase_invoice/purchase_invoice.json")

    # Load existing JSON
    with open(json_path, "r") as f:
        data = json.load(f)

    # Define new fields
    new_fields = [
        {
            "fieldname": "custom_payroll_period",
            "label": "Payroll Period",
            "fieldtype": "Check",
            "insert_after": "posting_date",  # adjust where you want it
            "hidden": 0,
            "reqd": 0
        },
        {
            "fieldname": "custom_from_payroll",
            "label": "From Payroll",
            "fieldtype": "Data",
            "insert_after": "company",
            "hidden": 0,
            "reqd": 0
        }
    ]

    # Add fields if they don't exist
    existing_fieldnames = [f["fieldname"] for f in data.get("fields", [])]
    added = False

    for field in new_fields:
        if field["fieldname"] not in existing_fieldnames:
            data["fields"].append(field)
            added = True

    if added:
        # Save JSON back
        with open(json_path, "w") as f:
            json.dump(data, f, indent=4)

        # Reload DocType
        frappe.reload_doc("accounts", "doctype", "purchase_invoice", force=True)
        frappe.clear_cache(doctype="Purchase Invoice")

        return "Payroll Period and From Payroll fields added successfully"

    return "Fields already exist"
