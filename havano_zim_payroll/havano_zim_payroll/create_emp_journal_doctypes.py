import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def execute():
    try:
        # Create Havano Employer Contributions Detail
        if not frappe.db.exists("DocType", "Havano Employer Contributions Detail"):
            detail_doc = frappe.get_doc({
                "doctype": "DocType",
                "name": "Havano Employer Contributions Detail",
                "module": "Havano Zim Payroll",
                "custom": 0,
                "istable": 1,
                "editable_grid": 1,
                "fields": [
                    {
                        "fieldname": "detail",
                        "fieldtype": "Data",
                        "label": "Detail",
                        "in_list_view": 1,
                        "columns": 4
                    },
                    {
                        "fieldname": "dr",
                        "fieldtype": "Currency",
                        "label": "DR",
                        "in_list_view": 1,
                        "columns": 3
                    },
                    {
                        "fieldname": "cr",
                        "fieldtype": "Currency",
                        "label": "CR",
                        "in_list_view": 1,
                        "columns": 3
                    }
                ]
            })
            detail_doc.insert(ignore_permissions=True)
            print("Created Havano Employer Contributions Detail")

        # Create Havano Employer Contributions Journal
        if not frappe.db.exists("DocType", "Havano Employer Contributions Journal"):
            journal_doc = frappe.get_doc({
                "doctype": "DocType",
                "name": "Havano Employer Contributions Journal",
                "module": "Havano Zim Payroll",
                "custom": 0,
                "autoname": "format:ECJ-{YYYY}-{MM}-{####}",
                "permissions": [
                    {
                        "role": "System Manager",
                        "read": 1, "write": 1, "create": 1, "delete": 1,
                        "report": 1, "export": 1, "print": 1, "email": 1, "share": 1
                    },
                    {
                        "role": "HR Manager",
                        "read": 1, "write": 1, "create": 1, "delete": 1,
                        "report": 1, "export": 1, "print": 1, "email": 1, "share": 1
                    }
                ],
                "fields": [
                    {
                        "fieldname": "payroll_period",
                        "fieldtype": "Data",
                        "label": "Payroll Period",
                        "reqd": 1,
                        "in_list_view": 1
                    },
                    {
                        "fieldname": "company",
                        "fieldtype": "Link",
                        "options": "Company",
                        "label": "Company",
                        "reqd": 1,
                        "in_list_view": 1
                    },
                    {
                        "fieldname": "journal_details",
                        "fieldtype": "Table",
                        "options": "Havano Employer Contributions Detail",
                        "label": "Journal Details"
                    }
                ]
            })
            journal_doc.insert(ignore_permissions=True)
            print("Created Havano Employer Contributions Journal")
            
        print("Success")
    except Exception as e:
        print("Error:", e)
        import traceback
        traceback.print_exc()
