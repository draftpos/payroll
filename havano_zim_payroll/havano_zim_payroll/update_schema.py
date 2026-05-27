import frappe
import sys

frappe.init(site="v15.local")
frappe.connect()

doctype = frappe.get_doc("DocType", "havano_payroll_earnings")
existing_fields = [f.fieldname for f in doctype.fields]

modified = False
if "original_amount_usd" not in existing_fields:
    doctype.append("fields", {
        "fieldname": "original_amount_usd",
        "fieldtype": "Float",
        "label": "Original Base Amount",
        "hidden": 1
    })
    modified = True

if "original_amount_zwg" not in existing_fields:
    doctype.append("fields", {
        "fieldname": "original_amount_zwg",
        "fieldtype": "Float",
        "label": "Original Foreign Amount",
        "hidden": 1
    })
    modified = True

if modified:
    doctype.save()
    frappe.db.commit()
    print("Added original_amount fields")
else:
    print("Fields already exist")
