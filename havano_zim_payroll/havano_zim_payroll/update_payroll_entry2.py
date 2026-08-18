import frappe
import json
import os

def run():
    frappe.init(site="v15.local")
    frappe.connect()

    # Add custom fields to Havano Payroll Entry
    fields = [
        {
            "fieldname": "total_taxable_income",
            "fieldtype": "Float",
            "label": "Total Taxable Income",
            "in_list_view": 1,
            "insert_after": "employee_deductions"
        }
    ]

    doc = frappe.get_doc("DocType", "Havano Payroll Entry")
    
    # Check if fields exist
    existing_fields = [f.fieldname for f in doc.fields]
    changed = False
    
    for f in fields:
        if f["fieldname"] not in existing_fields:
            doc.append("fields", {
                "fieldname": f["fieldname"],
                "fieldtype": f["fieldtype"],
                "label": f["label"],
                "in_list_view": f["in_list_view"],
                "insert_after": f["insert_after"]
            })
            changed = True
            print(f"Added {f['fieldname']}")
        else:
            # ensure in_list_view is 1
            for df in doc.fields:
                if df.fieldname == f["fieldname"]:
                    if df.in_list_view != 1:
                        df.in_list_view = 1
                        changed = True
                        print(f"Set in_list_view to 1 for {f['fieldname']}")

    if changed:
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        print("DocType saved.")
    else:
        print("Fields already exist and configured correctly.")

if __name__ == "__main__":
    run()
