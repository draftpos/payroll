import frappe

def execute():
    doctype_name = "Havano Historical PAYE"
    
    if not frappe.db.exists("DocType", doctype_name):
        fields = [
            {
                "fieldname": "employee",
                "fieldtype": "Link",
                "options": "havano_employee",
                "label": "Employee",
                "in_list_view": 1,
                "reqd": 1
            },
            {
                "fieldname": "first_name",
                "fieldtype": "Data",
                "label": "First Name",
                "fetch_from": "employee.first_name",
                "in_list_view": 1
            },
            {
                "fieldname": "last_name",
                "fieldtype": "Data",
                "label": "Last Name",
                "fetch_from": "employee.last_name",
                "in_list_view": 1
            },
            {
                "fieldname": "tax_year",
                "fieldtype": "Data",
                "label": "Tax Year",
                "in_list_view": 1,
                "reqd": 1,
                "default": "2026"
            }
        ]
        
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        for i, month in enumerate(months):
            fields.append({
                "fieldname": f"month_{i+1}_usd",
                "fieldtype": "Currency",
                "label": f"{month} PAYE (USD)",
                "default": "0.0"
            })
            fields.append({
                "fieldname": f"month_{i+1}_zwg",
                "fieldtype": "Currency",
                "label": f"{month} PAYE (ZWG)",
                "default": "0.0"
            })
            
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": doctype_name,
            "module": "Havano Zim Payroll",
            "custom": 0,
            "istable": 0,
            "fields": fields,
            "permissions": [
                {
                    "role": "System Manager",
                    "read": 1,
                    "write": 1,
                    "create": 1,
                    "delete": 1
                }
            ]
        })
        doc.insert(ignore_permissions=True)
        print(f"Created DocType: {doctype_name}")
    else:
        print(f"DocType {doctype_name} already exists.")
