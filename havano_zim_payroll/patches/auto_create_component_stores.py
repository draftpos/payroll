import frappe

def execute():
    try:
        components = frappe.get_all("havano_salary_component", pluck="name")
    except Exception:
        return
    
    count = 0
    for comp in components:
        dt_name = f"{comp} Report Store"
        if not frappe.db.exists("DocType", dt_name):
            try:
                doc = frappe.get_doc({
                    "doctype": "DocType",
                    "name": dt_name,
                    "module": "Havano Zim Payroll",
                    "custom": 1,
                    "naming_rule": "Expression",
                    "autoname": "format:{employee}-{payroll_period}",
                    "fields": [
                        {"fieldname": "employee", "fieldtype": "Link", "options": "havano_employee", "label": "Employee", "in_list_view": 1},
                        {"fieldname": "first_name", "fieldtype": "Data", "label": "First Name", "fetch_from": "employee.first_name", "read_only": 1},
                        {"fieldname": "surname", "fieldtype": "Data", "label": "Surname", "fetch_from": "employee.last_name", "read_only": 1},
                        {"fieldname": "national_id", "fieldtype": "Data", "label": "National ID", "fetch_from": "employee.national_id", "read_only": 1},
                        {"fieldname": "department", "fieldtype": "Link", "options": "Department", "label": "Department", "in_list_view": 1, "in_standard_filter": 1},
                        {"fieldname": "payroll_period", "fieldtype": "Link", "options": "Payroll Period", "label": "Payroll Period", "in_list_view": 1, "in_standard_filter": 1},
                        {"fieldname": "amount", "fieldtype": "Currency", "label": "Amount", "in_list_view": 1}
                    ],
                    "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}]
                })
                doc.insert(ignore_permissions=True)
                count += 1
            except Exception as e:
                frappe.log_error(f"Failed to auto-create {dt_name}: {str(e)}")

    frappe.db.commit()
    print(f"Successfully auto-generated {count} new Report Store DocTypes for existing Salary Components!")
