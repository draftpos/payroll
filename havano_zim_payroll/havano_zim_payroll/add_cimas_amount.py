import frappe

def execute():
    doctype = frappe.get_doc("DocType", "havano_employee")
    existing_fields = [f.fieldname for f in doctype.fields]

    if "cimas_amount" not in existing_fields:
        # Find index of funeral_and_cimas_section
        idx = 0
        for i, f in enumerate(doctype.fields):
            if f.fieldname == "funeral_and_cimas_section":
                idx = i
                break
        
        # We must insert it into the list of fields at idx + 1
        doctype.fields.insert(idx + 1, frappe._dict({
            "doctype": "DocField",
            "fieldname": "cimas_amount",
            "fieldtype": "Currency",
            "label": "CIMAS Amount",
            "insert_after": "funeral_and_cimas_section"
        }))
        
        doctype.save()
        frappe.db.commit()
        print("Added cimas_amount field to havano_employee")
    else:
        print("cimas_amount already exists")
